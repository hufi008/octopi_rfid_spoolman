import threading
import time

import octoprint.plugin
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

from .main import find_spool_by_uid, select_spool_in_octoprint, uid_to_hex


class RfidSpoolmanPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.SettingsPlugin,
):
    def __init__(self):
        self._stop_event = threading.Event()
        self._reader_thread = None
        self._reader = None
        self._last_uid = None
        self._last_spool_id = None

    def get_settings_defaults(self):
        return {
            "spoolman_url": "http://jarvis:8000",
            "octoprint_url": "http://localhost:5000",
        }

    def on_after_startup(self):
        api_key = self._settings.global_get(["api", "key"])
        if not api_key:
            self._logger.error(
                "Kein OctoPrint-API-Key in den globalen Einstellungen gefunden; "
                "RFID-Plugin wird nicht gestartet."
            )
            return

        spoolman_url = self._settings.get(["spoolman_url"]).rstrip("/")
        octoprint_url = self._settings.get(["octoprint_url"]).rstrip("/")

        try:
            self._reader = SimpleMFRC522()
        except Exception:
            self._logger.exception("RFID-Leser konnte nicht initialisiert werden.")
            return

        self._stop_event.clear()
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            args=(spoolman_url, octoprint_url, api_key),
            name="rfid-spoolman-reader",
            daemon=True,
        )
        self._reader_thread.start()
        self._logger.info("RFID-Spoolman-Plugin gestartet.")

    def _reader_loop(self, spoolman_url, octoprint_url, api_key):
        while not self._stop_event.is_set():
            try:
                uid_int = self._reader.read_id_no_block()
                if not uid_int:
                    time.sleep(0.2)
                    continue

                current_hex = uid_to_hex(uid_int)
                if not current_hex:
                    time.sleep(0.2)
                    continue

                if current_hex == self._last_uid:
                    time.sleep(0.2)
                    continue

                self._logger.info("RFID-Tag erkannt: %s", current_hex)
                spool_id = find_spool_by_uid(spoolman_url, current_hex)

                if spool_id is None:
                    self._logger.warning(
                        "Unbekannter RFID-Tag: %s – bitte in Spoolman zuordnen.",
                        current_hex,
                    )
                    time.sleep(1.0)
                    continue

                self._last_uid = current_hex
                self._logger.info("Spoolman-Spule gefunden: %s", spool_id)

                if spool_id == self._last_spool_id:
                    time.sleep(0.2)
                    continue

                self._logger.info("Aktiviere Spoolman-Spule %s in OctoPrint.", spool_id)
                if select_spool_in_octoprint(octoprint_url, api_key, spool_id):
                    self._last_spool_id = spool_id

            except Exception:
                self._logger.exception("Fehler in der RFID-Erkennung.")
                time.sleep(1.0)

    def on_shutdown(self):
        self._stop_event.set()
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=2.0)
        try:
            GPIO.cleanup()
        except Exception:
            self._logger.exception("Fehler beim Aufräumen der GPIO-Ressourcen.")
        self._logger.info("RFID-Spoolman-Plugin beendet.")


__plugin_name__ = "RFID Spoolman"
__plugin_pythoncompat__ = ">=3.11,<4"
__plugin_implementation__ = RfidSpoolmanPlugin()
