# python-port-scanner

A multithreaded TCP port scanner written in Python. It scans a single IPv4 address or a whole CIDR range from the command line, using only the standard library.

I built it to practise the networking fundamentals from my Cisco Networking Basics course: IPv4 addressing and subnetting, TCP connections, and ports.

## Legal and ethical use

Only scan devices and networks that you own or have explicit permission to scan. Scanning other people's systems can be illegal and may break the rules of your school, workplace or network provider. Testing on `127.0.0.1` (your own machine) is always safe.

## Features

- Scans a single IPv4 address (`192.168.1.10`) or a CIDR range (`192.168.1.0/24`)
- Skips the network and broadcast addresses of a range automatically
- Choose which ports to scan: one port, a custom range, the well-known ports (1-1023, the default) or all ports (1-65535)
- Shows what a port is commonly used for (for example 443: HTTPS) when it finds one in its built-in table
- Uses a thread pool so many ports are checked at the same time
- Command-line options for the ports, timeout and number of workers, with a built-in `--help`
- Validates every input and gives a short error message, not a traceback, for bad values (invalid addresses, IPv6, out-of-range ports, non-positive timeouts)
- Prints progress after each address and the total scan time

## Requirements

- Python 3
- No external libraries (it uses `argparse`, `ipaddress`, `socket`, `time` and `concurrent.futures`)

## Usage

```
python scanner.py TARGET [-p PORTS] [-t TIMEOUT] [--workers WORKERS]
```

| Argument | Required? | Default | What it accepts |
|---|---|---|---|
| `TARGET` | Yes | none | A single IPv4 address (`192.168.1.10`) or a CIDR range (`192.168.1.0/24`) |
| `-p`, `--ports` | No | `w` | A single port (`80`), a range (`20-80`), `w` for the well-known ports (1-1023) or `a` for all ports (1-65535) |
| `-t`, `--timeout` | No | `0.5` | Seconds to wait for each port, above 0 |
| `--workers` | No | `100` | How many ports are checked at the same time, at least 1 |
| `-h`, `--help` | No | | Shows the usage and what each option does |

Examples:

```
python scanner.py 127.0.0.1
python scanner.py 127.0.0.1 -p 100-200 -t 0.01
python scanner.py 192.168.1.0/24 -p 22 -t 0.5
python scanner.py 127.0.0.1 -p a --workers 200
python scanner.py --help
```

Example output:

```
> python scanner.py 127.0.0.1 -t 0.01
Scanning 127.0.0.1/32 (ports 1-1023)
Port 135 on 127.0.0.1 is listening
Port 445 on 127.0.0.1 is listening
Port 623 on 127.0.0.1 is listening
Finished 127.0.0.1
Scan took 0.35 seconds
```

When an open port is in the built-in table, a hint is printed under it. For example, with a test web server running on port 8080:

```
Port 8080 on 127.0.0.1 is listening.
	Port commonly used for: HTTP alternate -> A second port often used for web servers and proxies.
```

Bad input is rejected with a clear message:

```
> python scanner.py 127.0.0.1 -t abc
usage: scanner.py [-h] [-p PORTS] [-t TIMEOUT] [--workers WORKERS] target
scanner.py: error: argument -t/--timeout: Timeout must be a number.
```

## How it works

1. **Command line:** `argparse` reads the target and options. Each one has its own checking function that converts the text and rejects bad values with a clear message.
2. **Subnetting:** the `ipaddress` module turns text like `192.168.1.0/24` into a network object and lists its usable host addresses.
3. **Port selection:** the ports option becomes a first and last port to scan.
4. **TCP connect scan:** for each port, a socket tries to complete the TCP three-way handshake with `connect_ex`. If it succeeds, the port is open.
5. **Threading:** a `ThreadPoolExecutor` runs many of these checks at once. The scanner spends nearly all its time waiting for replies, so the waits overlap.
6. **One address at a time:** the list of jobs is built per address, so memory use doesn't grow with the size of the range.
7. **Service hints:** open ports are looked up in a dictionary of commonly used ports. These are conventions, so a match is a hint, not proof of what is running.

## Performance

All tests were on `127.0.0.1` (my own machine) with 100 workers unless stated:

