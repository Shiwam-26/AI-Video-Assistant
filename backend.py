
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional
import asyncio

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from main import run_pipeline
from core.Rag_Engine import ask_question

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AI Video Assistant", version="1.0.0")

# Local in-memory sessions. Server restart clears sessions.
SESSIONS: dict[str, dict] = {}


class ChatRequest(BaseModel):
    session_id: str
    question: str


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AI Video Assistant"}


@app.post("/api/analyze")
async def analyze_video(
    source_type: str = Form(...),
    language: str = Form("english"),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    temp_path = None

    try:
        if language not in {"english", "hinglish"}:
            raise HTTPException(
                status_code=400,
                detail="Unsupported language."
            )

        if source_type == "youtube":
            if not url or not url.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Please enter a YouTube URL."
                )
            source = url.strip()

        elif source_type == "file":
            if file is None or not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="Please upload an audio or video file."
                )

            allowed = {
                ".mp3", ".wav", ".m4a", ".ogg", ".mp4",
                ".mov", ".mkv", ".webm", ".mpeg", ".mpga",
            }

            suffix = Path(file.filename).suffix.lower()

            if suffix not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file type."
                )

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
                dir=UPLOAD_DIR
            ) as tmp:
                shutil.copyfileobj(file.file, tmp)
                temp_path = tmp.name

            source = temp_path

        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid source type."
            )

        # Run the synchronous AI pipeline without blocking
        # FastAPI's async event loop.
        result = await asyncio.to_thread(
            run_pipeline, source, language
        )

        session_id = str(uuid.uuid4())

        SESSIONS[session_id] = {
            "result": result,
            "rag_chain": result.get("rag_chain"),
            "chat_history": [],
        }

        return {
            "session_id": session_id,
            "title": result.get("title") or "Video Analysis",
            "summary": result.get("summary") or "",
            "transcript": result.get("transcript") or "",
            "action_items": result.get("action_items") or "",
            "key_decisions": result.get("key_decisions") or "",
            "open_questions": result.get("open_questions") or "",
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Video analysis failed: {exc}"
        ) from exc

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

        if file is not None:
            await file.close()


@app.post("/api/chat")
async def chat(payload: ChatRequest):
    session = SESSIONS.get(payload.session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=(
                "Analysis session not found. "
                "Please analyze the video again."
            )
        )

    question = payload.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question."
        )

    try:
        answer = await asyncio.to_thread(
            ask_question,
            session["rag_chain"],
            question
        )

        answer = str(answer)

        session["chat_history"].extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])

        return {"answer": answer}

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not answer question: {exc}"
        ) from exc


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)
