import os
import re
import bleach
import hmac
import hashlib
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette.status import HTTP_401_UNAUTHORIZED
import shutil
import subprocess
from jose import JWTError, jwt
from datetime import datetime

UPLOAD_DIR = "/opt/omnitide_nexus/uploads"
FINE_TUNE_DIR = "/opt/omnitide_nexus/finetuned_models"
HMAC_SECRET = os.environ.get("OCKIFTP_HMAC_SECRET", "supersecretkey")
JWT_SECRET = os.environ.get("LCSAF_JWT_SECRET", "changeme")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FINE_TUNE_DIR, exist_ok=True)

app = FastAPI(title="OCKIFT-P Refactored")


# JWT validation
def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return username
    except JWTError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")


# Advanced data processing
def sanitize(text):
    text = bleach.clean(text)
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)
    return text


def chunk_text(text, chunk_size=1024, overlap=128):
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i : i + chunk_size]
        chunks.append(chunk)
    return chunks


def deduplicate(chunks):
    seen = set()
    deduped = []
    for chunk in chunks:
        h = hashlib.sha256(chunk.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            deduped.append(chunk)
    return deduped


def sign_chunk(chunk):
    return hmac.new(HMAC_SECRET.encode(), chunk.encode(), hashlib.sha256).hexdigest()


@app.post("/ingest")
def ingest(file: UploadFile = File(...), username: str = Depends(verify_token)):
    ext = file.filename.split(".")[-1].lower()
    if ext not in {"txt", "jsonl"}:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    file_id = str(uuid.uuid4())
    dest_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    with open(dest_path, "r", encoding="utf-8") as f:
        raw = f.read()
    sanitized = sanitize(raw)
    chunks = chunk_text(sanitized)
    chunks = deduplicate(chunks)
    signatures = [sign_chunk(chunk) for chunk in chunks]
    chunked_path = dest_path + ".chunks"
    with open(chunked_path, "w", encoding="utf-8") as f:
        for chunk, sig in zip(chunks, signatures):
            f.write(f"{sig}\t{chunk}\n")
    return {
        "status": "success",
        "file_id": file_id,
        "chunks": len(chunks),
        "chunked_path": chunked_path,
    }


@app.post("/fine_tune")
def fine_tune(file_id: str, epochs: int = 1, username: str = Depends(verify_token)):
    matching = [f for f in os.listdir(UPLOAD_DIR) if f.startswith(file_id)]
    if not matching:
        raise HTTPException(status_code=404, detail="File not found.")
    data_path = os.path.join(UPLOAD_DIR, matching[0])
    run_id = datetime.now().strftime("llama3_omnitide_v%Y%m%d_%H%M%S")
    output_dir = os.path.join(FINE_TUNE_DIR, run_id)
    os.makedirs(output_dir, exist_ok=True)
    try:
        result = subprocess.run(
            [
                "python3",
                "-u",
                "fine_tuning_scripts/train.py",
                "--data",
                data_path,
                "--output",
                output_dir,
                "--epochs",
                str(epochs),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # Quantization & pruning
        subprocess.run(
            [
                "python3",
                "-u",
                "fine_tuning_scripts/optimize_model.py",
                "--model_dir",
                output_dir,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # Versioning
        latest_symlink = os.path.join(FINE_TUNE_DIR, "latest")
        if os.path.islink(latest_symlink) or os.path.exists(latest_symlink):
            os.remove(latest_symlink)
        os.symlink(output_dir, latest_symlink)
    except subprocess.CalledProcessError as e:
        # Rollback: revert symlink to previous if exists
        raise HTTPException(status_code=500, detail=f"Fine-tuning failed: {e.stderr}")
    return {
        "status": "fine_tuning_complete",
        "run_id": run_id,
        "output_dir": output_dir,
        "stdout": result.stdout,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
