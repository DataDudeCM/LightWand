import socket
import time

WAND_IP = "192.168.1.8"
WAND_PORT = 7777
NUM_LEDS = 100

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_frame(pixels):
    frame = bytearray()

    for r, g, b in pixels:
        frame.extend([r, g, b])

    sock.sendto(frame, (WAND_IP, WAND_PORT))


def solid_color(r, g, b, seconds=1):
    pixels = [(r, g, b)] * NUM_LEDS
    send_frame(pixels)
    time.sleep(seconds)


print("Testing solid colors...")

solid_color(255, 0, 0)
solid_color(0, 255, 0)
solid_color(0, 0, 255)

print("Moving dot...")

for _ in range(3):

    for pos in range(NUM_LEDS):

        pixels = [(0, 0, 0)] * NUM_LEDS
        pixels[pos] = (255, 255, 255)

        send_frame(pixels)

        time.sleep(0.03)


print("Turning LEDs off.")

send_frame([(0, 0, 0)] * NUM_LEDS)

sock.close()