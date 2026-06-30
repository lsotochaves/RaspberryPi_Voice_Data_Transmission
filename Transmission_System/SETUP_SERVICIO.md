# Configuración de servicios systemd

Instrucciones para que los scripts arranquen automáticamente al alimentar cada Raspberry Pi.

---

## Transmisor (Pi 2 Zero)

```bash
sudo cp transmitter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable transmitter.service
sudo systemctl start transmitter.service
```

## Receptor (Pi Zero)

```bash
sudo cp receiver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable receiver.service
sudo systemctl start receiver.service
```

---

## Comandos útiles

Ver estado del servicio:

```bash
sudo systemctl status transmitter.service
sudo systemctl status receiver.service
```

Ver logs en tiempo real:

```bash
sudo journalctl -u transmitter.service -f
sudo journalctl -u receiver.service -f
```

Detener el servicio:

```bash
sudo systemctl stop transmitter.service
sudo systemctl stop receiver.service
```

Deshabilitar el inicio automático:

```bash
sudo systemctl disable transmitter.service
sudo systemctl disable receiver.service
```

Reiniciar el servicio después de cambios en el código:

```bash
sudo systemctl restart transmitter.service
sudo systemctl restart receiver.service
```
