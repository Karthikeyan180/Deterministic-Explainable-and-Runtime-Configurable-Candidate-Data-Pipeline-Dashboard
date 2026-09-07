"""
Web API Server & Dashboard Host
Zero-dependency HTTP API server serving REST endpoints and interactive Web UI SPA.
"""

import http.server
import socketserver
import json
import os
import urllib.parse
from typing import Dict, Any
from src.pipeline import CandidateTransformationPipeline
from evaluator import EvaluationEngine


PORT = 8080
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


class CandidatePipelineHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler providing REST endpoints and serving web dashboard UI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == "/api/benchmark":
            self.handle_api_benchmark()
        elif parsed_path.path == "/api/config":
            self.handle_api_get_config()
        elif parsed_path.path == "/api/schema":
            self.handle_api_get_schema()
        else:
            # Fallback to serving web directory files (e.g. index.html)
            if parsed_path.path == "/":
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == "/api/ingest":
            self.handle_api_ingest()
        elif parsed_path.path == "/api/config":
            self.handle_api_update_config()
        else:
            self.send_error(404, "Endpoint not found")

    def handle_api_ingest(self):
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8")
            payload = json.loads(post_body) if post_body else {}

            # Support direct JSON payload or file paths
            pipeline = CandidateTransformationPipeline()

            if "raw_json" in payload:
                # Save temporary JSON payload
                temp_file = "data/_temp_upload.json"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(payload["raw_json"], f)
                result = pipeline.process_files([temp_file])
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            else:
                files = payload.get("files", ["data/sample_candidates.json", "data/sample_candidates.csv"])
                result = pipeline.process_files(files)

            self.send_json_response(200, result.to_dict())

        except Exception as e:
            self.send_json_response(500, {"error": f"Ingestion failed: {str(e)}"})

    def handle_api_benchmark(self):
        try:
            evaluator = EvaluationEngine()
            report = evaluator.run_benchmark(["data/sample_candidates.json", "data/sample_candidates.csv", "data/sample_resumes.txt"])
            self.send_json_response(200, report)
        except Exception as e:
            self.send_json_response(500, {"error": f"Benchmark failed: {str(e)}"})

    def handle_api_get_config(self):
        try:
            with open("config/field_mappings.json", "r", encoding="utf-8") as f:
                mappings = json.load(f)
            with open("config/dedup_rules.json", "r", encoding="utf-8") as f:
                dedup = json.load(f)
            self.send_json_response(200, {"field_mappings": mappings, "dedup_rules": dedup})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_api_update_config(self):
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_len).decode("utf-8"))
            if "field_mappings" in body:
                with open("config/field_mappings.json", "w", encoding="utf-8") as f:
                    json.dump(body["field_mappings"], f, indent=2)
            if "dedup_rules" in body:
                with open("config/dedup_rules.json", "w", encoding="utf-8") as f:
                    json.dump(body["dedup_rules"], f, indent=2)
            self.send_json_response(200, {"status": "success", "message": "Configurations updated successfully"})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def handle_api_get_schema(self):
        try:
            with open("config/output_schema.json", "r", encoding="utf-8") as f:
                schema = json.load(f)
            self.send_json_response(200, schema)
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

    def send_json_response(self, code: int, data: Dict[str, Any]):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def start_server(port: int = PORT):
    os.makedirs(WEB_DIR, exist_ok=True)
    with socketserver.TCPServer(("", port), CandidatePipelineHandler) as httpd:
        print(f"[+] Server running at http://localhost:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    start_server()
