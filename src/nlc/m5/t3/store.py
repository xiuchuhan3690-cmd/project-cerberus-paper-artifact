"""Durable single-host CutoverSlot state machine.

The atomic replace is the linearization point.  This is deliberately not a
distributed-consensus implementation or claim.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading
from contextlib import contextmanager

from m1.canonical import canonical_bytes
from nlc.m5.t1.verifier import RootAcceptContext
from nlc.m5.t2.verifier import verify_parentless_root
from .canonical import PROPOSAL_TAG, RECEIPT_TAG, SLOT_TAG, proposal_material, slot_material, tagged_hash
from .model import (
    ActivationResult, CutoverError, CutoverSlot, ENGINE_VERSION, InjectedCrash,
    RECEIPT_VERSION, RootProposal, STORE_VERSION,
)


CRASH_POINTS = (
    "BEFORE_PERSISTENCE", "AFTER_PROPOSAL_PERSISTENCE", "AFTER_PREPARE",
    "AFTER_EVIDENCE_PERSISTENCE", "IMMEDIATELY_BEFORE_COMMIT_WRITE",
    "IMMEDIATELY_AFTER_COMMIT_WRITE", "BEFORE_RECEIPT_GENERATION",
    "AFTER_RECEIPT_GENERATION", "BEFORE_CALLER_ACK", "AFTER_CALLER_ACK",
)
_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.RLock] = {}


def _crash(selected: str | None, point: str) -> None:
    if selected == point:
        raise InjectedCrash(point)


class PersistentCutoverStore:
    def __init__(self, path: Path, slot: CutoverSlot):
        self.path = Path(path)
        self.slot = slot
        lock_key = str(self.path.resolve())
        with _LOCKS_GUARD:
            self._lock = _PATH_LOCKS.setdefault(lock_key, threading.RLock())
        self._lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self._read()

    def _initial(self) -> dict:
        return {
            "ack_issued": False, "candidate_root_id": "",
            "decision_evidence": {}, "history": [], "phase": "EMPTY",
            "proposal": {}, "receipt": {}, "receipt_id": "",
            "slot": self.slot.__dict__, "state": "EMPTY",
            "store_version": STORE_VERSION, "terminal_outcome": "",
        }

    def _read(self) -> dict:
        try:
            raw = self.path.read_bytes()
            value = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise CutoverError("STORE_AMBIGUOUS_HOLD") from None
        if canonical_bytes(value) + b"\n" != raw:
            raise CutoverError("STORE_AMBIGUOUS_HOLD")
        if value.get("store_version") != STORE_VERSION or value.get("slot") != self.slot.__dict__:
            raise CutoverError("STORE_SLOT_MISMATCH_HOLD")
        return value

    def snapshot(self) -> dict:
        with self._lock, self._file_lock():
            return self._read() if self.path.exists() else self._initial()

    def snapshot_bytes(self) -> bytes:
        return canonical_bytes(self.snapshot()) + b"\n"

    def _write(self, value: dict) -> None:
        raw = canonical_bytes(value) + b"\n"
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("wb") as handle:
            handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, self.path)

    @contextmanager
    def _file_lock(self):
        """Crash-released, cross-process one-byte lock for this store path."""
        with self._lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0"); handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                try: yield
                finally:
                    handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try: yield
                finally: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _validate_inputs(self, proposal: RootProposal, construction_receipt: bytes,
                         certificate: bytes, context: RootAcceptContext) -> dict:
        if tagged_hash(PROPOSAL_TAG, proposal_material(proposal)) != proposal.proposal_id:
            raise CutoverError("PROPOSAL_BINDING_MISMATCH")
        if tagged_hash(SLOT_TAG, slot_material(self.slot)) != self.slot.slot_id:
            raise CutoverError("SLOT_ID_MISMATCH")
        if proposal.slot_id != self.slot.slot_id:
            raise CutoverError("PROPOSAL_SLOT_MISMATCH")
        verified = verify_parentless_root(construction_receipt, certificate, context)
        if verified.verdict != "ACCEPT" or verified.root_id != proposal.root_id:
            raise CutoverError("ROOT_NOT_ELIGIBLE")
        receipt_obj = json.loads(construction_receipt)
        if receipt_obj["certificate_id"] != proposal.certificate_id:
            raise CutoverError("CERTIFICATE_ID_MISMATCH")
        import hashlib
        if hashlib.sha256(construction_receipt).hexdigest() != proposal.construction_receipt_id:
            raise CutoverError("CONSTRUCTION_RECEIPT_ID_MISMATCH")
        if (receipt_obj["construction_material"]["target_domain"] != self.slot.target_domain
                or receipt_obj["construction_material"]["target_epoch"] != self.slot.target_epoch):
            raise CutoverError("STALE_OR_WRONG_SLOT")
        return {
            "authority_parent_edge_count": 0,
            "parentless_reason_code": verified.reason_code,
            "root_eligibility_verdict": verified.verdict,
            "t2_receipt_sha256": proposal.construction_receipt_id,
            "verifier_version": verified.verifier_version,
        }

    def activate(self, proposal: RootProposal, construction_receipt: bytes,
                 certificate: bytes, context: RootAcceptContext,
                 crash_at: str | None = None) -> ActivationResult:
        if crash_at is not None and crash_at not in CRASH_POINTS:
            raise ValueError("UNKNOWN_CRASH_POINT")
        with self._lock, self._file_lock():
            try:
                evidence = self._validate_inputs(proposal, construction_receipt, certificate, context)
                current = self._read() if self.path.exists() else self._initial()
            except CutoverError as exc:
                return ActivationResult("REJECT", exc.reason_code, "HOLD" if "HOLD" in exc.reason_code else "EMPTY", "NOT_ACTIVE", None, None)
            if current["state"] == "COMMITTED":
                if current["proposal"]["proposal_id"] == proposal.proposal_id:
                    raw = canonical_bytes(current["receipt"])
                    return ActivationResult("ACCEPT", "ALREADY_COMMITTED", "COMMITTED", "ACTIVE", current["candidate_root_id"], raw)
                return ActivationResult("REJECT", "SLOT_ALREADY_COMMITTED_CONFLICT", "COMMITTED", "NOT_ACTIVE", current["candidate_root_id"], None)
            if current["state"] in ("ABORTED", "HOLD"):
                return ActivationResult("REJECT", "TERMINAL_NON_COMMIT_STATE", current["state"], "NOT_ACTIVE", None, None)
            if current["proposal"] and current["proposal"]["proposal_id"] != proposal.proposal_id:
                return ActivationResult("REJECT", "PREPARED_PROPOSAL_CONFLICT", "PREPARED", "NOT_ACTIVE", None, None)
            _crash(crash_at, "BEFORE_PERSISTENCE")
            if not current["proposal"]:
                current.update(state="PREPARED", phase="PROPOSAL_PERSISTED", proposal=proposal.__dict__, candidate_root_id=proposal.root_id)
                self._write(current)
            _crash(crash_at, "AFTER_PROPOSAL_PERSISTENCE")
            current["phase"] = "PREPARED"; self._write(current)
            _crash(crash_at, "AFTER_PREPARE")
            current["decision_evidence"] = evidence; current["phase"] = "EVIDENCE_PERSISTED"; self._write(current)
            _crash(crash_at, "AFTER_EVIDENCE_PERSISTENCE")
            _crash(crash_at, "BEFORE_RECEIPT_GENERATION")
            receipt_material = {
                "accepted_certificate_id": proposal.certificate_id,
                "activation_result": "ACTIVE",
                "authority_ancestry": [], "authority_parent_edges": [],
                "commit_state": "COMMITTED", "decision_evidence": evidence,
                "engine_version": ENGINE_VERSION, "proposal_id": proposal.proposal_id,
                "receipt_version": RECEIPT_VERSION, "root_id": proposal.root_id,
                "root_construction_receipt_id": proposal.construction_receipt_id,
                "slot_id": self.slot.slot_id,
            }
            receipt = {**receipt_material, "receipt_id": tagged_hash(RECEIPT_TAG, receipt_material)}
            _crash(crash_at, "AFTER_RECEIPT_GENERATION")
            _crash(crash_at, "IMMEDIATELY_BEFORE_COMMIT_WRITE")
            current.update(
                state="COMMITTED", phase="COMMITTED", terminal_outcome="COMMITTED_ACTIVE",
                receipt=receipt, receipt_id=receipt["receipt_id"], ack_issued=False,
            )
            if not any(row.get("event") == "COMMIT" for row in current["history"]):
                current["history"].append({"event": "COMMIT", "proposal_id": proposal.proposal_id, "root_id": proposal.root_id})
            self._write(current)
            _crash(crash_at, "IMMEDIATELY_AFTER_COMMIT_WRITE")
            _crash(crash_at, "BEFORE_CALLER_ACK")
            current["ack_issued"] = True; current["phase"] = "ACK_ISSUED"; self._write(current)
            _crash(crash_at, "AFTER_CALLER_ACK")
            return ActivationResult("ACCEPT", "CUTOVER_COMMITTED", "COMMITTED", "ACTIVE", proposal.root_id, canonical_bytes(receipt))
