# Proyecto de Comunicación Inalámbrica de Audio

Sistema portátil de comunicación inalámbrica de voz entre dos dispositivos autónomos (transmisor y receptor) basados en Raspberry Pi Zero W.

---

## Hardware

| Componente | Función |
|---|---|
| Raspberry Pi Zero W | Procesamiento principal |
| INMP441 (I2S, Google Voice HAT) | Captura de voz |
| NRF24L01+PA+LNA | Enlace inalámbrico 2.4 GHz |
| Parlante USB o DAC | Reproducción de audio |
| Botón en GPIO17 | Push-to-talk |
| LEDs indicadores | Señalización de estados |
| Batería portátil | Alimentación autónoma |

### Conexiones NRF24L01

| NRF24L01 | Raspberry Pi |
|---|---|
| CE | GPIO25 |
| CSN | CE0 (spidev0.0) |
| SPI | Bus SPI (habilitado en config.txt) |

### Botón

- GPIO17 → un extremo del botón
- GND → otro extremo del botón
- Pull-up interno habilitado por software

---

## Configuración del sistema operativo

Raspberry Pi OS Trixie. Requiere en `/boot/firmware/config.txt`:

```
dtparam=spi=on
dtparam=i2s=on
dtoverlay=googlevoicehat-soundcard
```

Dispositivo ALSA: `plughw:1,0`

---

## Parámetros de audio

| Parámetro | Valor |
|---|---|
| Frecuencia de muestreo | 8,000 Hz |
| Resolución | 8 bits por muestra |
| Tasa de datos | 64 kbps |
| Duración máxima | 60 segundos |
| Tamaño máximo del buffer | 480,000 bytes |

---

## Protocolo de transmisión

### Formato del paquete (29 bytes)

```
[START][SEQ_HIGH][SEQ_LOW][LEN][DATOS][CRC]
  1B      1B        1B     1B   27B    1B
```

| Campo | Tamaño | Descripción |
|---|---|---|
| START | 1 byte | Byte de sincronización (0xAA) |
| SEQ_HIGH | 1 byte | Byte alto del número de secuencia |
| SEQ_LOW | 1 byte | Byte bajo del número de secuencia |
| LEN | 1 byte | Cantidad de bytes válidos en DATOS |
| DATOS | 27 bytes | Muestras de audio PCM |
| CRC | 1 byte | Suma de verificación (byte bajo de la suma de todos los campos) |

### Trama de fin

SEQ = `0xFFFF` está reservado para señalar el fin del mensaje. Garantiza que ningún paquete de datos usa ese valor.

### Límites de secuencia

- Paquetes máximos por mensaje: 17,778 (480,000 ÷ 27)
- SEQ máximo utilizado: ~0x4E20, muy por debajo de 0xFFFF

---

## Plan de implementación

### Transmisor

1. Inicializar NRF24L01 (pyrf24)
2. Inicializar botón GPIO17 (gpiod, pull-up)
3. Esperar botón presionado
4. Mientras botón presionado: grabar audio en chunks con sounddevice
5. Verificar límite de 480,000 bytes durante grabación
6. Al soltar el botón (o alcanzar el límite): detener grabación
7. Dividir buffer en chunks de 24 bytes
8. Construir paquetes [START][SEQ_H][SEQ_L][LEN][DATOS][CRC]
9. Enviar paquetes secuencialmente
10. Enviar trama de fin (SEQ = 0xFFFF)

### Receptor

1. Inicializar NRF24L01 en modo escucha
2. Esperar paquetes
3. Verificar CRC de cada paquete
4. Almacenar datos válidos en buffer ordenado por SEQ
5. Detectar trama de fin (SEQ = 0xFFFF)
6. Reconstruir audio desde el buffer
7. Reproducir mensaje

---

## Dependencias

```
spidev
pyrf24
gpiod
sounddevice
```

Instalación:

```bash
pip install -r requirements.txt
```

---

## Estado actual

- [x] SPI habilitado y verificado
- [x] I2S y micrófono INMP441 funcional (ALSA)
- [x] NRF24L01 receptor básico funcional
- [x] Botón GPIO17 funcional (gpiod)
- [x] Protocolo de paquetes definido
- [ ] Grabación con límite de buffer
- [ ] Empaquetado y transmisión
- [ ] Recepción, verificación y reproducción
