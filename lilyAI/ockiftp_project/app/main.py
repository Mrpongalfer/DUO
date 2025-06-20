from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED
import shutil
import os
import subprocess
import uuid

app = FastAPI(
    title="Omnitide Codex Knowledge Ingestion & Fine-Tuning Pipeline (OCKIFT-P)"
)

UPLOAD_DIR = "/tmp/ockiftp_uploads"
FINE_TUNE_DIR = "/tmp/ockiftp_finetune"
ALLOWED_EXTENSIONS = {"txt", "jsonl"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FINE_TUNE_DIR, exist_ok=True)

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.environ.get("OCKIFT_USER", "ockift_admin")
    correct_password = os.environ.get("OCKIFT_PASS", "supersecurepass")
    if not (
        credentials.username == correct_username
        and credentials.password == correct_password
    ):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.post("/ingest")
def ingest(file: UploadFile = File(...), username: str = Depends(verify_credentials)):
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    file_id = str(uuid.uuid4())
    dest_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Optionally, add data validation/cleaning here
    return {"status": "success", "file_id": file_id, "path": dest_path}


@app.post("/fine_tune")
def fine_tune(
    file_id: str, epochs: int = 1, username: str = Depends(verify_credentials)
):
    # Find the file
    matching = [f for f in os.listdir(UPLOAD_DIR) if f.startswith(file_id)]
    if not matching:
        raise HTTPException(status_code=404, detail="File not found.")
    data_path = os.path.join(UPLOAD_DIR, matching[0])
    run_id = str(uuid.uuid4())
    output_dir = os.path.join(FINE_TUNE_DIR, run_id)
    os.makedirs(output_dir, exist_ok=True)
    # Call the fine-tuning script
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
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Fine-tuning failed: {e.stderr}")
    return {
        "status": "fine_tuning_started",
        "run_id": run_id,
        "output_dir": output_dir,
        "stdout": result.stdout,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
