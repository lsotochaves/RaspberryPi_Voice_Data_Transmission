import struct
import time

import RPi.GPIO as GPIO
from pyrf24 import RF24, RF24_PA_LOW, RF24_1MBPS

# ── Audio parameters ──
TARGET_RATE = 8000
MAX_AUDIO_BYTES = 480_000

# ── GPIO ──
LED_RECEIVING_PIN = None  # TODO: set actual pin
LED_PLAYING_PIN = None  # TODO: set actual pin

# ── Radio ──
RADIO_CE_PIN = 25
RADIO_CSN_PIN = 0  # spidev0.0
RX_ADDRESS = b"1Node"

# ── Protocol ──
START_BYTE = 0xAA
PAYLOAD_SIZE = 27
PACKET_SIZE = 32
SEQ_END = 0xFFFF
MAX_PACKETS = 17_778


# ──────────────────────────────────────────────
#  Initialization
# ──────────────────────────────────────────────


def init_radio():
    radio = RF24(RADIO_CE_PIN, RADIO_CSN_PIN)
    if not radio.begin():
        raise RuntimeError("NRF24L01 not responding")
    radio.setPALevel(RF24_PA_LOW)
    radio.setDataRate(RF24_1MBPS)
    radio.setPayloadSize(PACKET_SIZE)
    radio.setChannel(76)
    radio.openReadingPipe(1, RX_ADDRESS)
    radio.startListening()
    return radio


def init_leds():
    GPIO.setmode(GPIO.BCM)
    if LED_RECEIVING_PIN is not None:
        GPIO.setup(LED_RECEIVING_PIN, GPIO.OUT)
        GPIO.output(LED_RECEIVING_PIN, GPIO.LOW)
    if LED_PLAYING_PIN is not None:
        GPIO.setup(LED_PLAYING_PIN, GPIO.OUT)
        GPIO.output(LED_PLAYING_PIN, GPIO.LOW)


# ──────────────────────────────────────────────
#  LED helpers
# ──────────────────────────────────────────────


def led_receiving(state):
    if LED_RECEIVING_PIN is not None:
        GPIO.output(LED_RECEIVING_PIN, GPIO.HIGH if state else GPIO.LOW)


def led_playing(state):
    if LED_PLAYING_PIN is not None:
        GPIO.output(LED_PLAYING_PIN, GPIO.HIGH if state else GPIO.LOW)


# ──────────────────────────────────────────────
#  Packet parsing and validation
# ──────────────────────────────────────────────


def verify_crc(packet):
    crc_sum = 0
    for b in packet[:31]:
        crc_sum += b
    return (crc_sum & 0xFF) == packet[31]


def parse_packet(packet):
    if len(packet) != PACKET_SIZE:
        return None
    if packet[0] != START_BYTE:
        return None
    if not verify_crc(packet):
        return None

    seq = (packet[1] << 8) | packet[2]
    length = packet[3]

    if length > PAYLOAD_SIZE:
        return None

    data = packet[4 : 4 + length]
    return seq, data


# ──────────────────────────────────────────────
#  Reception
# ──────────────────────────────────────────────


def receive_message(radio):
    buffer = {}
    packets_received = 0
    crc_errors = 0

    led_receiving(True)
    print("Waiting for transmission...")

    while True:
        if radio.available():
            raw = radio.read(PACKET_SIZE)
            result = parse_packet(raw)

            if result is None:
                crc_errors += 1
                continue

            seq, data = result

            if seq == SEQ_END:
                break

            if seq not in buffer and seq < MAX_PACKETS:
                buffer[seq] = data
                packets_received += 1

    led_receiving(False)
    print(f"Received {packets_received} packets ({crc_errors} CRC errors)")
    return buffer


# ──────────────────────────────────────────────
#  Audio reconstruction
# ──────────────────────────────────────────────


def reconstruct_audio(buffer):
    if not buffer:
        return b""

    max_seq = max(buffer.keys())
    audio = bytearray()

    for seq in range(max_seq + 1):
        if seq in buffer:
            audio.extend(buffer[seq])
        else:
            silence = bytes(PAYLOAD_SIZE)
            audio.extend(silence)

    if len(audio) > MAX_AUDIO_BYTES:
        audio = audio[:MAX_AUDIO_BYTES]

    return bytes(audio)


# ──────────────────────────────────────────────
#  Playback (Bluetooth – tentative)
# ──────────────────────────────────────────────


def save_audio(pcm_data, filename="received_audio.wav"):
    if not pcm_data:
        print("No audio to save")
        return

    import wave

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(1)
        wf.setframerate(TARGET_RATE)
        wf.writeframes(pcm_data)

    duration = len(pcm_data) / TARGET_RATE
    print(f"Saved {duration:.1f}s of audio to {filename}")


# ──────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────


def main():
    radio = init_radio()
    init_leds()

    print("Receiver ready. Listening for messages.")

    try:
        while True:
            buffer = receive_message(radio)
            pcm_data = reconstruct_audio(buffer)

            if pcm_data:
                print(f"Reconstructed {len(pcm_data)} bytes ({len(pcm_data) / TARGET_RATE:.1f}s)")
                save_audio(pcm_data)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
