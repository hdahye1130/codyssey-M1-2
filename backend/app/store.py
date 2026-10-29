"""Persistent storage: Firestore for deployment; JSON only for explicitly selected local demo."""
import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache


def now():
    return datetime.now(timezone.utc).isoformat()


class LocalDemoStore:
    """Local-only file store, never a substitute for deployed Firestore."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        if not self.path.exists():
            self.path.write_text(json.dumps({"data": {}, "conversations": {}}, ensure_ascii=False), encoding="utf-8")

    def _read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, value):
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.path)

    def list_data(self):
        with self.lock:
            return sorted(deepcopy(list(self._read()["data"].values())), key=lambda row: row["date"])

    def get_data(self, id):
        with self.lock:
            return deepcopy(self._read()["data"].get(id))

    def create_data(self, record):
        with self.lock:
            db = self._read()
            if record["id"] in db["data"]:
                return False
            db["data"][record["id"]] = record
            self._write(db)
            return True

    def update_data(self, id, record):
        with self.lock:
            db = self._read()
            if id not in db["data"]:
                return False
            db["data"][id] = record
            self._write(db)
            return True

    def delete_data(self, id):
        with self.lock:
            db = self._read()
            if id not in db["data"]:
                return False
            del db["data"][id]
            self._write(db)
            return True

    def seed_rows(self, records):
        with self.lock:
            db = self._read()
            count = 0
            for record in records:
                if record["id"] not in db["data"]:
                    db["data"][record["id"]] = record
                    count += 1
            if count:
                self._write(db)
            return count

    def list_conversations(self):
        with self.lock:
            values = deepcopy(list(self._read()["conversations"].values()))
        return sorted(values, key=lambda c: c["updated_at"], reverse=True)

    def get_conversation(self, id):
        with self.lock:
            return deepcopy(self._read()["conversations"].get(id))

    def save_conversation(self, record):
        with self.lock:
            db = self._read()
            if not record.get("id"):
                record["id"] = uuid.uuid4().hex
            record = deepcopy(record)
            db["conversations"][record["id"]] = record
            self._write(db)
            return record

    def delete_conversation(self, id):
        with self.lock:
            db = self._read()
            if id not in db["conversations"]:
                return False
            del db["conversations"][id]
            self._write(db)
            return True


class FirestoreStore:
    def __init__(self):
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            credentials_json = os.environ.get("FIREBASE_CREDENTIALS_JSON", "").strip()
            if credentials_json:
                firebase_admin.initialize_app(credentials.Certificate(json.loads(credentials_json)))
            else:
                # Render: alternatively use GOOGLE_APPLICATION_CREDENTIALS with an absolute file path.
                firebase_admin.initialize_app(credentials.ApplicationDefault())
        self.db = firestore.client()

    def list_data(self):
        return [{"id": d.id, **d.to_dict()} for d in self.db.collection("data").stream()]

    def get_data(self, id):
        doc = self.db.collection("data").document(id).get()
        return {"id": doc.id, **doc.to_dict()} if doc.exists else None

    def create_data(self, record):
        from google.api_core.exceptions import Conflict
        try:
            self.db.collection("data").document(record["id"]).create({k: v for k, v in record.items() if k != "id"})
            return True
        except Conflict:
            return False

    def update_data(self, id, record):
        from google.api_core.exceptions import NotFound
        try:
            self.db.collection("data").document(id).update({k: v for k, v in record.items() if k != "id"})
            return True
        except NotFound:
            return False

    def delete_data(self, id):
        ref = self.db.collection("data").document(id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True

    def seed_rows(self, records):
        existing = {record["id"] for record in self.list_data()}
        missing = [record for record in records if record["id"] not in existing]
        for offset in range(0, len(missing), 400):
            batch = self.db.batch()
            for row in missing[offset:offset + 400]:
                ref = self.db.collection("data").document(row["id"])
                batch.set(ref, {k: v for k, v in row.items() if k != "id"})
            batch.commit()
        return len(missing)

    def list_conversations(self):
        return sorted(
            [{"id": d.id, **d.to_dict()} for d in self.db.collection("conversations").stream()],
            key=lambda c: c.get("updated_at", ""), reverse=True
        )

    def get_conversation(self, id):
        doc = self.db.collection("conversations").document(id).get()
        return {"id": doc.id, **doc.to_dict()} if doc.exists else None

    def save_conversation(self, record):
        record = deepcopy(record)
        if not record.get("id"):
            record["id"] = uuid.uuid4().hex
        self.db.collection("conversations").document(record["id"]).set(
            {k: v for k, v in record.items() if k != "id"}
        )
        return record

    def delete_conversation(self, id):
        ref = self.db.collection("conversations").document(id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True


@lru_cache(maxsize=1)
def get_store():
    if os.environ.get("LOCAL_DEMO", "0") == "1":
        return LocalDemoStore(os.environ.get("LOCAL_DATA_FILE", "./.local/demo.json"))
    return FirestoreStore()
