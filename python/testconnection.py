import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.settimeout(3)

sock.sendto(
    b"LIGHTWAND_DISCOVER",
    ("192.168.137.255", 7777)
)

try:
    data, addr = sock.recvfrom(1024)
    print("Reply:", data, "from", addr)
except socket.timeout:
    print("No discovery reply")