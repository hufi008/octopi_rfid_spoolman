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

def find_spool_by_uid(spoolman_url, card_uid):
    url = f"{spoolman_url}/api/v1/spool"
    params = {"extra.card_uids": card_uid}
    try:
        res = requests.get(url, params=params)
        if res.status_code == 200:
            spools = res.json()
            if spools and len(spools) > 0:
                return spools[0]["id"]
            else:
                print(f"Keine Spule mit der UID {card_uid} in Spoolman gefunden.", flush=True)
        else:
            print(f"Spoolman API Fehler: {res.status_code}", flush=True)
    except Exception as e:
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
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 200 or res.status_code == 204:
            print(f"-> Erfolgreich! Spule {spool_id} ist jetzt aktiv in OctoPrint.", flush=True)
        else:
            print(f"-> OctoPrint API Fehler ({res.status_code}): {res.text}", flush=True)
    except Exception as e:
        print(f"-> Verbindung zu OctoPrint fehlgeschlagen: {e}", flush=True)

def main():
    parser = argparse.ArgumentParser(description="OctoPi RFID Spoolman Link")
    parser.add_argument("--spoolman", required=True, help="Spoolman Server URL (z.B. http://jarvis:8000)")
    parser.add_argument("--octoprint", default="http://localhost:5000", help="OctoPrint URL")
    parser.add_argument("--apikey", required=True, help="OctoPrint Globaler API-Key")
    args = parser.parse_args()

    reader = SimpleMFRC522()
    print("[INFO] RFID gestartet. Tag-Erkennung aktiv...", flush=True)

    last_uid = None
    last_time = 0

    try:
        while True:
            uid_int = reader.read_id()
            current_hex = uid_to_hex(uid_int)
            
            if not current_hex:
                time.sleep(0.5)
                continue
                
            now = time.time()
            if current_hex == last_uid and (now - last_time) < 8:
                time.sleep(0.5)
                continue
                
            print(f"\nTag erkannt! HEX-UID: {current_hex}", flush=True)
            last_uid = current_hex
            last_time = now
            
            spool_id = find_spool_by_uid(args.spoolman, current_hex)
            if spool_id:
                print(f"Gefundene Spoolman-ID: {spool_id}. Setze aktiv in OctoPrint...", flush=True)
                select_spool_in_octoprint(args.octoprint, args.apikey, spool_id)
                
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nBeendet durch Nutzer.", flush=True)
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
