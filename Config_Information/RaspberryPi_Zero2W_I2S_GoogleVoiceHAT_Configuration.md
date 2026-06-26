# Raspberry Pi Zero 2 W - I2S and Google Voice HAT Configuration

## Objective

Configure the Raspberry Pi Zero 2 W to expose the INMP441 I2S microphone
as an ALSA capture device using the Google Voice HAT sound card overlay.

------------------------------------------------------------------------

## Operating System

-   Raspberry Pi OS Trixie
-   Kernel: `6.18.34+rpt-rpi-v8`

------------------------------------------------------------------------

## 1. Enable SPI and I2S

Edit:

``` bash
sudo nano /boot/firmware/config.txt
```

Ensure the following lines are present:

``` text
dtparam=spi=on
dtparam=i2s=on
dtoverlay=googlevoicehat-soundcard
```

Reboot:

``` bash
sudo reboot
```

------------------------------------------------------------------------

## 2. Verify the I2S Peripheral

``` bash
sudo pinctrl get 18-21
```

Expected:

``` text
18: a0    ...  // GPIO18 = PCM_CLK
19: a0    ...  // GPIO19 = PCM_FS
20: a0    ...  // GPIO20 = PCM_DIN
21: a0    ...  // GPIO21 = PCM_DOUT
```

------------------------------------------------------------------------

## 3. Verify the Sound Card

``` bash
arecord -l
```

Expected:

``` text
card 1: sndrpigooglevoicehat_soundcard
device 0: Google voiceHAT SoundCard HiFi voicehat-hifi-0
```

This confirms:

-   The Google Voice HAT overlay loaded correctly.
-   ALSA created the capture device.
-   The I2S interface is operational.

------------------------------------------------------------------------

## 4. List Available PCM Devices

``` bash
arecord -L
```

Expected entries include:

-   `hw:CARD=sndrpigooglevoicehat_soundcard`
-   `plughw:CARD=sndrpigooglevoicehat_soundcard`

------------------------------------------------------------------------

## 5. Record Audio

``` bash
arecord -D plughw:1,0 test.wav
```

or

``` bash
arecord -D plughw:1,0 -f S32_LE -r 48000 test.wav
```

Terminate with **Ctrl+C**.

------------------------------------------------------------------------

## 6. Verify the Recording

``` bash
ls -lh test.wav
```

``` bash
file test.wav
```

``` bash
hexdump -C test.wav | head
```

or

``` bash
xxd test.wav | head
```

------------------------------------------------------------------------

## Configuration Summary

  Item                          Status
  ----------------------------- --------
  SPI Enabled                   ✅
  I2S Enabled                   ✅
  Google Voice HAT Overlay      ✅
  GPIO Configured for PCM/I2S   ✅
  ALSA Capture Device Created   ✅
  Audio Recording Functional    ✅
