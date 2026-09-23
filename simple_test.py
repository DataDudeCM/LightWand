import socket
import time

IP = "192.168.1.8"
PORT = 7777
NUM_LEDS = 50

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

frame = bytes([255, 0, 0] * NUM_LEDS)

print("Sending red frame...")
sock.sendto(frame, (IP, PORT))

time.sleep(3)

print("Sending off frame...")
sock.sendto(bytes([0, 0, 0] * NUM_LEDS), (IP, PORT))