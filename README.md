# OctoPi RFID Spoolman Link

Dieses Paket verbindet einen RC522-RFID-Reader am Raspberry Pi (OctoPi) mit Spoolman-ng und OctoPrint.

## OctoPrint-Plugin (Entwicklungszweig)

Der Plugin-Code wird derzeit im Branch `plugin-development` entwickelt und ist noch nicht als produktiv getestet zu betrachten.

1. Vor der Aktivierung des Plugins den bisherigen RFID-Systemdienst stoppen und deaktivieren, damit nicht zwei Prozesse gleichzeitig auf den RC522 zugreifen.
2. In OctoPrint unter **Einstellungen → Plugin Manager → Get More… → … from URL** installieren mit:

   ```
   https://github.com/hufi008/octopi_rfid_spoolman/archive/refs/heads/plugin-development.zip
   ```

3. OctoPrint neu starten und prüfen, ob **RFID Spoolman** in den Plugins aktiviert ist.
4. Unter **Einstellungen → RFID Spoolman** die Spoolman-URL und die OctoPrint-URL kontrollieren.
5. In OctoPrint muss ein globaler API-Key konfiguriert sein; das Plugin verwendet diesen für die Spoolman-Plugin-API.
6. Die linke Seitenleiste zeigt den RFID-Status, die erkannte UID und die Spoolman-Spulennummer. Nicht zugeordnete Tags erscheinen als **Unknown**.

Der Plugin-Code greift auf den RC522 über `mfrc522` und `RPi.GPIO` zu. Die GPIO-/SPI-Unterstützung muss auf dem Raspberry Pi bereits eingerichtet sein.

## Bisheriger eigenständiger Dienst

Die Kommandozeilenfunktion bleibt für den bisherigen Systemdienst erhalten. Installiere das Paket in der dafür verwendeten Python-Umgebung:

```bash
sudo /opt/rfid_octopi/env/bin/pip install git+https://github.com/hufi008/octopi_rfid_spoolman
```

Der bisherige Dienst wird mit den Argumenten `--spoolman`, `--octoprint` und `--apikey` gestartet. API-Keys nicht in öffentliche Dateien oder Logs schreiben.
