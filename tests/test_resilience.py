"""
System Resilience & Service Interruption Test Suite
Evaluates concurrent API request handling, partial payload recoveries, service interruption resilience, and audit trail persistence.
"""

import unittest
import os
import json
import time
import threading
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from server import start_server, PORT, append_audit_log, get_audit_logs


class TestSystemResilience(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.port = 8089
        cls.server_thread = threading.Thread(target=start_server, kwargs={"port": cls.port}, daemon=True)
        cls.server_thread.start()
        time.sleep(1.0)  # Wait for server socket bind

    def test_audit_log_persistence(self):
        entry = {
            "candidate_id": "CAN-TEST-100",
            "field_name": "email",
            "old_value": "old@example.com",
            "new_value": "new@example.com",
            "reviewer_id": "test_reviewer",
            "reason": "Resilience test override",
            "timestamp": time.time()
        }
        append_audit_log(entry)

        logs = get_audit_logs()
        self.assertGreater(len(logs), 0)
        matching = [l for l in logs if l.get("candidate_id") == "CAN-TEST-100"]
        self.assertGreater(len(matching), 0)
        self.assertEqual(matching[-1]["new_value"], "new@example.com")

    def test_concurrent_api_requests(self):
        url_ingest = f"http://localhost:{self.port}/api/ingest"
        url_override = f"http://localhost:{self.port}/api/override"

        def make_ingest_request(idx):
            payload = json.dumps({"raw_json": [{"candidate_name": f"Concurrent Candidate {idx}", "email_address": f"user{idx}@test.com"}]}).encode("utf-8")
            req = urllib.request.Request(url_ingest, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))

        def make_override_request(idx):
            payload = json.dumps({
                "candidate_id": f"CAN-{idx:04d}",
                "field_name": "email",
                "new_value": f"override{idx}@test.com",
                "reviewer_id": f"reviewer_{idx}",
                "reason": "Concurrent stress override"
            }).encode("utf-8")
            req = urllib.request.Request(url_override, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))

        # Launch 10 concurrent requests across ingestion and overrides
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):
                futures.append(executor.submit(make_ingest_request, i))
                futures.append(executor.submit(make_override_request, i))

            for fut in as_completed(futures):
                status, data = fut.result()
                self.assertEqual(status, 200)

    def test_service_interruption_and_invalid_payloads(self):
        url_ingest = f"http://localhost:{self.port}/api/ingest"
        url_override = f"http://localhost:{self.port}/api/override"

        # 1. Invalid JSON body
        payload_bad = b"{malformed json"
        req = urllib.request.Request(url_ingest, data=payload_bad, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code

        self.assertEqual(status, 500)

        # 2. Missing required override parameters
        payload_missing = json.dumps({"candidate_id": "CAN-123"}).encode("utf-8")
        req_over = urllib.request.Request(url_override, data=payload_missing, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req_over) as resp:
                status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code

        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
