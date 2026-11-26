import socket
import threading
import unittest
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from contextlib import contextmanager

from benchmark import check_targets

@contextmanager
def endpoint(routes):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            status, body = routes.get(self.path, (404, ""))
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode())
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        yield f"127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        t.join()
        server.server_close()

class ReadinessTests(unittest.TestCase):
    def test_socket_and_http_are_not_registration(self):
        with endpoint({"/ready": (200, "{}"), "/services": (200, '["other"]')}) as server:
            self.assertEqual(check_targets(app=server, registry=server), ["registration"])

    def test_registration_cannot_replace_http(self):
        with endpoint({"/ready": (503, "{}"), "/services": (200, '["app"]')}) as server:
            self.assertEqual(check_targets(app=server, registry=server), ["http"])

    def test_missing_socket_reports_transport_and_http(self):
        with socket.socket() as closed_port, endpoint({"/services": (200, '["app"]')}) as registry:
            closed_port.bind(("127.0.0.1", 0))
            app = f"127.0.0.1:{closed_port.getsockname()[1]}"
            self.assertEqual(check_targets(app=app, registry=registry), ["tcp", "http"])

    def test_checks_all_three_signals(self):
        with endpoint({"/ready": (200, "{}"), "/services": (200, '["app"]')}) as server:
            self.assertEqual(check_targets(app=server, registry=server), [])

if __name__ == "__main__":
    unittest.main()
