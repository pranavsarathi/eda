# High-Performance Zero-Dependency Python HTTP Server for EDA Workstation
import os
import sys
import json
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

# Add current directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from eda.pipeline import EDAPipeline
from examples.library import EXAMPLES
from test_suite.run_suite import QualityGateResult

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class EDAHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(BASE_DIR, "static"), **kwargs)

    def do_GET(self):
        # 1. API: List Examples
        if self.path == "/api/examples":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(EXAMPLES).encode("utf-8"))
            return

        # 2. API: Run Mandatory Test Suite & Quality Gate
        if self.path == "/api/run-suite":
            try:
                runner = QualityGateResult()
                res = runner.evaluate()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        # 3. Serve root as index.html
        if self.path == "/" or self.path == "":
            self.path = "/index.html"

        # Delegate static files to SimpleHTTPRequestHandler
        return super().do_GET()

    def do_POST(self):
        # API: Run Full EDA Pipeline
        if self.path == "/api/analyze":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                params = json.loads(body)
                rtl_code = params.get("rtl", "")
                tb_code = params.get("tb", "")
                tech_node = params.get("tech_node", "130nm")
                clock_mhz = float(params.get("clock_mhz", 100.0))
                core_util = float(params.get("core_util", 0.70))
                aspect_ratio = float(params.get("aspect_ratio", 1.0))
                routing_layers = int(params.get("routing_layers", 6))

                pipeline = EDAPipeline(
                    rtl_code=rtl_code,
                    tb_code=tb_code,
                    tech_node=tech_node,
                    core_util=core_util,
                    aspect_ratio=aspect_ratio,
                    clock_mhz=clock_mhz,
                    routing_layers=routing_layers
                )
                result = pipeline.run()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def start_server(port=8080):
    for p in range(port, port + 10):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), EDAHTTPHandler)
            print(f"=================================================================")
            print(f"RTL -> Pre-Physical Design Learning & Estimation Workstation")
            print(f"Server running at: http://127.0.0.1:{p}")
            print(f"=================================================================")
            server.serve_forever()
            break
        except OSError:
            print(f"Port {p} in use, trying {p+1}...")

if __name__ == "__main__":
    start_server(8080)
