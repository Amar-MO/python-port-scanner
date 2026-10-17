import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = 0.01      # How many second to wait for each port
WORKERS = 100       # The ammount of ports that are checked are the same time
FIRST_PORT = 1
LAST_PORT = 65535

# Keep asking until the user gives a valid IPv4 address or range
while True:
    try:
        user_input = input("What do you want to scan?\n")
        network = ipaddress.ip_network(user_input, strict=False)
    except ValueError:
        print("Invalid input, please enter a valid IPv4 address or address range.")
        continue
    if network.version != 4:
        print("Only IPv4 is supported, please try again.")
        continue
    break


def is_listening(ip, port, time_out=TIMEOUT):
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as soc:
        soc.settimeout(time_out)
        return soc.connect_ex((ip, port)) == 0


def check_pair(pair):
    
    ip, port = pair
    return is_listening(ip, port)


print(f"Scanning {network} (ports {FIRST_PORT}-{LAST_PORT})")
start_time = time.time()

with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    for host in network.hosts():
        ip = str(host)

        
        pairs = []
        for port in range(FIRST_PORT, LAST_PORT + 1):
            pairs.append((ip, port))

        results = executor.map(check_pair, pairs)
        for (host_ip, port), is_open in zip(pairs, results):
            if is_open:
                print(f"Port {port} on {host_ip} is listening")

        print(f"Finished {ip}")

end_time = time.time()
print(f"Scan took {end_time - start_time:.2f} seconds")    