| Version | Timeout | Ports | Time |
|---|---|---|---|
| One port at a time | 0.01 s | 1-1249 | 20.2 s |
| Thread pool | 0.01 s | 1-1249 | 0.24 s |
| Thread pool | 0.01 s | 1-1023 | 0.35 s |
| Thread pool | 0.5 s (default) | 1-1023 | 5.65 s |
| Thread pool | 0.01 s | 1-65535 | 12.6 to 20.1 s (varied between runs) |
| Thread pool | 1 s | 1-65535 | 661.5 s |
| Thread pool, 14 addresses (`/28`) | 0.01 s | 1-1023 | 3.24 s |

The timeout is by far the biggest factor in scan time. Changing the worker count from 100 to 150 or 200 made no measurable difference for a scan of about 1,000 ports, and I haven't investigated why.

## What I learned

**Choosing a timeout.** My first full scan used a 1 second timeout and took ages to find even the first open port. Dropping it to 1 millisecond made testing usable, but it taught me the trade-off: a short timeout is fast on my own machine, while on a real network replies take longer, so open ports could be missed without any error. That is why the default is 0.5 seconds, and why I use `-t 0.01` for local tests. I also noticed that closed ports on `127.0.0.1` took about as long as the timeout to fail on my Windows laptop, which makes long timeouts slow for local scans.

**Making it fast with threads.** Checking one port at a time took 20.2 seconds for 1,249 ports. Almost all of that time was spent waiting for the network, not computing, so a thread pool can overlap the waits. With 100 workers the same scan took 0.24 seconds, about 84 times faster, and found the same open ports.

**Memory on large ranges.** Building one list of every (address, port) pair would be about 16.6 million pairs for a `/24`, which is roughly 1.5 GB by a rough estimate (not a measurement). The scan builds the jobs for one address at a time and reuses the same pool, so memory doesn't grow with the size of the range.

**Subnetting in practice.** My early tests rejected inputs like `192.168.4.5/24`. The reason is that the address has host bits set, so it isn't the start of its block, which is the same subnetting idea from my course. Setting `strict=False` accepts it and uses the real network, `192.168.4.0/24`.

**Errors that hide.** A bare `except` made every bad input look the same and could have hidden real bugs, so I changed it to catch `ValueError` only. IPv6 input would crash inside a worker thread because the socket is IPv4 only, so the address check rejects IPv6 up front.

**Port ranges and off-by-one errors.** Python's `range()` stops before its last value, so the scan loop needs the last port plus one to include it. I checked the definition of "well-known" ports against a reference instead of trusting my memory, and it is 1-1023 (port 0 is reserved).

**Testing what I actually ran.** One full scan took 661 seconds even though I thought I had set the timeout to 0.01. The edit hadn't been saved, so the program was still running the 1 second version, and the repeat with the saved value took about 20 seconds. The output also arrived in bursts during that slow run, because the thread pool returns results in the order the ports were submitted, so one slow batch holds back everything after it. The lesson was to check which version is really running before trusting a measurement.

**Command-line arguments.** I learned how `argparse` works by writing a small throwaway script first, to see the difference between required and optional arguments and what `type=` and `default=` do. Testing odd inputs taught me how it behaves: for example `-tw 0.01` is read as `-t` with the value `w`, and a second target is rejected because there is only one positional slot.

## Limitations

- **IPv4 and TCP only.** IPv6 and UDP are not supported.
- **Only tested on my own machine.** I haven't yet tested it against another device that has open ports, so the claim that a very short timeout can miss open ports on a real network is untested. The default timeout is 0.5 seconds for that reason.
- **Open or not, nothing more.** A failed connection could mean the port is closed or filtered by a firewall, and the scanner doesn't tell them apart.
- **Service names are conventions.** Any program can use any port, so "commonly used for" is a hint, not a guarantee. The table only covers about 17 common ports.
- **Large ranges take a long time,** because every chosen port on every address is checked, and addresses with no device still wait out the timeout on each port.
- **Output can arrive in bursts** on slow scans, because results are returned in port order.
- **No limit on `--workers`:** a very large value may cause errors or overwhelm a small network device.
- **Windows:** on my laptop, a long timeout makes scans of `127.0.0.1` very slow.

## Planned improvements

- Banner grabbing: reading what an open service says about itself
- Testing against another device I own, to measure how the timeout affects results on a real network