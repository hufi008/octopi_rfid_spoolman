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
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.AssetPlugin,
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
        self._rfid_status = "waiting"
        self._reader_status = "starting"
        self._rfid_message = "Warte auf RFID-Tag"
        self._rfid_uid = None
        self._rfid_spool_id = None

    def get_settings_defaults(self):
        return {
            "spoolman_url": "http://home-assistant.local:8000",
            "octoprint_url": "http://localhost:5000",
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
        return {}

    def on_api_get(self, request):
        return {
            "status": self._reader_status,
            "reader_status": self._reader_status,
            "card_status": self._rfid_status,
            "message": self._rfid_message,
            "uid": self._rfid_uid,
            "spool_id": self._rfid_spool_id,
        }

    def on_after_startup(self):
        self._api_key = self._settings.global_get(["api", "key"])
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

        # If the RFID plugin has never saved its own URL, reuse the URL
        # already configured by OctoPrint's Spoolman plugin.
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
            self._reader = SimpleMFRC522()
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
        self._logger.info("RFID-Spoolman-Plugin gestartet. Spoolman-URL: %s", self._spoolman_url)

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
            if (
                current_hex == self._last_attempt_uid
                and now - self._last_attempt_time < 2.0
            ):
                return
            self._last_attempt_uid = current_hex
            self._last_attempt_time = now
            self._rfid_uid = current_hex
            self._rfid_spool_id = None

            self._logger.info("RFID-Tag erkannt: %s", current_hex)
            spool_id = find_spool_by_uid(self._spoolman_url, current_hex, logger=self._logger)

            if spool_id is None:
                self._rfid_status = "unknown"
                self._rfid_message = "Unknown – muss in Spoolman eingetragen werden"
                self._logger.warning(
                    "Unbekannter RFID-Tag: %s – bitte in Spoolman zuordnen.",
                    current_hex,
                )
                return

            self._rfid_spool_id = spool_id
            self._logger.info("Spoolman-Spule gefunden: %s", spool_id)

            if spool_id == self._last_spool_id:
                self._rfid_status = "recognized"
                self._rfid_message = "Spule erkannt und bereits aktiv"
                self._last_uid = current_hex
                return

            self._logger.info("Aktiviere Spoolman-Spule %s in OctoPrint.", spool_id)
            if select_spool_in_octoprint(
                self._octoprint_url, self._api_key, spool_id
            ):
                self._last_spool_id = spool_id
                self._last_uid = current_hex
                self._rfid_status = "recognized"
                self._rfid_message = "Spule erkannt und in OctoPrint aktiviert"
            else:
                self._rfid_status = "error"
                self._rfid_message = "Spule gefunden, Aktivierung in OctoPrint fehlgeschlagen"

        except Exception:
            self._rfid_status = "error"
            self._rfid_message = "Fehler bei der RFID-/Spoolman-Abfrage"
            self._logger.exception("Fehler bei der Verarbeitung des RFID-Tags.")

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
__plugin_version__ = "0.2.4"
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
