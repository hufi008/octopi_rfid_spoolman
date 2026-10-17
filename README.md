# OctoPi RFID Spoolman Link

Dieses Paket verbindet einen RC522 RFID-Reader am Raspberry Pi (OctoPi) mit Spoolman-ng und OctoPrint.

## Installation auf dem OctoPi

```bash
# 1. In die virtuelle Umgebung installieren
sudo /opt/rfid_octopi/env/bin/pip install git+https://github.com/hufi008/octopi_rfid_spoolman

# 2. Service-Datei anlegen
sudo nano /etc/systemd/system/rfid-spoolman.service
```

Füge dort den Inhalt aus der Service-Vorlage ein und passe deine IPs und den API-Key an.

```bash
# 3. Dienst starten und aktivieren
sudo systemctl daemon-reload
sudo systemctl enable rfid-spoolman.service
sudo systemctl start rfid-spoolman.service
```
