import time
import argparse
import requests
from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO

def uid_to_hex(uid_integer):
    bytes_list = []
    for i in range(5):
        bytes_list.append((uid_integer >> (8 * i)) & 0xFF)

    bytes_list.reverse()
    uid_bytes = bytes_list[0:4]
    bcc_byte = bytes_list[4]

    calculated_bcc = 0
    for b in uid_bytes:
        calculated_bcc ^= b

    if calculated_bcc == bcc_byte:
        return "".join(f"{b:02X}" for b in uid_bytes)
    else:
        print("⚠️ RFID-Lesefehler: BCC-Prüfung fehlgeschlagen!", flush=True)
        return None

def find_spool_by_uid(spoolman_url, card_uid, logger=None):
    url = f"{spoolman_url}/api/v1/spool"
    params = {"extra.card_uids": card_uid}
    try:
        res = requests.get(url, params=params, timeout=5)
        if logger:
            logger.info(
                "Spoolman-Abfrage: GET %s -> HTTP %s",
                res.url,
                res.status_code,
            )
        if res.status_code == 200:
            spools = res.json()
            if spools:
                spool_id = spools[0]["id"]
                if logger:
                    logger.info(
                        "Spoolman-Abfrage für UID %s: Spule %s gefunden (Treffer: %s).",
                        card_uid,
                        spool_id,
                        len(spools),
                    )
                return spool_id
            if logger:
                logger.warning(
                    "Spoolman-Abfrage für UID %s: HTTP 200, aber keine Treffer.",
                    card_uid,
                )
            else:
                print(f"Keine Spule mit der UID {card_uid} in Spoolman gefunden.", flush=True)
        else:
            if logger:
                logger.error(
                    "Spoolman-API-Fehler für UID %s: HTTP %s; Antwort: %s",
                    card_uid,
                    res.status_code,
                    res.text[:300],
                )
            else:
                print(f"Spoolman API Fehler: {res.status_code}", flush=True)
    except Exception as e:
        if logger:
            logger.exception("Spoolman-Abfrage für UID %s fehlgeschlagen.", card_uid)
        else:
            print(f"Verbindung zu Spoolman fehlgeschlagen: {e}", flush=True)
    return None

def select_spool_in_octoprint(octoprint_url, api_key, spool_id):
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    url = f"{octoprint_url}/plugin/Spoolman/self/spool"
    payload = {
        "toolIdx": 0,
        "spoolId": int(spool_id)
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200 or res.status_code == 204:
            print(f"-> Erfolgreich! Spule {spool_id} ist jetzt aktiv in OctoPrint.", flush=True)
            return True
        else:
            print(f"-> OctoPrint API Fehler ({res.status_code}): {res.text}", flush=True)
            return False
    except Exception as e:
        print(f"-> Verbindung zu OctoPrint fehlgeschlagen: {e}", flush=True)
        return False

def main():
    parser = argparse.ArgumentParser(description="OctoPi RFID Spoolman Link")
    parser.add_argument("--spoolman", required=True, help="Spoolman Server URL (z.B. http://jarvis:8000)")
    parser.add_argument("--octoprint", default="http://localhost:5000", help="OctoPrint URL")
    parser.add_argument("--apikey", required=True, help="OctoPrint Globaler API-Key")
    args = parser.parse_args()

    reader = SimpleMFRC522()
    print("[INFO] RFID gestartet. Tag-Erkennung aktiv...", flush=True)

    last_uid = None
    last_spool_id = None

    try:
        while True:
            uid_int = reader.read_id()
            current_hex = uid_to_hex(uid_int)

            if not current_hex:
                time.sleep(0.5)
                continue

            if current_hex == last_uid:
                time.sleep(0.2)
                continue

            print(f"\nTag erkannt! HEX-UID: {current_hex}", flush=True)

            spool_id = find_spool_by_uid(args.spoolman, current_hex)

            # Bei einem Fehler oder unbekannter UID später erneut versuchen
            if spool_id is None:
                print(f"\n[WARN] Unbekannter Tag! UID: {current_hex} – Bitte in Spoolman zuordnen.", flush=True)
                time.sleep(0.5)
                continue

            # Erst nach erfolgreicher Spoolman-Abfrage als verarbeitet markieren
            last_uid = current_hex

            print(f"Gefundene Spoolman-ID: {spool_id}", flush=True)

            # Dieselbe Rolle ist bereits aktiv
            if spool_id == last_spool_id:
               #print(
               #     f"Spule {spool_id} ist bereits aktiv. Kein Wechsel nötig.",
               #     flush=True
               # )
                continue

            print(f"Aktiviere Spule {spool_id} in OctoPrint...", flush=True)

            if select_spool_in_octoprint(args.octoprint, args.apikey, spool_id):
                last_spool_id = spool_id

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nBeendet durch Nutzer.", flush=True)
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
