import struct
import time

import RPi.GPIO as GPIO
import sounddevice as sd
from pyrf24 import RF24, RF24_PA_MAX, RF24_250KBPS

# ── Audio parameters ──
RECORD_RATE = 48000
TARGET_RATE = 8000
DOWNSAMPLE_FACTOR = RECORD_RATE // TARGET_RATE  # 6
MAX_AUDIO_BYTES = 480_000
CHUNK = 1024

# ── GPIO ──
BUTTON_PIN = 17
LED_RECORDING_PIN = None  # TODO: set actual pin
LED_TRANSMITTING_PIN = None  # TODO: set actual pin

# ── Radio ──
RADIO_CE_PIN = 25
RADIO_CSN_PIN = 0  # spidev0.0
TX_ADDRESS = b"\xe7\xe7\xe7\xe7\xe7"

# ── Protocol ──
START_BYTE = 0xAA
PAYLOAD_SIZE = 27
PACKET_SIZE = 32
SEQ_END = 0xFFFF
PACKET_DELAY_S = 0.0


# ──────────────────────────────────────────────
#  Initialization
# ──────────────────────────────────────────────


def init_radio():
    radio = RF24(RADIO_CE_PIN, RADIO_CSN_PIN)
    if not radio.begin():
        raise RuntimeError("NRF24L01 not responding")
    radio.setPALevel(RF24_PA_MAX)
    radio.setDataRate(RF24_250KBPS)
    radio.setPayloadSize(PACKET_SIZE)
    radio.setChannel(100)
    radio.openWritingPipe(TX_ADDRESS)
    radio.stopListening()
    return radio


def init_button():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def init_leds():
    if LED_RECORDING_PIN is not None:
        GPIO.setup(LED_RECORDING_PIN, GPIO.OUT)
        GPIO.output(LED_RECORDING_PIN, GPIO.LOW)
    if LED_TRANSMITTING_PIN is not None:
        GPIO.setup(LED_TRANSMITTING_PIN, GPIO.OUT)
        GPIO.output(LED_TRANSMITTING_PIN, GPIO.LOW)


# ──────────────────────────────────────────────
#  LED helpers
# ──────────────────────────────────────────────


def led_recording(state):
    if LED_RECORDING_PIN is not None:
        GPIO.output(LED_RECORDING_PIN, GPIO.HIGH if state else GPIO.LOW)


def led_transmitting(state):
    if LED_TRANSMITTING_PIN is not None:
        GPIO.output(LED_TRANSMITTING_PIN, GPIO.HIGH if state else GPIO.LOW)


# ──────────────────────────────────────────────
#  Audio capture and processing
# ──────────────────────────────────────────────


def record_audio():
    raw_chunks = []
    total = 0

    with sd.RawInputStream(
        samplerate=RECORD_RATE, channels=2, dtype="int32", device=1, blocksize=CHUNK
    ) as stream:
        while GPIO.input(BUTTON_PIN) == GPIO.LOW and total < MAX_AUDIO_BYTES:
            data, _ = stream.read(CHUNK)
            raw_chunks.append(bytes(data))
            total += CHUNK // DOWNSAMPLE_FACTOR

    return b"".join(raw_chunks)


def process_audio(raw_data):
    buffer = bytearray()
    frame_size = 8  # 2 channels × 4 bytes (int32)
    total_frames = len(raw_data) // frame_size

    for start in range(0, total_frames - DOWNSAMPLE_FACTOR + 1, DOWNSAMPLE_FACTOR):
        if len(buffer) >= MAX_AUDIO_BYTES:
            break
        acc = 0
        for j in range(DOWNSAMPLE_FACTOR):
            offset = (start + j) * frame_size
            sample_int32 = struct.unpack("<i", raw_data[offset : offset + 4])[0]
            acc += sample_int32
        avg = acc // DOWNSAMPLE_FACTOR
        sample_uint8 = (avg >> 24) + 128
        buffer.append(sample_uint8 & 0xFF)

    return bytes(buffer)


# ──────────────────────────────────────────────
#  Packet building
# ──────────────────────────────────────────────


def build_packet(seq, data_chunk):
    seq_high = (seq >> 8) & 0xFF
    seq_low = seq & 0xFF
    length = len(data_chunk)

    padded = data_chunk.ljust(PAYLOAD_SIZE, b"\x00")

    crc_sum = START_BYTE + seq_high + seq_low + length
    for b in padded:
        crc_sum += b
    crc = crc_sum & 0xFF

    packet = bytes([START_BYTE, seq_high, seq_low, length]) + padded + bytes([crc])
    return packet


def build_all_packets(audio_buffer):
    packets = []

    for i in range(0, len(audio_buffer), PAYLOAD_SIZE):
        chunk = audio_buffer[i : i + PAYLOAD_SIZE]
        seq = i // PAYLOAD_SIZE
        packets.append(build_packet(seq, chunk))

    packets.append(build_packet(SEQ_END, b"\x00" * PAYLOAD_SIZE))
    return packets


# ──────────────────────────────────────────────
#  Transmission
# ──────────────────────────────────────────────


def transmit(radio, packets):
    for i, packet in enumerate(packets):
        radio.write(packet)
        if PACKET_DELAY_S > 0:
            time.sleep(PACKET_DELAY_S)

    print(f"Transmitted {len(packets)} packets")


# ──────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────


def main():
    radio = init_radio()
    init_button()
    init_leds()

    print("Transmitter ready. Hold button to record.")

    try:
        while True:
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                led_recording(True)
                print("Recording...")

                raw = record_audio()
                led_recording(False)

                audio = process_audio(raw)
                print(f"Recorded {len(audio)} bytes ({len(audio) / TARGET_RATE:.1f}s)")

                led_transmitting(True)
                packets = build_all_packets(audio)
                transmit(radio, packets)
                led_transmitting(False)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
