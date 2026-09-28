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


AUDIT_LOG_FILE = "data/audit_log.json"
PORT = 8080
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")


def get_audit_logs() -> list:
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def append_audit_log(entry: dict):
    logs = get_audit_logs()
    logs.append(entry)
    os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
    with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


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
        elif parsed_path.path == "/api/audit-trail":
            self.handle_api_get_audit_trail()
        else:
            if parsed_path.path == "/":
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == "/api/ingest":
            self.handle_api_ingest()
        elif parsed_path.path == "/api/config":
            self.handle_api_update_config()
        elif parsed_path.path == "/api/override":
            self.handle_api_override()
        else:
            self.send_error(404, "Endpoint not found")

    def handle_api_ingest(self):
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else ""
            payload = json.loads(post_body) if post_body else {}

            pipeline = CandidateTransformationPipeline()

            if "raw_json" in payload:
                temp_file = "data/_temp_upload.json"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(payload["raw_json"], f)
                result = pipeline.process_files([temp_file])
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            else:
                files = payload.get("files", ["data/sample_candidates.json", "data/sample_candidates.csv"])
                result = pipeline.process_files(files)

            res_dict = result.to_dict()
            res_dict["audit_trail"] = get_audit_logs()
            self.send_json_response(200, res_dict)

        except Exception as e:
            self.send_json_response(500, {"error": f"Ingestion failed: {str(e)}"})

    def handle_api_override(self):
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            body_str = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else ""
            body = json.loads(body_str) if body_str else {}

            candidate_id = body.get("candidate_id")
            field_name = body.get("field_name")
            new_value = body.get("new_value")
            reviewer_id = body.get("reviewer_id", "recruiter_admin")
            reason = body.get("reason", "Manual review override")

            if not candidate_id or not field_name:
                self.send_json_response(400, {"error": "Missing mandatory parameters: candidate_id and field_name"})
                return

            import time
            entry = {
                "candidate_id": candidate_id,
                "field_name": field_name,
                "old_value": body.get("old_value"),
                "new_value": new_value,
                "reviewer_id": reviewer_id,
                "reason": reason,
                "timestamp": time.time()
            }
            append_audit_log(entry)

            self.send_json_response(200, {
                "status": "success",
                "message": f"Successfully recorded override for {candidate_id}.{field_name}",
                "override_entry": entry,
                "audit_trail": get_audit_logs()
            })
        except Exception as e:
            self.send_json_response(500, {"error": f"Human override failed: {str(e)}"})

    def handle_api_get_audit_trail(self):
        try:
            logs = get_audit_logs()
            self.send_json_response(200, {"audit_logs": logs, "total_count": len(logs)})
        except Exception as e:
            self.send_json_response(500, {"error": str(e)})

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
