import os
import csv
from pathlib import Path

os.environ["LOCAL_DEMO"] = "1"
os.environ.pop("APP_ACCESS_TOKEN", None)

from fastapi.testclient import TestClient
from app import main
from app.store import LocalDemoStore
from seed_data import read_rows, get_csv_path


def test_project_csv():
    from datetime import date, timedelta
    from decimal import Decimal

    path = Path(__file__).resolve().parents[2] / "data" / "daily_solar.csv"
    assert get_csv_path() == path
    rows = read_rows(path)
    assert [r["date"] for r in rows] == [
        (date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(365)
    ]
    with path.open() as f:
        assert sum(Decimal(r["energy_mwh"]) for r in csv.DictReader(f)) == Decimal("12522309.071856")


def test_unicode_access_token(monkeypatch):
    monkeypatch.setenv("APP_ACCESS_TOKEN", "한글-접근코드")
    main.verify_access("한글-접근코드")
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        main.verify_access("wrong-token")
    assert exc.value.status_code == 401


def test_seed_uses_original_csv(tmp_path):
    p = tmp_path / "daily_solar.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "energy_mwh"])
        writer.writeheader()
        for i in range(1, 102):
            from datetime import date, timedelta
            writer.writerow({"date": (date(2025, 1, 1) + timedelta(days=i-1)).isoformat(), "energy_mwh": i * 100.0})
    rows = read_rows(p)
    assert len(rows) == 101 and rows[0]["value"] == 100.0
    db = LocalDemoStore(str(tmp_path / "store.json"))
    assert db.seed_rows(rows) == 101
    assert db.seed_rows(rows) == 0


def test_crud_summary_conversations_chat(tmp_path, monkeypatch):
    db = LocalDemoStore(str(tmp_path / "store.json"))
    monkeypatch.setattr(main, "get_store", lambda: db)
    monkeypatch.setattr(main, "ask_copa", lambda q, history, context: "확인된 데이터에 근거한 답변입니다.")
    client = TestClient(main.app)
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    r = client.post("/api/data", json={"date": "2025-01-01", "value": 100.5, "memo": "기존"})
    assert r.status_code == 201
    assert client.post("/api/data", json={"date": "2025-01-01", "value": 100.5}).status_code == 409
    assert client.post("/api/data", json={"date": "2025-01-02", "value": -4}).status_code == 422
    assert client.get("/api/data").json()[0]["value"] == 100.5
    s = client.get("/api/data/summary").json()
    assert s["count"] == 1 and s["average_mwh"] == 100.5
    assert client.put("/api/data/2025-01-01", json={"value": 201.5, "memo": "수정"}).json()["value"] == 201.5
    c = client.post("/api/conversations", json={"title": "첫 대화"}).json()
    assert c["title"] == "첫 대화"
    chat = client.post("/api/chat", json={"question": "평균은?", "conversation_id": c["id"]}).json()
    assert chat["conversation_id"] == c["id"]
    assert len(client.get("/api/conversations/" + c["id"]).json()["messages"]) == 2
    assert len(client.get("/api/conversations").json()) == 1
    assert client.delete("/api/conversations/" + c["id"]).status_code == 200
    assert client.delete("/api/data/2025-01-01").status_code == 200
    assert client.get("/api/data/summary").json()["count"] == 0


def test_auth_required(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "get_store", lambda: LocalDemoStore(str(tmp_path / "store2.json")))
    monkeypatch.setenv("APP_ACCESS_TOKEN", "test-secret")
    client = TestClient(main.app)
    assert client.get("/api/data").status_code == 401
    assert client.get("/api/data", headers={"X-App-Token": "test-secret"}).status_code == 200


def test_copa_request(monkeypatch):
    import requests
    from app.service import ask_copa

    monkeypatch.setenv("COPA_API_KEY", "test-virtual-key")
    monkeypatch.delenv("COPA_MODEL", raising=False)
    calls = []

    class Response:
        def raise_for_status(self):
            calls.append("status_checked")

        def json(self):
            assert calls == ["status_checked"]
            return {"choices": [{"message": {"content": " 답변 "}}]}

    def post(url, *, headers, json, timeout):
        assert url == "https://copa.codyssey.kr/v1/chat/completions"
        assert headers == {"Authorization": "Bearer test-virtual-key"}
        assert json["model"] == "gpt-5-mini"
        assert json["messages"][0]["role"] == "system"
        assert "태양광 데이터" in json["messages"][0]["content"]
        assert json["messages"][1:] == [
            {"role": "assistant", "content": "이전 답변"},
            {"role": "user", "content": "안녕하세요"},
        ]
        assert timeout == 60
        return Response()

    monkeypatch.setattr(requests, "post", post)
    assert ask_copa("안녕하세요", [{"role": "assistant", "content": "이전 답변"}], "태양광 데이터") == "답변"


def test_copa_http_errors_are_safe(tmp_path, monkeypatch, caplog):
    import requests

    db = LocalDemoStore(str(tmp_path / "errors.json"))
    monkeypatch.setattr(main, "get_store", lambda: db)
    monkeypatch.delenv("APP_ACCESS_TOKEN", raising=False)
    client = TestClient(main.app)
    for status, expected in [(401, "COPA_API_KEY"), (403, "403"), (404, "COPA_MODEL"), (429, "429"), (500, "실패")]:
        response = requests.Response()
        response.status_code = status
        response._content = b'{"error":{"code":"secret-upstream-detail","message":"secret-virtual-key"}}'

        def fail(*args):
            response.raise_for_status()

        monkeypatch.setattr(main, "ask_copa", fail)
        result = client.post("/api/chat", json={"question": "평균은?"})
        assert result.status_code == 503
        assert expected in result.json()["detail"]
        assert "secret-" not in result.text
    assert "secret-" not in caplog.text
    assert "status=401" in caplog.text
    assert db.list_conversations() == []
