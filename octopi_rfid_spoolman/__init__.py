import math
import threading
import time

import requests

import octoprint.plugin
import octoprint.util
import RPi.GPIO as GPIO

from .rc522_reader import RC522Reader
from .hx711_reader import HX711Reader
from .main import find_spool_by_uid, select_spool_in_octoprint, uid_to_hex


class RfidSpoolmanPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.EventHandlerPlugin,
):
    def __init__(self):
        self._reader_timer = None
        self._reader = None
        self._hx711_reader = None
        self._hx711_timer = None
        self._hx711_lock = threading.Lock()
        self._hx711_status = "starting"
        self._hx711_message = "HX711 wird gestartet"
        self._hx711_raw = None
        self._hx711_weight_g = None
        self._api_key = None
        self._spoolman_url = None
        self._octoprint_url = None
        self._last_uid = None
        self._last_spool_id = None
        self._last_attempt_uid = None
        self._last_attempt_time = 0.0
        self._rfid_status = "waiting"
        self._reader_status = "starting"
        self._rfid_message = "Warte auf RFID-Tag"
        self._rfid_uid = None
        self._rfid_spool_id = None
        self._rfid_spool = None
        self._printing = False
        self._weight_samples = []
        self._weight_sync_pending = None

    def get_settings_defaults(self):
        return {
            "spoolman_url": "http://home-assistant.local:8000",
            "octoprint_url": "http://localhost:5000",
            "hx711_offset": 0.0,
            "hx711_reference_unit": 0.0,
        }

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        for key in ("spoolman_url", "octoprint_url"):
            if key in data and isinstance(data[key], str):
                self._settings.set([key], data[key].strip().rstrip("/"))
        self._settings.save()

    def get_template_configs(self):
        return [
            {"type": "settings", "name": "RFID Spoolman"},
            {"type": "sidebar", "name": "RFID Spoolman", "custom_bindings": False},
        ]

    def get_assets(self):
        return {"js": ["js/rfid_spoolman.js"]}

    def get_api_commands(self):
        return {"tare": [], "calibrate": ["weight_g"]}

    def is_api_protected(self):
        return True

    def on_api_get(self, request):
        calibrated = (
            self._hx711_reader is not None
            and self._hx711_reader.reference_unit is not None
        )
        return {
            "status": self._reader_status,
            "reader_status": self._reader_status,
            "card_status": self._rfid_status,
            "message": self._rfid_message,
            "uid": self._rfid_uid,
            "spool_id": self._rfid_spool_id,
            "spool": self._rfid_spool,
            "hx711_status": self._hx711_status,
            "hx711_message": self._hx711_message,
            "hx711_raw": self._hx711_raw,
            "hx711_weight_g": self._hx711_weight_g,
            "hx711_offset": (
                self._hx711_reader.offset if self._hx711_reader is not None else None
            ),
            "hx711_calibrated": calibrated,
            "hx711_reference_unit": (
                self._hx711_reader.reference_unit
                if self._hx711_reader is not None else None
            ),
        }

    def on_api_command(self, command, data):
        if self._hx711_reader is None:
            return {"success": False, "message": "HX711 ist nicht verfügbar."}

        try:
            with self._hx711_lock:
                if command == "tare":
                    offset = self._hx711_reader.tare(samples=10)
                    self._settings.set(["hx711_offset"], offset)
                    self._settings.save()
                    self._hx711_raw = offset
                    self._hx711_weight_g = 0.0 if self._hx711_reader.reference_unit else None
                    self._hx711_message = "Tara gespeichert"
                    self._logger.info("HX711-Tara gespeichert: %.1f Rohwerte", offset)
                    return {"success": True, "message": "Tara gespeichert."}

                if command == "calibrate":
                    try:
                        weight_g = float(data.get("weight_g"))
                    except (TypeError, ValueError):
                        return {"success": False, "message": "Bitte ein Gewicht in Gramm eingeben."}
                    if weight_g <= 0 or weight_g > 5000:
                        return {"success": False, "message": "Gewicht muss zwischen 0 und 5000 g liegen."}
                    raw = self._hx711_reader.read_average(samples=5)
                    difference = raw - self._hx711_reader.offset
                    if abs(difference) < 100:
                        return {
                            "success": False,
                            "message": "Messdifferenz zu klein. Tara ohne Last setzen und bekanntes Gewicht auflegen.",
                        }
                    factor = difference / weight_g
                    self._hx711_reader.reference_unit = factor
                    self._settings.set(["hx711_reference_unit"], factor)
                    self._settings.save()
                    self._hx711_raw = raw
                    self._hx711_weight_g = weight_g
                    self._hx711_message = "Kalibrierung gespeichert"
                    self._logger.info(
                        "HX711 kalibriert: %.1f Rohwerte/g mit %.2f g Referenzgewicht",
                        factor, weight_g,
                    )
                    return {"success": True, "message": "Kalibrierung gespeichert."}

        except Exception as exc:
            self._hx711_message = str(exc)
            self._logger.exception("HX711-Aktion fehlgeschlagen.")
            return {"success": False, "message": "HX711-Aktion fehlgeschlagen: " + str(exc)}

        return {"success": False, "message": "Unbekannter Befehl."}

    def on_after_startup(self):
        self._api_key = self._settings.global_get(["api", "key"])
        try:
            self._printing = bool(self._printer.is_printing())
        except Exception:
            self._printing = False
        if not self._api_key:
            self._reader_status = "error"
            self._rfid_status = "error"
            self._rfid_message = "Kein globaler OctoPrint-API-Key konfiguriert"
            self._logger.error(
                "Kein globaler OctoPrint-API-Key konfiguriert; "
                "RFID-Plugin wird nicht gestartet."
            )
            return

        self._spoolman_url = (self._settings.get(["spoolman_url"]) or "").strip().rstrip("/")
        self._octoprint_url = (self._settings.get(["octoprint_url"]) or "http://localhost:5000").strip().rstrip("/")

        if not self._spoolman_url or self._spoolman_url == "http://home-assistant.local:8000":
            configured_spoolman_url = self._settings.global_get(
                ["plugins", "Spoolman", "spoolmanUrl"]
            )
            if isinstance(configured_spoolman_url, str) and configured_spoolman_url.strip():
                self._spoolman_url = configured_spoolman_url.strip().rstrip("/")
                self._logger.warning(
                    "Keine eigene Spoolman-URL gespeichert; verwende die URL aus dem Spoolman-Plugin: %s",
                    self._spoolman_url,
                )

        try:
            self._reader = RC522Reader()
        except Exception:
            self._reader_status = "error"
            self._rfid_status = "error"
            self._rfid_message = "RFID-Leser konnte nicht initialisiert werden"
            self._logger.exception("RFID-Leser konnte nicht initialisiert werden.")
            return

        self._reader_status = "online"
        self._rfid_status = "waiting"
        self._rfid_message = "Warte auf RFID-Tag"
        self._reader_timer = octoprint.util.RepeatedTimer(
            0.2, self._poll_reader, run_first=True, daemon=True
        )
        self._reader_timer.start()

        # HX711 is independent: a scale error must not disable the RFID reader.
        try:
            offset = float(self._settings.get(["hx711_offset"]) or 0.0)
            reference_unit = float(self._settings.get(["hx711_reference_unit"]) or 0.0)
            self._hx711_reader = HX711Reader(
                dout_pin=38,
                sck_pin=40,
                offset=offset,
                reference_unit=reference_unit if reference_unit != 0 else None,
                ready_timeout=2.0,
            )
            self._hx711_status = "online"
            self._hx711_message = (
                "Waage bereit" if self._hx711_reader.reference_unit
                else "Rohwerte verfügbar – Tara und Kalibrierung erforderlich"
            )
            self._hx711_timer = octoprint.util.RepeatedTimer(
                1.0, self._poll_hx711, run_first=True, daemon=True
            )
            self._hx711_timer.start()
            self._logger.info("HX711 gestartet (DOUT BOARD 38, SCK BOARD 40).")
        except Exception as exc:
            self._hx711_status = "error"
            self._hx711_message = str(exc)
            self._logger.exception("HX711 konnte nicht initialisiert werden.")

        self._logger.info("RFID-Spoolman-Plugin gestartet. Spoolman-URL: %s", self._spoolman_url)

    def _poll_hx711(self):
        if self._hx711_reader is None:
            return
        try:
            with self._hx711_lock:
                raw = self._hx711_reader.read_average(samples=3, timeout=2.0)
                self._hx711_raw = raw
                if self._hx711_reader.reference_unit is not None:
                    self._hx711_weight_g = (
                        raw - self._hx711_reader.offset
                    ) / self._hx711_reader.reference_unit
                else:
                    self._hx711_weight_g = None
                self._hx711_status = "online"
                self._hx711_message = (
                    "Waage bereit" if self._hx711_reader.reference_unit is not None
                    else "Noch nicht kalibriert"
                )
        except Exception as exc:
            self._hx711_status = "error"
            self._hx711_message = str(exc)
            self._logger.warning("HX711-Lesefehler: %s", exc)
            return

        # Cross-check the event flag with OctoPrint's live printer state. This
        # also protects against a plugin restart while a print is already active.
        try:
            printer_is_printing = bool(self._printer.is_printing())
            if printer_is_printing != self._printing:
                self._printing = printer_is_printing
                self._weight_samples.clear()
        except Exception:
            pass

        # Never synchronize a moving spool while a print is active. Require
        # a stable 10-second window before treating the scale as absolute stock.
        if self._hx711_weight_g is None:
            return
        now = time.monotonic()
        self._weight_samples.append((now, self._hx711_weight_g))
        self._weight_samples = [
            (stamp, value) for stamp, value in self._weight_samples
            if now - stamp <= 10.0
        ]
        if self._printing or len(self._weight_samples) < 8:
            return
        if now - self._weight_samples[0][0] < 8.0:
            return
        values = [value for _, value in self._weight_samples]
        if max(values) - min(values) > 2.0:
            return

        stable_weight_g = sum(values) / len(values)
        if self._weight_sync_pending is None:
            return

        reason = self._weight_sync_pending
        # Consume this event exactly once. A failed HTTP request is logged and
        # is not retried automatically; a later activation/end event can sync again.
        self._weight_sync_pending = None
        self._sync_spoolman_weight(stable_weight_g, reason=reason)

    def on_event(self, event, payload):
        if event == "PrintStarted":
            self._printing = True
            self._weight_samples.clear()
            self._logger.info("Waagensynchronisierung während des Drucks pausiert.")
        elif event in ("PrintDone", "PrintFailed", "PrintCancelled"):
            self._printing = False
            self._weight_samples.clear()
            self._weight_sync_pending = "Druckende"
            self._logger.info(
                "Druck beendet; warte auf ein stabiles Waagengewicht vor Spoolman-Synchronisierung."
            )

    def _sync_spoolman_weight(self, gross_weight_g, reason="Ereignis"):
        """Report one stable gross spool measurement to Spoolman for a specific event."""
        if (
            self._rfid_status != "recognized"
            or self._rfid_spool_id is None
            or not self._spoolman_url
        ):
            return

        try:
            gross_weight_g = float(gross_weight_g)
            # An unloaded platform must never overwrite a spool as empty.
            if not math.isfinite(gross_weight_g) or gross_weight_g < 20.0:
                return
        except (TypeError, ValueError):
            return

        spool_id = int(self._rfid_spool_id)
        try:
            response = requests.put(
                f"{self._spoolman_url}/api/v1/spool/{spool_id}/measure",
                json={"weight": gross_weight_g},
                timeout=5,
            )
            response.raise_for_status()
            updated_spool = response.json()

            if self._rfid_spool_id == spool_id and self._rfid_spool is not None:
                for key in ("remaining_weight", "initial_weight", "remaining_length"):
                    if key in updated_spool:
                        self._rfid_spool[key] = updated_spool[key]

            remaining = updated_spool.get("remaining_weight")
            if remaining is None:
                self._logger.info(
                    "Spoolman-Gewicht aktualisiert (%s): Spule %s, Gesamtgewicht %.1f g",
                    reason, spool_id, gross_weight_g,
                )
            else:
                self._logger.info(
                    "Spoolman-Gewicht aktualisiert (%s): Spule %s, Gesamtgewicht %.1f g, "
                    "Restfilament %.1f g",
                    reason, spool_id, gross_weight_g, remaining,
                )
        except Exception as exc:
            self._logger.warning(
                "Spoolman-Gewicht für Spule %s konnte nicht aktualisiert werden: %s",
                spool_id, exc,
            )

    def _poll_reader(self):
        try:
            uid_int = self._reader.read_id_no_block()
            self._reader_status = "online"
        except Exception:
            self._reader_status = "error"
            self._rfid_status = "error"
            self._rfid_message = "Fehler beim Lesen des RFID-Lesers"
            self._logger.exception("Fehler beim Lesen des RC522-RFID-Lesers.")
            return

        try:
            if uid_int is None:
                return
            current_hex = uid_to_hex(uid_int)
            if not current_hex:
                return
            if current_hex == self._last_uid and self._rfid_status == "recognized":
                return

            now = time.monotonic()
            if current_hex == self._last_attempt_uid and now - self._last_attempt_time < 2.0:
                return
            self._last_attempt_uid = current_hex
            self._last_attempt_time = now
            self._rfid_uid = current_hex
            self._rfid_spool_id = None
            self._rfid_spool = None

            self._logger.info("RFID-Tag erkannt: %s", current_hex)
            spool = find_spool_by_uid(self._spoolman_url, current_hex, logger=self._logger)
            if spool is None:
                self._rfid_status = "unknown"
                self._rfid_message = "Unknown – muss in Spoolman eingetragen werden"
                self._logger.warning("Unbekannter RFID-Tag: %s – bitte in Spoolman zuordnen.", current_hex)
                return

            spool_id = spool["id"]
            self._rfid_spool_id = spool_id
            self._rfid_spool = {
                "id": spool_id,
                "filament_name": (spool.get("filament") or {}).get("name"),
                "material": (spool.get("filament") or {}).get("material"),
                "vendor": ((spool.get("filament") or {}).get("vendor") or {}).get("name"),
                "remaining_weight": spool.get("remaining_weight"),
                "initial_weight": spool.get("initial_weight"),
                "remaining_length": spool.get("remaining_length"),
            }
            self._logger.info("Spoolman-Spule gefunden: %s", spool_id)

            if spool_id == self._last_spool_id:
                self._rfid_status = "recognized"
                self._rfid_message = "Spule erkannt und bereits aktiv"
                self._last_uid = current_hex
                return

            self._logger.info("Aktiviere Spoolman-Spule %s in OctoPrint.", spool_id)
            if select_spool_in_octoprint(self._octoprint_url, self._api_key, spool_id):
                self._last_spool_id = spool_id
                self._last_uid = current_hex
                self._rfid_status = "recognized"
                self._rfid_message = "Spule erkannt und in OctoPrint aktiviert"
                self._weight_samples.clear()
                self._weight_sync_pending = "Spule aktiviert"
                self._logger.info(
                    "Spule %s aktiviert; warte auf stabile Messung für Spoolman-Synchronisierung.",
                    spool_id,
                )
            else:
                self._rfid_status = "error"
                self._rfid_message = "Spule gefunden, Aktivierung in OctoPrint fehlgeschlagen"
        except Exception:
            self._rfid_status = "error"
            self._rfid_message = "Fehler bei der RFID-/Spoolman-Abfrage"
            self._logger.exception("Fehler bei der Verarbeitung des RFID-Tags.")

    def on_shutdown(self):
        for timer in (self._reader_timer, self._hx711_timer):
            if timer is not None:
                timer.cancel()
                timer.join(timeout=2.0)
        if self._hx711_reader is not None:
            try:
                self._hx711_reader.close()
            except Exception:
                self._logger.exception("Fehler beim Schließen des HX711.")
        try:
            GPIO.cleanup()
        except Exception:
            self._logger.exception("Fehler beim Aufräumen der GPIO-Ressourcen.")
        self._logger.info("RFID-Spoolman-Plugin beendet.")


__plugin_name__ = "RFID Spoolman"
__plugin_version__ = "0.4.0"
__plugin_pythoncompat__ = ">=3.11,<4"
__plugin_implementation__ = RfidSpoolmanPlugin()


def get_update_information(*args, **kwargs):
    return {
        "rfid_spoolman": {
            "displayName": __plugin_name__,
            "displayVersion": __plugin_version__,
            "type": "github_release",
            "current": __plugin_version__,
            "user": "hufi008",
            "repo": "octopi_rfid_spoolman",
            "pip": "https://github.com/hufi008/octopi_rfid_spoolman/archive/{target}.zip",
        }
    }


__plugin_hooks__ = {
    "octoprint.plugin.softwareupdate.check_config": get_update_information,
}
