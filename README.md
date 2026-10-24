# OctoPi RFID Spoolman

OctoPrint-Plugin zum Auslesen von RFID-Tags mit einem RC522-Leser und zum Aktivieren der zugehörigen Filament-Spule in Spoolman über das OctoPrint-Spoolman-Plugin. Zusätzlich liest das Plugin eine HX711-Wägezelle aus und zeigt Rohwert und kalibriertes Gewicht in der Seitenleiste an.

## Funktionen

- Liest RFID-Tags mit einem RC522-RFID-Leser am Raspberry Pi.
- Sucht die gelesene UID in Spoolman und aktiviert die zugehörige Spule in OctoPrint.
- Zeigt RFID-Status, UID und Spuleninformationen in der Seitenleiste an.
- Liest HX711-Rohwerte über physische GPIO-BOARD-Pins 38 (DOUT) und 40 (SCK).
- Unterstützt Tara und Kalibrierung über ein bekanntes Gewicht.
- Rundet die lokale Gewichtsanzeige auf 2-g-Schritte; der ungerundete Messwert bleibt intern erhalten.
- Überträgt das Gesamtgewicht der erkannten Spule automatisch an Spoolman. Spoolman berechnet daraus das verbleibende Filamentgewicht.

## Waage einrichten

1. Stelle sicher, dass Filament Scale Enhanced deaktiviert ist, damit kein zweites Plugin gleichzeitig auf die HX711-GPIO-Pins zugreift.
2. Nach dem Neustart sollte die Seitenleiste den HX711-Status und Rohwert anzeigen.
3. Setze Tara mit der leeren Plattform bzw. dem leeren Halter auf der Waage.
4. Lege ein genau gewogenes Referenzgewicht auf den Halter.
5. Trage dessen tatsächliches Gewicht in Gramm ein und klicke **Kalibrieren**.
6. Kontrolliere, ob die Anzeige annähernd das bekannte Gewicht ergibt. Die Kalibrierung kann bei Bedarf wiederholt werden.

Die Tara und der Kalibrierungsfaktor werden in den Plugin-Einstellungen gespeichert. Die Kalibrierung sollte nach Änderungen an der mechanischen Montage oder am Lastpfad überprüft werden.

Wenn ein RFID-Tag einer Spule erkannt wurde, sendet das Plugin das ungerundete Gesamtgewicht an Spoolman (`PUT /api/v1/spool/{id}/measure`). Synchronisiert wird höchstens alle 30 Sekunden pro Spule und nur bei einer Änderung von mindestens 2 g. Messwerte unter 20 g werden ignoriert, damit eine unbelastete Plattform keine Spule als leer meldet.

## Voraussetzungen

- OctoPrint auf einem Raspberry Pi mit GPIO/SPI-Unterstützung.
- RC522-RFID-Leser und HX711-Wägezelle.
- Spoolman und das passende Spoolman-Plugin für OctoPrint.
- Ein globaler API-Key in der OctoPrint-Konfiguration.

## Installation

1. Installiere das Plugin über den OctoPrint Plugin Manager aus einem GitHub-ZIP oder aktualisiere die bestehende Installation.
2. Starte OctoPrint neu, wenn gerade kein Druck läuft.
3. Öffne **Einstellungen → RFID Spoolman** und kontrolliere die URLs.
4. Prüfe den RFID-Status und die Waagenwerte in der linken Seitenleiste.

## Sicherheit und Umfang

Die Waage aktualisiert den Bestand der per RFID erkannten Spule in Spoolman anhand des gemessenen Gesamtgewichts. Veröffentliche deinen OctoPrint-API-Key nicht in Repository-Dateien, Screenshots oder Logs.
