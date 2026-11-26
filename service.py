"""Small fictional components for a readiness demonstration."""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen

ROLE = os.environ["DEMO_ROLE"]
ENABLE_AT = time.monotonic() + float(os.environ.get("DEMO_DELAY", 0))
REGISTRATIONS = set()
REGISTRY_LOCK = threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/ready":
            ready = time.monotonic() >= ENABLE_AT
            self.respond(200 if ready else 503, {"ready": ready})
        elif ROLE == "registry" and self.path == "/services":
            with REGISTRY_LOCK:
                snapshot = sorted(REGISTRATIONS)
            self.respond(200, snapshot)
        else:
            self.respond(404, {})

    def do_POST(self):
        if ROLE != "registry" or self.path != "/register":
            self.respond(404, {})
            return
        length = self.headers.get("Content-Length", "")
        if length != "3" or self.rfile.read(3) != b"app":
            self.respond(400, {})
            return
        with REGISTRY_LOCK:
            REGISTRATIONS.add("app")
        self.respond(200, {"registered": "app"})

def register():
    time.sleep(max(0, ENABLE_AT - time.monotonic()))
    req = Request("http://registry:8000/register", data=b"app", method="POST")
    while True:
        try:
            with urlopen(req, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.2)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    if ROLE == "app":
        threading.Thread(target=register, daemon=True).start()
    server.serve_forever()
