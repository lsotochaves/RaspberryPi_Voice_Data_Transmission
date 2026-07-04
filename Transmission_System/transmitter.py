import struct
import threading
import time

import RPi.GPIO as GPIO
import sounddevice as sd
from pyrf24 import RF24, RF24_PA_MAX, RF24_1MBPS

# Audio parameters
RECORD_RATE = 48000
TARGET_RATE = 8000
DOWNSAMPLE_FACTOR = RECORD_RATE // TARGET_RATE  # 6
MAX_AUDIO_BYTES = 480_000
CHUNK = 1024

# GPIO
BUTTON_PIN = 17
LED_PIN = 26

# Radio
RADIO_CE_PIN = 25
RADIO_CSN_PIN = 0  # spidev0.0
TX_ADDRESS = b"1Node"

# Protocol
START_BYTE = 0xAA
PAYLOAD_SIZE = 27
PACKET_SIZE = 32
SEQ_END = 0xFFFF
PACKET_DELAY_S = 0.0


def init_radio():
    """Initialize the NRF24L01 radio in transmit mode."""
    radio = RF24(RADIO_CE_PIN, RADIO_CSN_PIN)
    if not radio.begin():
        raise RuntimeError("NRF24L01 not responding")
    radio.setPALevel(RF24_PA_MAX)
    radio.setDataRate(RF24_1MBPS)
    radio.setPayloadSize(PACKET_SIZE)
    radio.setChannel(76)
    radio.openWritingPipe(TX_ADDRESS)
    radio.stopListening()
    return radio


def init_button():
    """Configure GPIO17 as input with internal pull-up."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def init_led():
    """Configure the status LED on GPIO26."""
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.HIGH)


def _blink_loop(stop_event, interval=0.15):
    """Toggle the LED until stop_event is set."""
    while not stop_event.is_set():
        GPIO.output(LED_PIN, GPIO.LOW)
        stop_event.wait(interval)
        GPIO.output(LED_PIN, GPIO.HIGH)
        stop_event.wait(interval)


def find_input_device():
    """Return the ALSA device index for the INMP441 microphone."""
    for i, dev in enumerate(sd.query_devices()):
        if "googlevoicehat" in dev["name"].lower() and dev["max_input_channels"] > 0:
            return i
    raise RuntimeError("INMP441 (googlevoicehat) not found")


def record_audio():
    """Record raw audio while the push-to-talk button is held."""
    raw_chunks = []
    total = 0

    with sd.RawInputStream(
        samplerate=RECORD_RATE, channels=2, dtype="int32", device=find_input_device(), blocksize=CHUNK
    ) as stream:
        while GPIO.input(BUTTON_PIN) == GPIO.LOW and total < MAX_AUDIO_BYTES:
            data, _ = stream.read(CHUNK)
            raw_chunks.append(bytes(data))
            total += CHUNK // DOWNSAMPLE_FACTOR

    return b"".join(raw_chunks)


def process_audio(raw_data):
    """Downsample 48 kHz int32 stereo to 8 kHz uint8 mono."""
    buffer = bytearray()
    frame_size = 8  # 2 channels × 4 bytes (int32)
    total_frames = len(raw_data) // frame_size

    for start in range(0, total_frames - DOWNSAMPLE_FACTOR + 1, DOWNSAMPLE_FACTOR):
        if len(buffer) >= MAX_AUDIO_BYTES:
            break
        offset = start * frame_size
        sample_int32 = struct.unpack("<i", raw_data[offset : offset + 4])[0]
        sample_uint8 = (sample_int32 >> 24) + 128
        buffer.append(sample_uint8 & 0xFF)

    return bytes(buffer)


def build_packet(seq, data_chunk):
    """Build a 32-byte packet with header, payload and CRC."""
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
    """Split the audio buffer into 27-byte packets plus an end frame."""
    packets = []

    for i in range(0, len(audio_buffer), PAYLOAD_SIZE):
        chunk = audio_buffer[i : i + PAYLOAD_SIZE]
        seq = i // PAYLOAD_SIZE
        packets.append(build_packet(seq, chunk))

    packets.append(build_packet(SEQ_END, b"\x00" * PAYLOAD_SIZE))
    return packets


def transmit(radio, packets):
    """Send all packets sequentially over the radio link."""
    for i, packet in enumerate(packets):
        radio.write(packet)
        if PACKET_DELAY_S > 0:
            time.sleep(PACKET_DELAY_S)

    print(f"Transmitted {len(packets)} packets")


def main():
    """Main loop: wait for button press, record, process and transmit."""
    radio = init_radio()
    init_button()
    init_led()

    print("Transmitter ready. Hold button to record.")

    try:
        while True:
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                print("Recording...")
                blink_stop = threading.Event()
                blink_thread = threading.Thread(target=_blink_loop, args=(blink_stop,))
                blink_thread.start()

                raw = record_audio()
                blink_stop.set()
                blink_thread.join()

                audio = process_audio(raw)
                print(f"Recorded {len(audio)} bytes ({len(audio) / TARGET_RATE:.1f}s)")

                GPIO.output(LED_PIN, GPIO.HIGH)
                packets = build_all_packets(audio)
                transmit(radio, packets)

                GPIO.output(LED_PIN, GPIO.LOW)
                time.sleep(3)
                GPIO.output(LED_PIN, GPIO.HIGH)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
