import sounddevice as sd
import RPi.GPIO as GPIO
import numpy as np
from scipy.signal import decimate
import time

BUTTON_PIN = 17
RECORD_RATE = 48000
TARGET_RATE = 8000
DOWNSAMPLE_FACTOR = RECORD_RATE // TARGET_RATE  # 6
MAX_BYTES = 480_000
CHUNK = 1024

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Listo. Mantenga presionado el botón para grabar...")

try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            print("Grabando...")
            raw_chunks = []

            with sd.InputStream(samplerate=RECORD_RATE, channels=2, dtype='int32',
                                device=1, blocksize=CHUNK) as stream:
                while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    data, _ = stream.read(CHUNK)
                    raw_chunks.append(data[:, 0])  # Canal L (mono)

                    total_estimated = len(raw_chunks) * (CHUNK // DOWNSAMPLE_FACTOR)
                    if total_estimated >= MAX_BYTES:
                        print("Límite de buffer alcanzado")
                        break

            raw_audio = np.concatenate(raw_chunks)

            # Downsample 48kHz -> 8kHz con filtro anti-aliasing
            audio_8k = decimate(raw_audio, DOWNSAMPLE_FACTOR)

            # Cuantizar int32 -> uint8 (0-255)
            audio_8k = audio_8k / (2**31)           # Normalizar a [-1, 1]
            audio_uint8 = ((audio_8k + 1) * 127.5).clip(0, 255).astype(np.uint8)

            buffer = audio_uint8.tobytes()[:MAX_BYTES]

            print(f"Grabación finalizada: {len(buffer)} bytes ({len(buffer) / TARGET_RATE:.1f} seg)")

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nSaliendo...")
finally:
    GPIO.cleanup()
