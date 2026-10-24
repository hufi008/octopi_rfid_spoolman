# Changelog

## 0.4.0

- Round the displayed HX711 weight to the nearest 2 g; retain the unrounded measurement internally.
- Trigger one gross-weight measurement after a spool is newly activated in OctoPrint and after a print finishes, fails, or is cancelled.
- Send the unrounded measurement to Spoolman using `PUT /api/v1/spool/{id}/measure`; Spoolman calculates the remaining filament weight from the gross measurement and spool tare.
- Require at least 8 seconds of stable readings; do not synchronize during a print and do not retry failed requests automatically.
- Ignore readings below 20 g so an unloaded platform cannot mark a spool as empty.
- Keep HX711 tare and calibration controls in OctoPrint settings.
