import sounddevice as sd
import RPi.GPIO as GPIO
import time

BUTTON_PIN = 17
SAMPLE_RATE = 8000
MAX_BYTES = 480_000
CHUNK = 1024

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Listo. Mantenga presionado el botón para grabar...")

try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            print("Grabando...")
            buffer = bytearray()

            with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype='uint8',
                                   device=1, blocksize=CHUNK) as stream:
                while GPIO.input(BUTTON_PIN) == GPIO.LOW and len(buffer) < MAX_BYTES:
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
    GPIO.cleanup()
