"""Caché JSON local con escritura atómica; no contiene claves ni datos clínicos."""
import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EvidenceCache:
    def __init__(self, path, ttl_seconds=86400, records_key="articles"):
        self.path = Path(path)
        self.ttl = ttl_seconds
        self.records_key = records_key
        self.lock = threading.RLock()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            self.entries = {key: entry for key, entry in value.items() if isinstance(entry, dict) and isinstance(entry.get(self.records_key), list)} if isinstance(value, dict) else {}
        except (OSError, ValueError):
            self.entries = {}

    @staticmethod
    def key(params):
        raw = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, params):
        with self.lock:
            value = self.entries.get(self.key(params))
            if not isinstance(value, dict) or not isinstance(value.get(self.records_key), list):
                return None
            return json.loads(json.dumps(value))

    def fresh(self, entry):
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(entry["fetched_at"])
            return 0 <= age.total_seconds() < self.ttl
        except (KeyError, ValueError, TypeError):
            return False

    def put(self, params, value):
        with self.lock:
            entries = dict(self.entries)
            entries[self.key(params)] = dict(value, params=params)
            entries = dict(sorted(entries.items(), key=lambda item: item[1].get("fetched_at", ""))[-100:])
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as target:
                os.fchmod(target.fileno(), 0o600)
                json.dump(entries, target, ensure_ascii=False, indent=2)
                target.flush()
                os.fsync(target.fileno())
            temporary.replace(self.path)
            self.entries = entries

    def parameters(self):
        with self.lock:
            return [value["params"] for value in self.entries.values() if "params" in value]

    def clear(self):
        with self.lock:
            if self.path.exists():
                self.path.unlink()
            self.entries = {}
