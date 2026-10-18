import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = 0.01      # How many seconds to wait for each port
WORKERS = 100       # The amount of ports that are checked at the same time
FIRST_PORT = 1
LAST_PORT = 65536


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

while True:
    ports_input = input("Would you like to scan: One port(type a port number)/ All ports(a)/ well-known ports(w)/ a range(r).\n")
    if ports_input.isdigit():
        if int(ports_input) > 0 and int(ports_input) < 65536:
            FIRST_PORT = int(ports_input)
            LAST_PORT = int(ports_input) + 1
            break
        else:
            print("Value is out of range, please try again.")
    elif ports_input == "a" or ports_input == "A":
        FIRST_PORT = 1
        LAST_PORT = 65536
        break
    elif ports_input == "w" or ports_input == "W":
        FIRST_PORT = 1
        LAST_PORT = 1024
        break
    elif ports_input == "r" or ports_input == "R":
        FIRST_PORT = input("Please input first port: \n")
        if not FIRST_PORT.isdigit():
            print("Invalid input, please try again.")
            continue
        elif int(FIRST_PORT) <= 0 or int(FIRST_PORT) > 65535:
            print("Invalid input, please try again.")
            continue
        else:
            FIRST_PORT = int(FIRST_PORT)
        LAST_PORT = input("Please input last port: \n")
        if not LAST_PORT.isdigit():
            print("Invalid input, please try again.")
            continue
        elif int(LAST_PORT) <= 0 or int(LAST_PORT) > 65535 or int(LAST_PORT) < int(FIRST_PORT):
            print("Invalid input, please try again.")
            continue

        
        LAST_PORT = int(LAST_PORT) + 1
        break
    else:
        print("Invalid input, please try again.")
        



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
                print(f"Port {port} on {host_ip} is listening")

        print(f"Finished {ip}")

end_time = time.time()
print(f"Scan took {end_time - start_time:.2f} seconds")    