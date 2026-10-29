"""API /docs, public health check, protected data + conversations + chat."""
import os
import secrets
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from app.models import DataCreate, DataUpdate, ConversationCreate, ChatRequest
from app.store import get_store, now
from app.service import summarize, make_data_context, ask_copa

load_dotenv()
app = FastAPI(title="KPX Solar Data AI Assistant", version="1.0.0")
origins = [x.strip() for x in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["X-App-Token", "Content-Type"])


def verify_access(x_app_token: str | None = Header(default=None)):
    expected = os.environ.get("APP_ACCESS_TOKEN", "")
    if not expected and os.environ.get("LOCAL_DEMO") != "1":
        raise HTTPException(status_code=503, detail="서버에 APP_ACCESS_TOKEN 설정이 필요합니다.")
    if expected and not secrets.compare_digest((x_app_token or "").encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=401, detail="접근 코드가 올바르지 않습니다.")


def store():
    try:
        return get_store()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="데이터베이스 연결을 확인하세요.") from exc


@app.get("/health")
def health():
    return {"status": "ok", "mode": "local-demo" if os.getenv("LOCAL_DEMO") == "1" else "firestore"}


@app.get("/api/data", dependencies=[Depends(verify_access)])
def list_data(db=Depends(store)):
    return sorted(db.list_data(), key=lambda r: r["date"])


@app.get("/api/data/summary", dependencies=[Depends(verify_access)])
def data_summary(db=Depends(store)):
    return summarize(db.list_data())


@app.post("/api/data", status_code=201, dependencies=[Depends(verify_access)])
def add_data(payload: DataCreate, db=Depends(store)):
    record = {"id": payload.date.isoformat(), "date": payload.date.isoformat(),
              "value": payload.value, "memo": payload.memo, "source": "사용자 입력"}
    if not db.create_data(record):
        raise HTTPException(status_code=409, detail="이미 존재하는 날짜입니다.")
    return record


@app.put("/api/data/{id}", dependencies=[Depends(verify_access)])
def edit_data(id: str, payload: DataUpdate, db=Depends(store)):
    original = db.get_data(id)
    if not original:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    updated = {**original, "value": payload.value, "memo": payload.memo, "source": "사용자 수정"}
    if not db.update_data(id, updated):
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    return updated


@app.delete("/api/data/{id}", dependencies=[Depends(verify_access)])
def remove_data(id: str, db=Depends(store)):
    if not db.delete_data(id):
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    return {"deleted": id}


@app.post("/api/conversations", status_code=201, dependencies=[Depends(verify_access)])
def create_conversation(payload: ConversationCreate, db=Depends(store)):
    stamp = now()
    record = {"id": None, "title": payload.title or "새 대화",
              "messages": [m.model_dump() for m in payload.messages],
              "created_at": stamp, "updated_at": stamp}
    return db.save_conversation(record)


@app.get("/api/conversations", dependencies=[Depends(verify_access)])
def list_conversations(db=Depends(store)):
    return [{"id": c["id"], "title": c["title"], "created_at": c["created_at"],
             "updated_at": c["updated_at"], "message_count": len(c.get("messages", []))}
            for c in db.list_conversations()]


@app.get("/api/conversations/{id}", dependencies=[Depends(verify_access)])
def get_conversation(id: str, db=Depends(store)):
    record = db.get_conversation(id)
    if not record:
        raise HTTPException(status_code=404, detail="대화가 없습니다.")
    return record


@app.delete("/api/conversations/{id}", dependencies=[Depends(verify_access)])
def delete_conversation(id: str, db=Depends(store)):
    if not db.delete_conversation(id):
        raise HTTPException(status_code=404, detail="대화가 없습니다.")
    return {"deleted": id}


@app.post("/api/chat", dependencies=[Depends(verify_access)])
def chat(payload: ChatRequest, db=Depends(store)):
    convo = db.get_conversation(payload.conversation_id) if payload.conversation_id else None
    if payload.conversation_id and convo is None:
        raise HTTPException(status_code=404, detail="대화 기록을 찾을 수 없습니다.")
    history = convo.get("messages", []) if convo else []
    rows = db.list_data()
    stats = summarize(rows)
    context = make_data_context(stats, rows, payload.question)
    try:
        answer = ask_copa(payload.question, history, context)
    except Exception as exc:
        # Log safe metadata only; never expose API keys or raw upstream response bodies.
        import logging
        response = getattr(exc, "response", None)
        status = response.status_code if response is not None else None
        body = None
        if response is not None:
            try:
                error_payload = response.json()
                body = error_payload.get("error") if isinstance(error_payload, dict) else None
            except ValueError:
                pass
        error_code = body.get("code") if isinstance(body, dict) else None
        if error_code not in {
            "credit_balance_exhausted", "insufficient_quota",
            "organization_usage_limit_exceeded", "organization_spend_limit_exceeded",
            "project_spend_limit_exceeded", "model_not_found"
        }:
            error_code = "unspecified"
        logging.getLogger("uvicorn.error").error(
            "COPA call failed: error_type=%s status=%s code=%s",
            type(exc).__name__, status, error_code
        )
        if status == 401:
            detail = "COPA 인증 오류(401): Render의 COPA_API_KEY가 올바른지 확인하세요."
        elif status == 429:
            detail = "COPA 사용 제한(429): API 결제 잔액과 사용 한도를 확인하세요."
        elif status == 403:
            detail = "COPA 접근 제한(403): 프로젝트 및 모델 접근 권한을 확인하세요."
        elif status == 404:
            detail = "COPA 모델 오류(404): COPA_MODEL 설정을 확인하세요."
        else:
            detail = "AI 호출에 실패했습니다. Render 로그의 COPA 오류 유형과 상태 코드를 확인하세요."
        raise HTTPException(status_code=503, detail=detail) from exc
    messages = (history + [{"role": "user", "content": payload.question},
                           {"role": "assistant", "content": answer}])[-30:]
    stamp = now()
    saved = db.save_conversation({"id": convo["id"] if convo else None,
                                  "title": convo["title"] if convo else payload.question[:60],
                                  "messages": messages,
                                  "created_at": convo["created_at"] if convo else stamp,
                                  "updated_at": stamp})
    return {"answer": answer, "conversation_id": saved["id"], "data_count": stats["count"]}
