"""
db.py — local SQLite tracker for OpportunityAI.

Design:
  * stdlib sqlite3 only. No ORM.
  * Parameterised queries only.
  * Short-lived connection per call (safe under Streamlit's rerun model), WAL enabled.
  * Schema version tracked with PRAGMA user_version.

Tables: profile, applications, stage_history, skill_progress, feedback, ai_cache.
Nothing here touches the network. Deleting the file wipes all local data.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

STAGES = ["Discovered", "Shortlisted", "Preparing", "Applied", "Interview",
          "Selected", "Rejected", "Withdrawn", "No response"]

SKILL_STATES = ["Not Started", "Learning", "Practised", "Demonstrated in Project"]

_DB_PATH = os.environ.get("OPPORTUNITYAI_DB", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "opportunityai.db"))


def db_path() -> str:
    return os.environ.get("OPPORTUNITYAI_DB", _DB_PATH)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
    except sqlite3.Error:
        pass
    return conn


def init_db() -> None:
    """Create tables if missing. Safe to call on every app start."""
    try:
        with _connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS applications (
                    opportunity_id TEXT PRIMARY KEY,
                    stage TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stage_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id TEXT NOT NULL,
                    from_stage TEXT,
                    to_stage TEXT NOT NULL,
                    at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS skill_progress (
                    skill TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    evidence_note TEXT DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    opportunity_id TEXT NOT NULL,
                    vote TEXT NOT NULL,
                    at TEXT NOT NULL,
                    PRIMARY KEY (opportunity_id, at)
                );
                CREATE TABLE IF NOT EXISTS ai_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    except sqlite3.Error:
        # Never let a storage problem crash the app.
        pass


def _now() -> str:
    import datetime as _dt
    return _dt.datetime.now().isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Profile
# --------------------------------------------------------------------------- #
def save_profile(profile: Dict[str, Any]) -> None:
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO profile (id, json, updated_at) VALUES (1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET json=excluded.json, updated_at=excluded.updated_at",
                (json.dumps(profile), _now()))
    except sqlite3.Error:
        pass


def load_profile() -> Dict[str, Any]:
    try:
        with _connect() as conn:
            row = conn.execute("SELECT json FROM profile WHERE id=1").fetchone()
        return json.loads(row["json"]) if row else {}
    except (sqlite3.Error, json.JSONDecodeError):
        return {}


# --------------------------------------------------------------------------- #
# Applications + stage history
# --------------------------------------------------------------------------- #
def set_stage(opportunity_id: str, stage: str, notes: str = "") -> None:
    if stage not in STAGES:
        stage = "Discovered"
    try:
        with _connect() as conn:
            row = conn.execute("SELECT stage FROM applications WHERE opportunity_id=?",
                               (opportunity_id,)).fetchone()
            from_stage = row["stage"] if row else None
            conn.execute(
                "INSERT INTO applications (opportunity_id, stage, notes, updated_at) VALUES (?,?,?,?) "
                "ON CONFLICT(opportunity_id) DO UPDATE SET stage=excluded.stage, "
                "notes=excluded.notes, updated_at=excluded.updated_at",
                (opportunity_id, stage, notes, _now()))
            if from_stage != stage:
                conn.execute(
                    "INSERT INTO stage_history (opportunity_id, from_stage, to_stage, at) VALUES (?,?,?,?)",
                    (opportunity_id, from_stage, stage, _now()))
    except sqlite3.Error:
        pass


def get_applications() -> List[Dict[str, Any]]:
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT opportunity_id, stage, notes, updated_at FROM applications "
                "ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def get_stage_history(opportunity_id: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with _connect() as conn:
            if opportunity_id:
                rows = conn.execute(
                    "SELECT * FROM stage_history WHERE opportunity_id=? ORDER BY id",
                    (opportunity_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM stage_history ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def remove_application(opportunity_id: str) -> None:
    try:
        with _connect() as conn:
            conn.execute("DELETE FROM applications WHERE opportunity_id=?", (opportunity_id,))
    except sqlite3.Error:
        pass


# --------------------------------------------------------------------------- #
# Skill progress
# --------------------------------------------------------------------------- #
def set_skill_state(skill: str, state: str, evidence_note: str = "") -> None:
    if state not in SKILL_STATES:
        state = "Not Started"
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO skill_progress (skill, state, evidence_note, updated_at) VALUES (?,?,?,?) "
                "ON CONFLICT(skill) DO UPDATE SET state=excluded.state, "
                "evidence_note=excluded.evidence_note, updated_at=excluded.updated_at",
                (skill, state, evidence_note, _now()))
    except sqlite3.Error:
        pass


def get_skill_states() -> Dict[str, Dict[str, str]]:
    try:
        with _connect() as conn:
            rows = conn.execute("SELECT skill, state, evidence_note FROM skill_progress").fetchall()
        return {r["skill"]: {"state": r["state"], "evidence_note": r["evidence_note"]} for r in rows}
    except sqlite3.Error:
        return {}


# --------------------------------------------------------------------------- #
# Feedback
# --------------------------------------------------------------------------- #
def save_feedback(opportunity_id: str, vote: str) -> None:
    if vote not in ("up", "down"):
        return
    try:
        with _connect() as conn:
            conn.execute("INSERT OR REPLACE INTO feedback (opportunity_id, vote, at) VALUES (?,?,?)",
                         (opportunity_id, vote, _now()))
    except sqlite3.Error:
        pass


def get_feedback() -> Dict[str, str]:
    try:
        with _connect() as conn:
            rows = conn.execute("SELECT opportunity_id, vote FROM feedback").fetchall()
        return {r["opportunity_id"]: r["vote"] for r in rows}
    except sqlite3.Error:
        return {}


# --------------------------------------------------------------------------- #
# AI cache
# --------------------------------------------------------------------------- #
def cache_get(key: str) -> Optional[str]:
    try:
        with _connect() as conn:
            row = conn.execute("SELECT value FROM ai_cache WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None
    except sqlite3.Error:
        return None


def cache_set(key: str, value: str) -> None:
    try:
        with _connect() as conn:
            conn.execute("INSERT OR REPLACE INTO ai_cache (key, value, created_at) VALUES (?,?,?)",
                         (key, value, _now()))
    except sqlite3.Error:
        pass


# --------------------------------------------------------------------------- #
# Wipe
# --------------------------------------------------------------------------- #
def wipe_all() -> None:
    """Delete all locally stored data (profile, tracker, resume-derived cache)."""
    try:
        with _connect() as conn:
            for table in ("profile", "applications", "stage_history",
                          "skill_progress", "feedback", "ai_cache"):
                conn.execute(f"DELETE FROM {table}")
    except sqlite3.Error:
        pass


def counts() -> Dict[str, int]:
    out = {}
    try:
        with _connect() as conn:
            for table in ("applications", "stage_history", "skill_progress", "ai_cache"):
                out[table] = conn.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"]
    except sqlite3.Error:
        pass
    return out
