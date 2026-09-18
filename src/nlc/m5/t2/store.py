"""File-backed idempotent persistence for synthetic constructor votes.

This is not a CutoverSlot, active-root registry, or competing-certificate
arbiter.  It records one immutable vote per (constructor, proposal) pair only.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading

from m1.canonical import canonical_bytes
from .constructor import ConstructionError, validate_vote_record, vote_bytes, vote_dict
from .model import ConstructorVote, VOTE_VERSION


STORE_VERSION = "NLC-M5-T2-VOTE-STORE/1.0"


class PersistentVoteStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._votes: dict[str, ConstructorVote] = {}
        if self.path.exists():
            self._load()

    @staticmethod
    def _key(vote: ConstructorVote) -> str:
        return f"{vote.constructor_id}|{vote.proposal_id}"

    def _load(self) -> None:
        try:
            raw = self.path.read_bytes()
            value = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise ConstructionError("VOTE_STORE_CORRUPTED") from None
        if value.get("store_version") != STORE_VERSION or set(value) != {"store_version", "votes"}:
            raise ConstructionError("VOTE_STORE_CORRUPTED")
        if canonical_bytes(value) + b"\n" != raw:
            raise ConstructionError("VOTE_STORE_NONCANONICAL")
        for key, item in value["votes"].items():
            if not isinstance(item, dict) or set(item) != {
                "certificate_id", "constructor_id", "constructor_set_commitment", "nonce",
                "proposal_id", "root_accept_predicate_version", "synthetic_proof",
                "target_domain", "target_epoch", "vote_version",
            }:
                raise ConstructionError("VOTE_STORE_CORRUPTED")
            vote = ConstructorVote(
                item["vote_version"], item["constructor_id"], item["proposal_id"],
                item["certificate_id"], item["target_domain"], item["target_epoch"],
                item["nonce"], item["constructor_set_commitment"],
                item["root_accept_predicate_version"], item["synthetic_proof"],
            )
            if vote.vote_version != VOTE_VERSION or self._key(vote) != key:
                raise ConstructionError("VOTE_STORE_CORRUPTED")
            validate_vote_record(vote)
            self._votes[key] = vote

    def _persist(self) -> None:
        value = {
            "store_version": STORE_VERSION,
            "votes": {key: vote_dict(vote) for key, vote in sorted(self._votes.items())},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".next")
        with temporary.open("wb") as handle:
            handle.write(canonical_bytes(value) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)

    def record(self, vote: ConstructorVote) -> ConstructorVote:
        with self._lock:
            validate_vote_record(vote)
            key = self._key(vote)
            existing = self._votes.get(key)
            if existing is not None:
                if vote_bytes(existing) != vote_bytes(vote):
                    raise ConstructionError("CONFLICTING_PERSISTENT_VOTE")
                return existing
            self._votes[key] = vote
            self._persist()
            return vote

    def votes_for(self, proposal_id: str) -> tuple[ConstructorVote, ...]:
        with self._lock:
            return tuple(sorted(
                (vote for vote in self._votes.values() if vote.proposal_id == proposal_id),
                key=lambda vote: vote.constructor_id,
            ))

    def snapshot_bytes(self) -> bytes:
        with self._lock:
            value = {
                "store_version": STORE_VERSION,
                "votes": {key: vote_dict(vote) for key, vote in sorted(self._votes.items())},
            }
            return canonical_bytes(value) + b"\n"
