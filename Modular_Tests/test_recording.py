import sounddevice as sd
import RPi.GPIO as GPIO
import struct
import wave
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

            with sd.RawInputStream(samplerate=RECORD_RATE, channels=2, dtype='int32',
                                   device=1, blocksize=CHUNK) as stream:
                total = 0
                while GPIO.input(BUTTON_PIN) == GPIO.LOW and total < MAX_BYTES:
                    data, _ = stream.read(CHUNK)
                    raw_chunks.append(bytes(data))
                    total += CHUNK // DOWNSAMPLE_FACTOR

            # Unir todos los chunks crudos
            raw = b''.join(raw_chunks)

            # Cada frame = 2 canales × 4 bytes (int32) = 8 bytes
            # Tomar canal L, 1 de cada 6 frames
            buffer = bytearray()
            frame_size = 8  # 2 canales × 4 bytes
            for i in range(0, len(raw), frame_size * DOWNSAMPLE_FACTOR):
                if len(buffer) >= MAX_BYTES:
                    break
                sample_bytes = raw[i:i+4]  # Canal L (primeros 4 bytes del frame)
                if len(sample_bytes) == 4:
                    sample_int32 = struct.unpack('<i', sample_bytes)[0]
                    sample_uint8 = (sample_int32 >> 24) + 128
                    buffer.append(sample_uint8 & 0xFF)

            print(f"Grabación finalizada: {len(buffer)} bytes ({len(buffer) / TARGET_RATE:.1f} seg)")

            with wave.open("test.wav", "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(1)
                wf.setframerate(TARGET_RATE)
                wf.writeframes(buffer)
            print("Guardado como test.wav")

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nSaliendo...")
finally:
    GPIO.cleanup()
