"""Independent read-only verifier for exported Cerberus M1 ledger evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, sha256_hex
from .model import ProvenanceValidationError, record_id, validate_record

ZERO_DIGEST = "0" * 64
ENVELOPE_FIELDS = {"sequence", "record", "record_digest", "previous_chain_digest", "chain_digest"}


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _chain_digest(sequence: int, record: dict[str, Any], record_digest: str, previous: str) -> str:
    material = {
        "sequence": sequence,
        "record": record,
        "record_digest": record_digest,
        "previous_chain_digest": previous,
    }
    return sha256_hex(canonical_bytes(material))


def verify_lines(lines: list[str], checkpoint: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    previous = ZERO_DIGEST
    computed_root = ZERO_DIGEST
    seen: dict[str, str] = {}
    runs: set[str] = set()
    sessions: dict[str, str] = {}
    generations: dict[str, tuple[str, str]] = {}
    artifacts: dict[str, tuple[str, str]] = {}
    issuance_bindings: set[tuple[str, str, str, str]] = set()

    def error(code: str, sequence: int | None, detail: str) -> None:
        errors.append({"code": code, "sequence": sequence, "detail": detail})

    for position, raw_line in enumerate(lines, start=1):
        try:
            envelope = json.loads(raw_line, object_pairs_hook=_strict_object)
        except (json.JSONDecodeError, ValueError) as exc:
            error("MALFORMED_JSON", position, str(exc))
            continue
        if not isinstance(envelope, dict) or set(envelope) != ENVELOPE_FIELDS:
            error("MALFORMED_ENVELOPE", position, "envelope fields are not exact")
            continue
        try:
            canonical_line = canonical_bytes(envelope).decode("utf-8")
        except Exception as exc:
            error("NON_CANONICAL", position, str(exc))
            continue
        if raw_line != canonical_line:
            error("NON_CANONICAL", position, "serialized line differs from canonical bytes")
        sequence = envelope.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence != position:
            error("SEQUENCE_MISMATCH", position, f"expected {position}, got {sequence}")
        record = envelope.get("record")
        try:
            validate_record(record)
            identity = record_id(record)
        except ProvenanceValidationError as exc:
            error("INVALID_RECORD", position, str(exc))
            continue
        if identity in seen:
            error("DUPLICATE_ID", position, identity)
        claimed_record_digest = envelope.get("record_digest")
        actual_record_digest = sha256_hex(canonical_bytes(record))
        if claimed_record_digest != actual_record_digest:
            error("RECORD_DIGEST_MISMATCH", position, "record digest differs")
        claimed_previous = envelope.get("previous_chain_digest")
        if claimed_previous != previous:
            error("CHAIN_PREVIOUS_MISMATCH", position, "previous chain digest differs")
        try:
            actual_chain = _chain_digest(position, record, actual_record_digest, previous)
        except Exception as exc:
            error("CHAIN_COMPUTATION_FAILED", position, str(exc))
            continue
        if envelope.get("chain_digest") != actual_chain:
            error("CHAIN_DIGEST_MISMATCH", position, "chain digest differs")
        computed_root = actual_chain
        previous = actual_chain

        run_id = record["run_id"]
        entity_type = record["entity_type"]
        if entity_type == "EXPERIMENT_RUN":
            runs.add(run_id)
        elif run_id not in runs:
            error("MISSING_OR_LATE_RUN", position, run_id)
        if entity_type == "SESSION":
            sessions[record["session_id"]] = run_id
        elif entity_type == "GENERATION":
            session_run = sessions.get(record["session_id"])
            if session_run is None:
                error("MISSING_OR_LATE_SESSION", position, record["session_id"])
            elif session_run != run_id:
                error("CROSS_RUN_REFERENCE", position, record["session_id"])
            generations[record["generation_id"]] = (run_id, record["session_id"])
        elif entity_type == "ARTIFACT":
            generation = generations.get(record["generation_id"])
            if generation is None:
                error("MISSING_OR_LATE_GENERATION", position, record["generation_id"])
            elif generation[0] != run_id:
                error("CROSS_RUN_REFERENCE", position, record["generation_id"])
            artifacts[record["artifact_id"]] = (run_id, record["generation_id"])
        elif entity_type == "ISSUANCE":
            session_run = sessions.get(record["session_id"])
            generation = generations.get(record["generation_id"])
            artifact = artifacts.get(record["artifact_id"])
            if session_run is None or generation is None or artifact is None:
                error("MISSING_ISSUANCE_PARENT", position, "one or more issuance parents are absent or late")
            else:
                if {run_id, session_run, generation[0], artifact[0]} != {run_id}:
                    error("CROSS_RUN_REFERENCE", position, "issuance contexts differ")
                if generation[1] != record["session_id"] or artifact[1] != record["generation_id"]:
                    error("AMBIGUOUS_BINDING", position, "issuance parents do not form one chain")
            binding = (run_id, record["session_id"], record["generation_id"], record["artifact_id"])
            if binding in issuance_bindings:
                error("REPLAYED_ISSUANCE", position, "issuance binding already appeared")
            issuance_bindings.add(binding)
        elif entity_type == "DERIVATION":
            for support in record["supporting_record_ids"]:
                if support not in seen:
                    error("MISSING_OR_LATE_SUPPORT", position, support)
                elif seen[support] != run_id:
                    error("CROSS_RUN_REFERENCE", position, support)
        seen[identity] = run_id

    expected_checkpoint_fields = {
        "schema_version", "synthetic_test_marker", "entry_count", "root_chain_digest", "run_ids"
    }
    if not isinstance(checkpoint, dict) or set(checkpoint) != expected_checkpoint_fields:
        error("INVALID_CHECKPOINT", None, "checkpoint fields are not exact")
    else:
        if checkpoint.get("schema_version") != "0.1" or checkpoint.get("synthetic_test_marker") != "CERBERUS_SYNTHETIC_TEST":
            error("INVALID_CHECKPOINT", None, "checkpoint identity is invalid")
        if checkpoint.get("entry_count") != len(lines):
            error("CHECKPOINT_COUNT_MISMATCH", None, "entry count differs")
        if checkpoint.get("root_chain_digest") != computed_root:
            error("CHECKPOINT_ROOT_MISMATCH", None, "root chain digest differs")
        if checkpoint.get("run_ids") != sorted(runs):
            error("CHECKPOINT_RUN_SET_MISMATCH", None, "run ids differ")
    return {
        "schema_version": "0.1",
        "synthetic_test_marker": "CERBERUS_SYNTHETIC_TEST",
        "valid": not errors,
        "entry_count": len(lines),
        "computed_root_chain_digest": computed_root,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 2:
        print("usage: python -m m1.verifier LEDGER.jsonl CHECKPOINT.json", file=sys.stderr)
        return 2
    ledger_path, checkpoint_path = map(Path, arguments)
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    result = verify_lines(lines, checkpoint)
    print(canonical_bytes(result).decode("utf-8"))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
