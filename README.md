# Reliable Data Transmission over an Unreliable Network

## Overview
This project implements **reliable file transfer over UDP**, simulating packet loss and handling it using a **Sliding Window protocol with Go-Back-N (GBN)**.

Both sender and receiver are multi-threaded and cooperate to ensure correct file delivery despite unreliable communication.

## Core Concepts
- UDP-based file transfer
- Sliding Window (size N)
- Go-Back-N retransmission strategy
- Timeout and duplicate ACK handling
- Simulated packet loss

## Architecture
- **Sender**
  - Main thread: sends data blocks
  - Helper thread: manages window, timeouts, retransmissions
- **Receiver**
  - Helper thread: receives blocks, sends ACKs
  - Main thread: writes data to file

## Technologies
- Python
- UDP sockets
- Multithreading
- `pickle` for message encoding
- Select-based timeouts

## Skills Demonstrated
- Transport layer protocols
- Reliability mechanisms
- Concurrent programming
- Fault-tolerant communication

## Academic Context
Computer Networks (TPC2 – 2025/2026)
