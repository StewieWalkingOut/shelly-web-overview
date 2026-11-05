import requests
import json
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

# === CONFIG ===
SHELLY_IP = "192.168.0.178"
SHELLY_PASSWORD = "1234"
POLL_INTERVAL = 60  # sekunder
DATA_FILE = "shelly_data.json"
PORT = 8080
# ==============

def poll_shelly():
    """Pollar Shelly och sparar data till JSON-fil."""
    url = f"http://{SHELLY_IP}/rpc/Switch.GetStatus?id=0"
    
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        
        # Läs tidigare data
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                history = json.load(f)
        else:
            history = []
        
        # Lägg till nytt mätvärde
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "apower": data.get("apower", 0),
            "voltage": data.get("voltage", 0),
            "current": data.get("current", 0),
            "aenergy_total": data.get("aenergy", {}).get("total", 0),
            "temperature": data.get("temperature", {}).get("tC", 0)
        }
        history.append(entry)
        
        # Behåll max 10000 punkter (~7 dagar vid 1 min intervall)
        if len(history) > 10000:
            history = history[-10000:]
        
        with open(DATA_FILE, "w") as f:
            json.dump(history, f)
        
        print(f"[{entry['timestamp']}] {entry['apower']} W, {entry['aenergy_total']} kWh")
    except Exception as e:
        print(f"Fel vid polling: {e}")

def poll_loop():
    while True:
        poll_shelly()
        time.sleep(POLL_INTERVAL)

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "rb") as f:   
                    self.wfile.write(f.read())   
            else:
                self.wfile.write(b"[]")
        else:
            self.path = "/index.html"
            super().do_GET()

# Starta polling i bakgrunds-tråd
t = threading.Thread(target=poll_loop, daemon=True)
t.start()

# Starta webserver
print(f"\nWebbserver startad: http://localhost:{PORT}\n")
server = HTTPServer(("0.0.0.0", PORT), Handler)
server.serve_forever()   