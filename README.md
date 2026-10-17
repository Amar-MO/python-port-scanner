# python-port-scanner

A multithreaded TCP port scanner written in Python. It scans a single IPv4 address or a whole CIDR range using only the standard library.

I built it to practise networking fundamentals from the Cisco Networking Basics course: IPv4 addressing and subnetting, TCP connections, and ports.

## Legal and ethical use

Only scan devices and networks that you own or have explicit permission to scan. Scanning other people's systems can be illegal and may break the rules of your school, workplace or network provider. Testing on `127.0.0.1` (your own machine) is always safe.

## Features

- Scans a single IPv4 address (`192.168.1.10`) or a CIDR range (`192.168.1.0/24`)
- Skips the network and broadcast addresses of a range automatically
- Checks ports 1 to 65535 on each address
- Uses a thread pool so many ports are checked at the same time
- Validates input and rejects invalid addresses and IPv6
- Prints progress after each address and the total scan time

## Requirements

- Python 3
- No external libraries (it uses `socket`, `ipaddress`, `time` and `concurrent.futures`)

## Usage

```
python scanner.py
```

Enter a target when asked, for example `127.0.0.1` or `192.168.1.0/24`.

Example output:

```
What do you want to scan?
127.0.0.1
Scanning 127.0.0.1/32 (ports 1-65535)
Port 135 on 127.0.0.1 is listening
Port 445 on 127.0.0.1 is listening
Port 8000 on 127.0.0.1 is listening
Finished 127.0.0.1
Scan took 12.57 seconds
```

Settings (`TIMEOUT`, `WORKERS`, `FIRST_PORT`, `LAST_PORT`) are constants at the top of `scanner.py`.

## How it works

1. **Input and subnetting:** the `ipaddress` module turns text like `192.168.1.0/24` into a network object and lists its usable host addresses.
2. **TCP connect scan:** for each port, a socket tries to complete the TCP three-way handshake with `connect_ex`. If it succeeds, the port is open.
3. **Threading:** a `ThreadPoolExecutor` runs many of these checks at once. The scanner spends nearly all its time waiting for replies, so the waits overlap.
4. **One address at a time:** the list of jobs is built per address, so memory use doesn't grow with the size of the range.

## Performance

Tested on `127.0.0.1` with a 0.01 second timeout and 100 workers:

| Version | Ports | Time |
|---|---|---|
| One port at a time | 1-1249 | 20.2 s |
| Thread pool | 1-1249 | 0.24 s |
| Thread pool | 1-65535 | 12.6 s |

## Challenges and what I learned

**Choosing a timeout.** My first full scan used a 1 second timeout and took ages to find even the first open port. Dropping it to 1 millisecond made testing usable, but it taught me the trade-off: a short timeout is fast on my own machine, while on a real network replies take longer, so open ports would be missed without any error. That is why the default is flagged as tuned for local scanning. I also noticed that closed ports on `127.0.0.1` took about as long as the timeout to fail on my Windows laptop, which made long timeouts impractical for local tests.

**Making it fast with threads.** Checking one port at a time took 20.2 seconds for 1,249 ports. Almost all of that time was spent waiting for the network, not computing, so a thread pool can overlap the waits. With 100 workers the same scan took 0.24 seconds, about 84 times faster, and found the same open ports.

**Memory on large ranges.** Building one list of every (address, port) pair would be about 16.6 million pairs for a `/24`, which I estimated at over 1 GB (an estimate, not a measurement). I changed the scan to build the jobs for one address at a time and reuse the same pool, so memory no longer grows with the size of the range.

**Subnetting in practice.** My early tests rejected inputs like `192.168.4.5/24`. The reason is that the address has host bits set, so it isn't the start of its block, which is the same subnetting idea from my course. Setting `strict=False` accepts it and uses the real network, `192.168.4.0/24`.

**Errors that hide.** A bare `except` made every bad input look the same and would have hidden real bugs. I changed it to catch `ValueError` only. I also found that IPv6 input would crash inside a worker thread because the socket is IPv4 only, so the input check now rejects IPv6 up front.

## Limitations

- **IPv4 and TCP only.** IPv6 and UDP are not supported.
- **The default timeout is tuned for scanning your own machine.** On a real network, replies take longer than 10 ms, so open ports may be missed. Raise `TIMEOUT` (around 0.5 is safer) for other devices, which makes scans slower.
- **Open or not, nothing more.** A failed connection could mean the port is closed or filtered by a firewall, and the scanner doesn't tell them apart.
- **Large ranges take a long time,** because every port on every address is checked.
- **Windows:** on my laptop, a long timeout makes scans of `127.0.0.1` very slow.
