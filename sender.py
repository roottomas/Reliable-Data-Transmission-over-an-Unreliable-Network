import sys
import os
from socket import *
import threading
import time
import queue
import pickle
import random
import select

blocksInWindow = 0
window = []
sendingDone = False


def sendDatagram(blockNo, contents, sock, end):
    rand = random.randint(0, 9)
    if rand > 1:
        toSend = (blockNo, contents)
        msg = pickle.dumps(toSend)
        sock.sendto(msg, end)


def waitForAck(s, seg):
    rx, tx, er = select.select([s], [], [], seg)
    return rx != []


def tx_thread(s, receiver, windowSize, cond, timeout):
    global blocksInWindow, window, sendingDone

    base = 1
    last_ack = 0
    duplicate_acks = 0
    last_seq_sent = 0

    s.setblocking(0)

    while True:
        with cond:
            if window:
                last_seq_sent = window[-1][0]
            if blocksInWindow == 0 and sendingDone:
                if last_seq_sent > 0:
                    final_block = (last_seq_sent + 1, b"")
                    msg = pickle.dumps(final_block)
                    s.sendto(msg, receiver)
                print("[TX] All data acknowledged, exiting tx_thread.")
                break

        ready = waitForAck(s, timeout)
        if ready:
            data, _ = s.recvfrom(64)
            ack_tuple = pickle.loads(data)
            ackNo = ack_tuple[0]
            with cond:
                if ackNo >= base:
                    # Slide window for cumulative ACK
                    shift = ackNo - base + 1
                    window = window[shift:]
                    blocksInWindow = len(window)
                    base = ackNo + 1
                    duplicate_acks = 0
                    cond.notify_all()
                elif ackNo == last_ack:
                    # Duplicate ACK -> retransmit
                    duplicate_acks += 1
                    if duplicate_acks == 2 and window:
                        print(f"Fast retransmit for base={base}")
                        for (bNo, bData) in window:
                            sendDatagram(bNo, bData, s, receiver)
                        duplicate_acks = 0
                last_ack = ackNo
        else:
            # Timeout -> retransmit all unACKed blocks
            with cond:
                if window:
                    print(f"Timeout, retransmitting from {window[0][0]} to {window[-1][0]}")
                    for (bNo, bData) in window:
                        sendDatagram(bNo, bData, s, receiver)


def sendBlock(seqNo, fileBytes, s, receiver, windowSize, cond):
    global blocksInWindow, window

    with cond:
        while blocksInWindow >= windowSize:
            cond.wait()

        window.append((seqNo, fileBytes))
        print(f"Sending block {seqNo} ({len(fileBytes)} bytes)")
        sendDatagram(seqNo, fileBytes, s, receiver)

        blocksInWindow += 1
        cond.notify_all()


def main(hostname, senderPort, windowSize, timeOutInSec):
    s = socket(AF_INET, SOCK_DGRAM)
    s.bind((hostname, senderPort))
    print(f"Sender listening on {s.getsockname()}")

    # interaction with receiver; no datagram loss
    buf, rem = s.recvfrom(256)
    req = pickle.loads(buf)
    fileName = req[0]
    blockSize = req[1]
    result = os.path.exists(fileName)

    if not result:
        print(f'File {fileName} does not exist in server')
        reply = (-1, 0)
        rep = pickle.dumps(reply)
        s.sendto(rep, rem)
        sys.exit(1)

    fileSize = os.path.getsize(fileName)
    reply = (0, fileSize)
    rep = pickle.dumps(reply)
    s.sendto(rep, rem)

    # file transfer; datagram loss possible
    windowCond = threading.Condition()
    tid = threading.Thread(target=tx_thread,
                           args=(s, rem, windowSize, windowCond, timeOutInSec))
    tid.start()

    f = open(fileName, 'rb')
    blockNo = 1

    while True:
        b = f.read(blockSize)
        sizeOfBlockRead = len(b)
        if sizeOfBlockRead > 0:
            sendBlock(blockNo, b, s, rem, windowSize, windowCond)
        if sizeOfBlockRead == blockSize:
            blockNo += 1
        else:
            break

    f.close()
    global sendingDone
    sendingDone = True
    tid.join()


if __name__ == "__main__":
    # python sender.py senderPort windowSize timeOutInSec
    if len(sys.argv) != 4:
        print("Usage: python sender.py senderPort windowSize timeOutInSec")
    else:
        senderPort = int(sys.argv[1])
        windowSize = int(sys.argv[2])
        timeOutInSec = int(sys.argv[3])
        hostname = gethostbyname(gethostname())
        random.seed(5)
        main(hostname, senderPort, windowSize, timeOutInSec)

