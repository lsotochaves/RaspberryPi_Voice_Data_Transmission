import sounddevice as sd
import gpiod
import time

BUTTON_PIN = 17
SAMPLE_RATE = 8000
MAX_BYTES = 480_000
CHUNK = 1024

chip = gpiod.Chip('gpiochip4')
line = chip.get_line(BUTTON_PIN)
line.request(consumer="ptt", type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)

print("Listo. Mantenga presionado el botón para grabar...")

try:
    while True:
        if line.get_value() == 0:
            print("Grabando...")
            buffer = bytearray()

            with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype='uint8',
                                   device='plughw:1,0', blocksize=CHUNK) as stream:
                while line.get_value() == 0 and len(buffer) < MAX_BYTES:
                    data, _ = stream.read(CHUNK)
                    buffer.extend(data)

            if len(buffer) >= MAX_BYTES:
                print(f"Límite alcanzado: {len(buffer)} bytes")
            else:
                print(f"Grabación finalizada: {len(buffer)} bytes ({len(buffer) / SAMPLE_RATE:.1f} seg)")

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nSaliendo...")
finally:
    line.release()
