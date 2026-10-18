import argparse
import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = 0.5       # How many seconds to wait for each port
WORKERS = 100       # The amount of ports that are checked at the same time
FIRST_PORT = 1
LAST_PORT = 65536
PORTS_DIC = {
    21: "FTP -> Sending files to and from a server.",
    22: "SSH -> Secure remote command-line access to a machine.",
    23: "Telnet -> Remote command-line access with no encryption.",
    25: "SMTP -> Mail servers passing email to each other.",
    53: "DNS -> Turning names like example.com into IP addresses.",
    80: "HTTP -> Ordinary, unencrypted web pages.",
    110: "POP3 -> Downloading email from a mail server.",
    143: "IMAP -> Reading email that stays on the server.",
    443: "HTTPS -> Web pages encrypted with TLS.",
    465: "SMTPS -> Sending email to a mail server over an encrypted connection.",
    587: "SMTP submission -> Sending email from a mail client to its server.",
    993: "IMAPS -> IMAP wrapped in encryption.",
    995: "POP3S -> POP3 wrapped in encryption.",
    3306: "MySQL -> A common database server.",
    3389: "RDP -> Windows Remote Desktop.",
    5432: "PostgreSQL -> Another common database server.",
    8080: "HTTP alternate -> A second port often used for web servers and proxies.",
}


# These functions check what the user typed, and argparse calls them for us
def valid_target(text):
    try:
        network = ipaddress.ip_network(text, strict=False)
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid input, please enter a valid IPv4 address or address range.")
    if network.version != 4:
        raise argparse.ArgumentTypeError("Only IPv4 is supported, please try again.")
    return network


def valid_ports(text):
    if text.isdigit():
        if int(text) > 0 and int(text) < 65536:
            return int(text), int(text) + 1
        else:
            raise argparse.ArgumentTypeError("Value is out of range, ports go from 1 to 65535.")
    elif text == "a" or text == "A":
        return 1, 65536
    elif text == "w" or text == "W":
        return 1, 1024
    else:
        parts = text.split("-")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise argparse.ArgumentTypeError("Invalid input, use a port number, a range like 20-80, w or a.")
        first = int(parts[0])
        last = int(parts[1])
        if first <= 0 or last > 65535 or last < first:
            raise argparse.ArgumentTypeError("Invalid range, ports go from 1 to 65535 and the first can't be above the last.")
        return first, last + 1


def valid_timeout(text):
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError("Timeout must be a number.")
    if value <= 0:
        raise argparse.ArgumentTypeError("Timeout must be above 0.")
    return value


def valid_workers(text):
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError("Workers must be a whole number of at least 1.")
    return int(text)


parser = argparse.ArgumentParser(
    description="A multithreaded TCP port scanner for IPv4 addresses and CIDR ranges.",
    epilog="Only scan devices and networks that you own or have permission to scan.")
parser.add_argument("target", type=valid_target,
                    help="IPv4 address or CIDR range, for example 127.0.0.1 or 192.168.1.0/24")
parser.add_argument("-p", "--ports", type=valid_ports, default="w",
                    help="a port (80), a range (20-80), w for well-known ports 1-1023, or a for all ports (default: w)")
parser.add_argument("-t", "--timeout", type=valid_timeout, default=TIMEOUT,
                    help="seconds to wait for each port (default: 0.5)")
parser.add_argument("--workers", type=valid_workers, default=WORKERS,
                    help="how many ports are checked at the same time (default: 100)")
args = parser.parse_args()

network = args.target
FIRST_PORT, LAST_PORT = args.ports
TIMEOUT = args.timeout
WORKERS = args.workers


def is_listening(ip, port, time_out=TIMEOUT):
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as soc:
        soc.settimeout(time_out)
        return soc.connect_ex((ip, port)) == 0


def check_pair(pair):
    
    ip, port = pair
    return is_listening(ip, port)


print(f"Scanning {network} (ports {FIRST_PORT}-{LAST_PORT - 1})")
start_time = time.time()

with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    for host in network.hosts():
        ip = str(host)

        
        pairs = []
        for port in range(FIRST_PORT, LAST_PORT):
            pairs.append((ip, port))

        results = executor.map(check_pair, pairs)
        for (host_ip, port), is_open in zip(pairs, results):
            if is_open:
                if port in PORTS_DIC:
                    print(f"Port {port} on {host_ip} is listening.\n\tPort commonly used for: {PORTS_DIC[port]}")
                else:
                    print(f"Port {port} on {host_ip} is listening")

        print(f"Finished {ip}")

end_time = time.time()
print(f"Scan took {end_time - start_time:.2f} seconds")   