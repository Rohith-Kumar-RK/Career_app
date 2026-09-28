"""
db.py - MongoDB data layer (pymongo).

Settings come from environment variables / a .env file:
    MONGO_URI       (default mongodb://localhost:27017)   <- also works with MongoDB Atlas "mongodb+srv://..."
    MONGO_DATABASE  (default ai_career)

Collections: users, profiles, roadmaps, resumes, interview_results
"""
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient

load_dotenv(Path(__file__).parent / ".env")

DEMO_PASSWORD = "DemoProfile2026!"
_client = None


def db_name() -> str:
    return os.getenv("MONGO_DATABASE", "ai_career")


def mongo_uri() -> str:
    return os.getenv("MONGO_URI", "mongodb://localhost:27017")


def _db():
    global _client
    if _client is None:
        _client = MongoClient(mongo_uri(), serverSelectionTimeoutMS=5000, tz_aware=False)
    return _client[db_name()]


def init_db() -> None:
    """Check the connection and create indexes (collections are created lazily by MongoDB)."""
    d = _db()
    d.client.admin.command("ping")          # raises if the server is unreachable
    d.users.create_index("email", unique=True)
    d.profiles.create_index("user_id", unique=True)
    d.roadmaps.create_index("user_id", unique=True)
    d.resumes.create_index("user_id", unique=True)
    d.interview_results.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])


def _now():
    return datetime.utcnow()


# ------------------------------------------------------------------ passwords
def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    iters = 200_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iters)
    return f"pbkdf2_sha256${iters}${salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# ------------------------------------------------------------------ users
def create_user(email: str, password: str, full_name: str) -> dict:
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Please enter a valid email address.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    d = _db()
    if d.users.find_one({"email": email}):
        raise ValueError("An account with this email already exists. Please sign in.")
    res = d.users.insert_one({"email": email, "password_hash": _hash_password(password),
                              "full_name": full_name.strip(), "created_at": _now()})
    uid = str(res.inserted_id)
    d.profiles.insert_one({"user_id": uid, "full_name": full_name.strip(), "ats_score": 0,
                           "strengths": [], "weaknesses": [], "created_at": _now(), "updated_at": _now()})
    return {"id": uid, "email": email, "full_name": full_name.strip()}


def authenticate(email: str, password: str) -> dict:
    row = _db().users.find_one({"email": email.strip().lower()})
    if not row or not _verify_password(password, row["password_hash"]):
        raise ValueError("Invalid email or password.")
    return {"id": str(row["_id"]), "email": row["email"], "full_name": row["full_name"]}


def load_demo_user(demo: dict) -> dict:
    """Create (or refresh) the demo account for a demo profile and return the user."""
    email = f"demo.{demo['key']}@aimastermind.ai"
    try:
        user = authenticate(email, DEMO_PASSWORD)
    except ValueError:
        user = create_user(email, DEMO_PASSWORD, demo["name"])
    save_profile(user["id"], {
        "full_name": demo["name"], "stream": demo["stream"], "stream_detail": demo["streamKey"],
        "status": demo["status"], "academic_score": demo["academicScore"], "ambition": demo["ambition"],
        "budget": demo["budget"], "strengths": demo["strengths"], "weaknesses": demo["weaknesses"],
    })
    user["full_name"] = demo["name"]
    return user


# ------------------------------------------------------------------ profile
_PROFILE_COLS = ("full_name", "stream", "stream_detail", "status", "academic_score",
                 "ambition", "budget", "strengths", "weaknesses", "ats_score")


def get_profile(user_id: str) -> dict | None:
    row = _db().profiles.find_one({"user_id": user_id})
    if not row:
        return None
    row.pop("_id", None)
    row.setdefault("strengths", [])
    row.setdefault("weaknesses", [])
    row.setdefault("ats_score", 0)
    return row


def save_profile(user_id: str, fields: dict) -> None:
    fields = {k: v for k, v in fields.items() if k in _PROFILE_COLS}
    _db().profiles.update_one(
        {"user_id": user_id},
        {"$set": {**fields, "updated_at": _now()}, "$setOnInsert": {"created_at": _now()}},
        upsert=True)


# ------------------------------------------------------------------ resume
def get_resume(user_id: str) -> dict | None:
    row = _db().resumes.find_one({"user_id": user_id})
    if not row:
        return None
    return {"data": row["data"], "ats_score": row.get("ats_score", 0), "updated_at": row.get("updated_at")}


def save_resume(user_id: str, data: dict, ats_score: int) -> None:
    _db().resumes.update_one(
        {"user_id": user_id},
        {"$set": {"title": "My Resume", "data": data, "ats_score": ats_score, "updated_at": _now()},
         "$setOnInsert": {"created_at": _now()}},
        upsert=True)
    save_profile(user_id, {"ats_score": ats_score})


# ------------------------------------------------------------------ roadmap
def get_roadmap(user_id: str) -> list | None:
    row = _db().roadmaps.find_one({"user_id": user_id})
    return row["phases"] if row else None


def save_roadmap(user_id: str, title: str, phases: list) -> None:
    _db().roadmaps.update_one(
        {"user_id": user_id},
        {"$set": {"title": title, "phases": phases, "updated_at": _now()},
         "$setOnInsert": {"created_at": _now()}},
        upsert=True)


# ------------------------------------------------------------------ interviews
def save_interview(user_id: str, stream: str, score: int, details: list) -> None:
    _db().interview_results.insert_one({"user_id": user_id, "stream": stream, "score": score,
                                        "details": details, "created_at": _now()})


def list_interviews(user_id: str, limit: int = 10) -> list:
    cur = (_db().interview_results.find({"user_id": user_id}, {"details": 0})
           .sort("created_at", DESCENDING).limit(limit))
    return [{"id": str(r["_id"]), "stream": r.get("stream"), "score": r["score"], "created_at": r["created_at"]}
            for r in cur]
