import requests
import json
import os
import hashlib
import hmac
import bleach
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter


class OckiftRefinementAgent:
    def __init__(self):
        self.ockiftp_url = os.environ.get("OCKIFTP_URL", "http://localhost:8000")
        self.jwt_token = os.environ.get("OCKIFTP_JWT", "")
        self.hmac_secret = os.environ.get("OCKIFTP_HMAC_SECRET", "supersecretkey")
        self.upload_dir = "/opt/omnitide_nexus/uploads"
        self.finetune_dir = "/opt/omnitide_nexus/finetuned_models"

    def sanitize(self, text):
        text = bleach.clean(text)
        text = re.sub(r"[\x00-\x1F\x7F]", "", text)
        return text

    def chunk_and_dedup(self, text):
        splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=128)
        chunks = splitter.split_text(text)
        seen = set()
        deduped = []
        for chunk in chunks:
            h = hashlib.sha256(chunk.encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                deduped.append(chunk)
        return deduped

    def sign_chunk(self, chunk):
        return hmac.new(
            self.hmac_secret.encode(), chunk.encode(), hashlib.sha256
        ).hexdigest()

    def generate_finetune_examples(self):
        # Placeholder: Analyze logs, generate JSONL examples
        examples = [
            {
                "instruction": "Refactor code for security.",
                "input": "...",
                "output": "...",
            }
        ]
        return examples

    def push_to_ockiftp(self, examples):
        jsonl = "\n".join(json.dumps(e) for e in examples)
        files = {"file": ("finetune_examples.jsonl", jsonl)}
        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        r = requests.post(f"{self.ockiftp_url}/ingest", files=files, headers=headers)
        return r.json()

    def trigger_fine_tune(self):
        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        data = {"file_id": "latest", "epochs": 1}
        r = requests.post(f"{self.ockiftp_url}/fine_tune", json=data, headers=headers)
        return r.json()

    def output_refactored_files(self):
        with open("ockiftp_main_refactored.py") as f:
            main_code = f.read()
        with open("ockiftp_train_refactored.py") as f:
            train_code = f.read()
        with open("fine_tuning_scripts/optimize_model.py") as f:
            optimize_code = f.read()
        return main_code, train_code, optimize_code
