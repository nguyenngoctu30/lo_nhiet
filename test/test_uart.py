import time
import serial

PORT = "COM8"
BAUD = 115200

packet = "GA,47.09,3.30,160.00,0.0654,0.001,0.0000,1\n"

with serial.Serial(PORT, BAUD, timeout=2) as ser:
    time.sleep(0.5)
    ser.write(packet.encode("utf-8"))
    print(">> PC da gui:", packet.strip())
    reply = ser.readline().decode("utf-8", errors="ignore").strip()
    print("<< STM32 phan hoi:", reply if reply else "(KHONG THAY PHAN HOI - Kiem tra day TX/RX)")