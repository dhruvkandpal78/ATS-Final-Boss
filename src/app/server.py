import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import dataclasses
import mimetypes

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.append(os.path.abspath(ROOT))

import pandas as pd
from src.core.analysis_service import AnalysisService
from src.utils.json_encoder import RobustJSONEncoder
from src.core.schemas import (
    AnalysisResult, ModelInfo, CoverageInfo, TimingInfo, ModuleResult, Finding
)

HERE = os.path.dirname(__file__)
MODELS_DIR = os.path.join(ROOT, "results", "models")
DIST_DIR = os.path.join(ROOT, "web", "dist")

print("[server] Booting neural defense core - loading models...")
analysis_service = AnalysisService(MODELS_DIR)
print("[server] Models loaded. Shield online.")

class APIHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        
    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        # Serve React dist files
        path = self.path
        if path == '/':
            path = '/index.html'
            
        # React router fallback
        file_path = os.path.join(DIST_DIR, path.lstrip('/'))
        if not os.path.exists(file_path):
            file_path = os.path.join(DIST_DIR, 'index.html')
            
        if os.path.exists(file_path):
            self.send_response(200)
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                self.send_header('Content-type', mime_type)
            self.end_headers()
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def do_POST(self):
        if self.path == '/api/analyze':
            start_time = time.time()
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 5 * 1024 * 1024:
                self.send_response(413)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(b'{"error": "payload_too_large"}')
                return

            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
            except Exception:
                self.send_response(400)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(b'{"error": "invalid_json"}')
                return

            mode = data.get("mode", "text")
            text = data.get("text", "")
            
            if mode == "pdf" and "b64" in data:
                pdf_bytes = base64.b64decode(data["b64"])
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text("text") + "\n"
                doc.close()

            res = analysis_service.analyze_text(text, b_score=0.0)

            a_score = res['features']['Module_A_Score']
            c_score = res['features']['Module_C_Score']
            
            decision = "review_recommended" if res['policy_decision'] else "no_signals_detected"
            reason_codes = []
            if res.get('injection_cues', 0) > 0:
                reason_codes.append("prompt_injection")
            if a_score > 0.9:
                reason_codes.append("keyword_stuffing")

            findings = []
            if a_score > 0.9:
                findings.append(Finding(
                    id="f1", detector="a", category="keyword_stuffing", severity="high",
                    explanation="Suspiciously high keyword density detected."
                ))
            if res.get('injection_cues', 0) > 0:
                findings.append(Finding(
                    id="f2", detector="c", category="prompt_injection", severity="high",
                    explanation="Prompt injection instruction detected."
                ))

            result = AnalysisResult(
                state="complete",
                schema_version="2.0",
                analysis_id=str(uuid.uuid4()),
                created_at=datetime.now(timezone.utc).isoformat(),
                status="complete",
                input_mode=mode,
                model=ModelInfo(id="ensemble-v1", calibrated=True),
                policy_version="1.0",
                decision=decision,
                reason_codes=reason_codes,
                coverage=CoverageInfo(pages_total=1, pages_analyzed=1),
                score=res['policy_proba'],
                score_kind="calibrated_probability",
                modules={
                    "a": ModuleResult(status="ok", score=a_score, findings=[f for f in findings if f.detector=="a"]),
                    "b": ModuleResult(status="ok", score=0.0, findings=[]),
                    "c": ModuleResult(status="ok", score=c_score, findings=[f for f in findings if f.detector=="c"])
                },
                findings=findings,
                timings_ms=TimingInfo(total=int((time.time() - start_time) * 1000))
            )

            response_json = json.dumps(dataclasses.asdict(result), cls=RobustJSONEncoder)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(response_json.encode('utf-8'))

def run(server_class=ThreadingHTTPServer, handler_class=APIHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"[server] Serving on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
