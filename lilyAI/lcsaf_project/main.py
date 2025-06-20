from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
import os
from agents.ollama_interface_agent import query_llama
from memory.context_manager import ContextManager
from memory.vector_store import VectorStore
from memory.structured_knowledge import StructuredKnowledge
from agents.ockift_refinement_agent import OckiftRefinementAgent

SECRET_KEY = os.environ.get("LCSAF_JWT_SECRET", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI(
    title="Lily Core: Self-Awareness & Agentic Orchestration Framework (LCSAF)"
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

context_manager = ContextManager()
vector_store = VectorStore()
structured_knowledge = StructuredKnowledge()
ockift_agent = OckiftRefinementAgent()

users_db = {
    "architect": {
        "username": "architect",
        "password": os.environ.get("LCSAF_ARCHITECT_PASS", "architectpass"),
    }
}


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


@app.post("/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/chat")
def chat(request: Request, prompt: str, token: str = Depends(verify_token)):
    context = context_manager.get_context(token)
    memory = vector_store.retrieve_relevant(prompt)
    knowledge = structured_knowledge.query(prompt)
    response = query_llama(prompt, context, memory, knowledge)
    context_manager.update_context(token, prompt, response)
    return {"response": response}


@app.post("/self_improve")
def self_improve(token: str = Depends(verify_token)):
    # Analyze previous interactions, generate fine-tuning examples, push to OCKIFT-P
    fine_tune_examples = ockift_agent.generate_finetune_examples()
    ingest_result = ockift_agent.push_to_ockiftp(fine_tune_examples)
    fine_tune_result = ockift_agent.trigger_fine_tune()
    return {"ingest_result": ingest_result, "fine_tune_result": fine_tune_result}
