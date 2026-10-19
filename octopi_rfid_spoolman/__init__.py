import time

import octoprint.plugin
import octoprint.util
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

from .main import find_spool_by_uid, select_spool_in_octoprint, uid_to_hex


class RfidSpoolmanPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.TemplatePlugin,
):
    def __init__(self):
        self._reader_timer = None
        self._reader = None
        self._api_key = None
        self._spoolman_url = None
        self._octoprint_url = None
        self._last_uid = None
        self._last_spool_id = None
        self._last_attempt_uid = None
        self._last_attempt_time = 0.0

    def get_settings_defaults(self):
        return {
            "spoolman_url": "http://home-assistant.local:8000",
            "octoprint_url": "http://localhost:5000",
        }

    def get_template_configs(self):
        return [{"type": "settings", "name": "RFID Spoolman"}]

    def on_after_startup(self):
        self._api_key = self._settings.global_get(["api", "key"])
        if not self._api_key:
            self._logger.error(
                "Kein globaler OctoPrint-API-Key konfiguriert; "
                "RFID-Plugin wird nicht gestartet."
            )
            return

        self._spoolman_url = self._settings.get(["spoolman_url"]).rstrip("/")
        self._octoprint_url = self._settings.get(["octoprint_url"]).rstrip("/")

        try:
            self._reader = SimpleMFRC522()
        except Exception:
            self._logger.exception("RFID-Leser konnte nicht initialisiert werden.")
            return

        self._reader_timer = octoprint.util.RepeatedTimer(
            0.2, self._poll_reader, run_first=True, daemon=True
        )
        self._reader_timer.start()
        self._logger.info("RFID-Spoolman-Plugin gestartet.")

    def _poll_reader(self):
        try:
            uid_int = self._reader.read_id_no_block()
            if uid_int is None:
                return

            current_hex = uid_to_hex(uid_int)
            if not current_hex or current_hex == self._last_uid:
                return

            now = time.monotonic()
            if (
                current_hex == self._last_attempt_uid
                and now - self._last_attempt_time < 2.0
            ):
                return
            self._last_attempt_uid = current_hex
            self._last_attempt_time = now

            self._logger.info("RFID-Tag erkannt: %s", current_hex)
            spool_id = find_spool_by_uid(self._spoolman_url, current_hex)

            if spool_id is None:
                self._logger.warning(
                    "Unbekannter RFID-Tag: %s – bitte in Spoolman zuordnen.",
                    current_hex,
                )
                return

            self._logger.info("Spoolman-Spule gefunden: %s", spool_id)

            if spool_id == self._last_spool_id:
                self._last_uid = current_hex
                return

            self._logger.info("Aktiviere Spoolman-Spule %s in OctoPrint.", spool_id)
            if select_spool_in_octoprint(
                self._octoprint_url, self._api_key, spool_id
            ):
                self._last_spool_id = spool_id
                self._last_uid = current_hex

        except Exception:
            self._logger.exception("Fehler bei der RFID-Tag-Abfrage.")

    def on_shutdown(self):
        if self._reader_timer is not None:
            self._reader_timer.cancel()
            self._reader_timer.join(timeout=2.0)

        try:
            GPIO.cleanup()
        except Exception:
            self._logger.exception("Fehler beim Aufräumen der GPIO-Ressourcen.")

        self._logger.info("RFID-Spoolman-Plugin beendet.")


__plugin_name__ = "RFID Spoolman"
__plugin_pythoncompat__ = ">=3.11,<4"
__plugin_implementation__ = RfidSpoolmanPlugin()
