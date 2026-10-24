# Changelog

## 0.4.0

- Round the displayed HX711 weight to the nearest 2 g; retain the unrounded measurement internally.
- Send the measured gross spool weight to Spoolman for the RFID-recognized spool using `PUT /api/v1/spool/{id}/measure`, only while the printer is idle and the scale reading is stable.
- Let Spoolman calculate the remaining filament weight from the gross measurement and spool tare.
- Require at least 8 seconds of stable readings; limit synchronization to at most once every 30 seconds per spool and only send again when the measured gross weight differs by at least 2 g.
- Ignore readings below 20 g so an unloaded platform cannot mark a spool as empty.
- Keep HX711 tare and calibration controls in OctoPrint settings.
