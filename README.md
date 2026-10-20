# OctoPi RFID Spoolman

OctoPrint-Plugin zum Auslesen von RFID-Tags mit einem RC522-Leser und zum Aktivieren der zugehörigen Filament-Spule in Spoolman über das OctoPrint-Spoolman-Plugin.

## Funktionen

- Liest RFID-Tags mit einem RC522-RFID-Leser am Raspberry Pi.
- Sucht die gelesene UID in Spoolman.
- Aktiviert die zugehörige Spule über das OctoPrint-Spoolman-Plugin.
- Zeigt in der OctoPrint-Seitenleiste den Leserstatus, die gelesene UID und das Ergebnis der Spulensuche an.
- Meldet unbekannte Tags, damit sie in Spoolman zugeordnet werden können.

## Voraussetzungen

- OctoPrint auf einem Raspberry Pi bzw. einem System, an dem der RC522 angeschlossen ist.
- RC522-RFID-Leser, korrekt angeschlossen und für SPI eingerichtet.
- Funktionierende GPIO-/SPI-Unterstützung sowie die Python-Abhängigkeiten des Plugins.
- Spoolman und das passende **Spoolman-Plugin für OctoPrint**.
- Ein globaler API-Key in der OctoPrint-Konfiguration.

Die Spoolman-URL muss vom OctoPrint-System aus erreichbar sein. Hostnamen und Ports unterscheiden sich je nach Netzwerk und Installation.

## Installation

Der Plugin-Code befindet sich derzeit im Entwicklungszweig `plugin-development`. Dieser Zweig ist in Entwicklung und sollte als nicht stabil bzw. noch nicht produktiv getestet betrachtet werden.

1. Öffne OctoPrint und gehe zu **Einstellungen → Plugin Manager → Get More…**.
2. Wähle **… from URL** und füge diese URL ein:

   ```text
   https://github.com/hufi008/octopi_rfid_spoolman/archive/refs/heads/plugin-development.zip
   ```

3. Installiere das Plugin und starte OctoPrint neu, wenn gerade kein Druck läuft.
4. Öffne **Einstellungen → RFID Spoolman** und kontrolliere die Spoolman-URL sowie die OctoPrint-URL.
5. Prüfe, ob in OctoPrint ein globaler API-Key konfiguriert ist und das OctoPrint-Spoolman-Plugin funktioniert.
6. Kontrolliere die linke Seitenleiste. Dort werden der Status des RFID-Lesers, die zuletzt gelesene UID und das Ergebnis angezeigt.

## Konfiguration

- **Spoolman-URL:** Basis-URL deiner Spoolman-Instanz, z. B. `http://home-assistant:8000`, sofern dieser Hostname in deinem Netzwerk erreichbar ist. Passe Hostname und Port an deine Installation an.
- **OctoPrint-URL:** In einer normalen lokalen Installation ist `http://localhost:5000) ein üblicher Wert.
- **API-Key:** Das Plugin verwendet den globalen API-Key aus der OctoPrint-Konfiguration.

Die angezeigten Standardwerte sind Beispiele und funktionieren nicht automatisch in jedem Netzwerk.

## RFID-Leser und Systemdienst

Das Plugin läuft innerhalb von OctoPrint. Für den normalen Plugin-Betrieb ist **kein separater systemd-Dienst** erforderlich.

Falls du zuvor die eigenständige Version als Dienst eingerichtet hast, stoppe und deaktiviere diesen alten Dienst, bevor du das Plugin verwendest. Zwei Prozesse dürfen nicht gleichzeitig auf denselben RC522-Leser zugreifen. Den alten Dienst nicht parallel zum Plugin starten.

## Fehlerbehebung

- **Leserstatus „Fehler“:** Prüfe Verkabelung, SPI-/GPIO-Konfiguration und ob noch ein anderer Prozess den RC522 verwendet.
- **Spoolman nicht erreichbar:** Prüfe die URL, den Port und ob die Adresse vom OctoPrint-System aus aufgelöst und erreicht werden kann.
- **Tag unbekannt:** Trage die UID des Tags in Spoolman bei der passenden Spule ein.
- **Spule wird nicht aktiviert:** Prüfe, ob das OctoPrint-Spoolman-Plugin installiert und funktionsfähig ist und der globale API-Key korrekt eingerichtet ist.

## Sicherheit

Veröffentliche deinen OctoPrint-API-Key nicht in Repository-Dateien, Screenshots oder Logs.