"""Tests for backups and CSV export, using temporary folders."""

import csv
import io
import sqlite3
from datetime import date, timedelta

from backup import (
    answers_csv, backup_folder, backup_now, backups, daily_backup, interviews_csv,
)
from progress import connect, record_answer, save_interview

TODAY = date(2026, 10, 21)


def make_db(tmp_path):
    conn = connect(tmp_path / "progress.db")
    record_answer(conn, TODAY, "job-1:technical", {"id": "linux-01", "topic": "linux"}, True)
    record_answer(conn, TODAY, "aptitude:mock", {"id": "m-1", "topic": "numerical"}, False)
    return conn


def test_backup_is_a_working_copy_of_the_database(tmp_path):
    conn = make_db(tmp_path)
    target = backup_now(tmp_path / "progress.db", tmp_path / "backups", TODAY)

    assert target.name == "progress-2026-10-21.db"
    copy = sqlite3.connect(target)
    assert copy.execute("SELECT COUNT(*) FROM answers").fetchone()[0] == 2
    copy.close()
    conn.close()


def test_only_the_newest_backups_are_kept(tmp_path):
    make_db(tmp_path).close()
    for n in range(5):
        backup_now(tmp_path / "progress.db", tmp_path / "backups", TODAY + timedelta(days=n), keep=3)

    names = [p.name for p in backups(tmp_path / "backups")]
    assert names == ["progress-2026-10-25.db", "progress-2026-10-24.db", "progress-2026-10-23.db"]


def test_daily_backup_runs_once_a_day(tmp_path):
    make_db(tmp_path).close()
    folder = tmp_path / "backups"

    assert daily_backup(tmp_path / "progress.db", folder, TODAY) is not None
    assert daily_backup(tmp_path / "progress.db", folder, TODAY) is None
    assert daily_backup(tmp_path / "missing.db", folder, TODAY + timedelta(days=1)) is None


def test_backup_folder_comes_from_env_then_onedrive(monkeypatch, tmp_path):
    monkeypatch.setattr("backup.load_dotenv", lambda: None)  # ignore your real .env
    monkeypatch.setenv("BACKUP_FOLDER", str(tmp_path / "mine"))
    assert backup_folder() == tmp_path / "mine"

    monkeypatch.delenv("BACKUP_FOLDER")
    monkeypatch.setenv("OneDrive", str(tmp_path / "OneDrive"))
    assert backup_folder() == tmp_path / "OneDrive" / "Interview Coach backups"


def test_answers_csv_names_the_job_and_practice_type(tmp_path):
    conn = make_db(tmp_path)
    rows = list(csv.DictReader(io.StringIO(answers_csv(conn, {"job-1": "Acme - Analyst"}))))

    assert rows[0]["job"] == "Acme - Analyst"
    assert rows[0]["practice"] == "technical"
    assert rows[0]["correct"] == "yes"
    assert rows[1]["job"] == "All jobs"
    assert rows[1]["practice"] == "aptitude mock"
    conn.close()


def test_interviews_csv_includes_answers_and_tips(tmp_path):
    conn = make_db(tmp_path)
    feedback = {"checklist": {}, "strength": "Clear.", "tips": ["Add a number.", "Say I."]}
    save_interview(conn, TODAY, "job-1", [{"question": "Q1", "answer": "A1", "score": 6, "feedback": feedback}], 6.0)

    [row] = list(csv.DictReader(io.StringIO(interviews_csv(conn, {"job-1": "Acme - Analyst"}))))
    assert row["your answer"] == "A1"
    assert row["tips"] == "Add a number. | Say I."
    conn.close()
