"""Append-oriented M1 issuance ledger prototype.

SQLite provides transactions and constraints; it is not treated as tamper
evidence. Tamper detection is provided by exported canonical records, a hash
chain, a checkpoint, and the independent verifier.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, sha256_hex
from .model import record_id, validate_record

ZERO_DIGEST = "0" * 64


class LedgerError(ValueError):
    pass


class DuplicateRecordError(LedgerError):
    pass


class ReplayError(LedgerError):
    pass


class ParentReferenceError(LedgerError):
    pass


class CrossRunReferenceError(LedgerError):
    pass


def _chain_digest(sequence: int, record: dict[str, Any], record_digest: str, previous: str) -> str:
    material = {
        "sequence": sequence,
        "record": record,
        "record_digest": record_digest,
        "previous_chain_digest": previous,
    }
    return sha256_hex(canonical_bytes(material))


class IssuanceLedger:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS entries (
                sequence INTEGER PRIMARY KEY,
                record_id TEXT NOT NULL UNIQUE,
                run_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                canonical_json TEXT NOT NULL,
                record_digest TEXT NOT NULL,
                previous_chain_digest TEXT NOT NULL,
                chain_digest TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(run_id)
            );
            CREATE TABLE IF NOT EXISTS generations (
                generation_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(session_id),
                run_id TEXT NOT NULL REFERENCES runs(run_id)
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id TEXT PRIMARY KEY,
                generation_id TEXT NOT NULL REFERENCES generations(generation_id),
                run_id TEXT NOT NULL REFERENCES runs(run_id)
            );
            CREATE TABLE IF NOT EXISTS issuances (
                issuance_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(session_id),
                generation_id TEXT NOT NULL REFERENCES generations(generation_id),
                artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                UNIQUE (run_id, session_id, generation_id, artifact_id)
            );
            """
        )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "IssuanceLedger":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def _exists(self, table: str, key: str, value: str) -> sqlite3.Row | None:
        allowed = {
            "runs": "run_id",
            "sessions": "session_id",
            "generations": "generation_id",
            "artifacts": "artifact_id",
        }
        if table not in allowed or key != allowed[table]:
            raise LedgerError("internal table lookup rejected")
        return self.connection.execute(f"SELECT * FROM {table} WHERE {key} = ?", (value,)).fetchone()

    def _require_run(self, run_id: str) -> None:
        if self._exists("runs", "run_id", run_id) is None:
            raise ParentReferenceError("run parent does not exist")

    def _insert_domain(self, record: dict[str, Any]) -> None:
        entity_type = record["entity_type"]
        if entity_type == "EXPERIMENT_RUN":
            self.connection.execute("INSERT INTO runs(run_id) VALUES (?)", (record["run_id"],))
            return
        self._require_run(record["run_id"])
        if entity_type == "SESSION":
            self.connection.execute("INSERT INTO sessions(session_id, run_id) VALUES (?, ?)", (record["session_id"], record["run_id"]))
        elif entity_type == "GENERATION":
            session = self._exists("sessions", "session_id", record["session_id"])
            if session is None:
                raise ParentReferenceError("session parent does not exist")
            if session["run_id"] != record["run_id"]:
                raise CrossRunReferenceError("generation and session use different runs")
            self.connection.execute(
                "INSERT INTO generations(generation_id, session_id, run_id) VALUES (?, ?, ?)",
                (record["generation_id"], record["session_id"], record["run_id"]),
            )
        elif entity_type == "ARTIFACT":
            generation = self._exists("generations", "generation_id", record["generation_id"])
            if generation is None:
                raise ParentReferenceError("generation parent does not exist")
            if generation["run_id"] != record["run_id"]:
                raise CrossRunReferenceError("artifact and generation use different runs")
            self.connection.execute(
                "INSERT INTO artifacts(artifact_id, generation_id, run_id) VALUES (?, ?, ?)",
                (record["artifact_id"], record["generation_id"], record["run_id"]),
            )
        elif entity_type == "ISSUANCE":
            session = self._exists("sessions", "session_id", record["session_id"])
            generation = self._exists("generations", "generation_id", record["generation_id"])
            artifact = self._exists("artifacts", "artifact_id", record["artifact_id"])
            if session is None or generation is None or artifact is None:
                raise ParentReferenceError("issuance parent does not exist")
            contexts = {session["run_id"], generation["run_id"], artifact["run_id"], record["run_id"]}
            if len(contexts) != 1:
                raise CrossRunReferenceError("issuance parent crosses run context")
            if generation["session_id"] != record["session_id"]:
                raise ParentReferenceError("issuance generation is not bound to the session")
            if artifact["generation_id"] != record["generation_id"]:
                raise ParentReferenceError("issuance artifact is not bound to the generation")
            replay = self.connection.execute(
                "SELECT issuance_id FROM issuances WHERE run_id=? AND session_id=? AND generation_id=? AND artifact_id=?",
                (record["run_id"], record["session_id"], record["generation_id"], record["artifact_id"]),
            ).fetchone()
            if replay is not None:
                raise ReplayError("issuance binding was already recorded")
            self.connection.execute(
                "INSERT INTO issuances(issuance_id, session_id, generation_id, artifact_id, run_id) VALUES (?, ?, ?, ?, ?)",
                (record["issuance_id"], record["session_id"], record["generation_id"], record["artifact_id"], record["run_id"]),
            )
        elif entity_type == "EVENT":
            return
        elif entity_type == "DERIVATION":
            for supporting_id in record["supporting_record_ids"]:
                row = self.connection.execute(
                    "SELECT run_id FROM entries WHERE record_id=?", (supporting_id,)
                ).fetchone()
                if row is None:
                    raise ParentReferenceError("derivation support record does not exist")
                if row["run_id"] != record["run_id"]:
                    raise CrossRunReferenceError("derivation support crosses run context")
        else:
            raise LedgerError("unsupported entity type")

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        validate_record(record)
        identity = record_id(record)
        with self.connection:
            if self.connection.execute("SELECT 1 FROM entries WHERE record_id=?", (identity,)).fetchone():
                raise DuplicateRecordError("record id already exists")
            self._insert_domain(record)
            latest = self.connection.execute(
                "SELECT sequence, chain_digest FROM entries ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            sequence = 1 if latest is None else latest["sequence"] + 1
            previous = ZERO_DIGEST if latest is None else latest["chain_digest"]
            record_digest = sha256_hex(canonical_bytes(record))
            chain_digest = _chain_digest(sequence, record, record_digest, previous)
            self.connection.execute(
                "INSERT INTO entries(sequence, record_id, run_id, entity_type, canonical_json, record_digest, previous_chain_digest, chain_digest) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    sequence,
                    identity,
                    record["run_id"],
                    record["entity_type"],
                    canonical_bytes(record).decode("utf-8"),
                    record_digest,
                    previous,
                    chain_digest,
                ),
            )
        return {
            "sequence": sequence,
            "record": record,
            "record_digest": record_digest,
            "previous_chain_digest": previous,
            "chain_digest": chain_digest,
        }

    def export_envelopes(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT * FROM entries ORDER BY sequence").fetchall()
        return [
            {
                "sequence": row["sequence"],
                "record": json.loads(row["canonical_json"]),
                "record_digest": row["record_digest"],
                "previous_chain_digest": row["previous_chain_digest"],
                "chain_digest": row["chain_digest"],
            }
            for row in rows
        ]

    def export_lines(self) -> list[str]:
        return [canonical_bytes(envelope).decode("utf-8") for envelope in self.export_envelopes()]

    def checkpoint(self) -> dict[str, Any]:
        latest = self.connection.execute(
            "SELECT sequence, chain_digest FROM entries ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        run_ids = [row["run_id"] for row in self.connection.execute("SELECT run_id FROM runs ORDER BY run_id")]
        return {
            "schema_version": "0.1",
            "synthetic_test_marker": "CERBERUS_SYNTHETIC_TEST",
            "entry_count": 0 if latest is None else latest["sequence"],
            "root_chain_digest": ZERO_DIGEST if latest is None else latest["chain_digest"],
            "run_ids": run_ids,
        }
