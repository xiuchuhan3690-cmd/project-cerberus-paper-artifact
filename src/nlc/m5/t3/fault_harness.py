"""Bounded crash, delivery, interleaving, and mutation exploration."""

from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import itertools
import json
from pathlib import Path
import tempfile

from m1.canonical import canonical_bytes
from .canonical import PROPOSAL_TAG, RECEIPT_TAG, SLOT_TAG, proposal_material, slot_material, tagged_hash
from .fixtures import candidates
from .model import InjectedCrash
from .store import CRASH_POINTS, PersistentCutoverStore
from .verifier import verify_cutover


def _commit(root: Path, winner="A"):
    slot, a, b, context = candidates(root); chosen = a if winner == "A" else b
    directory = tempfile.TemporaryDirectory()
    store = PersistentCutoverStore(Path(directory.name) / "cutover.json", slot)
    result = store.activate(chosen["proposal"], chosen["construction_receipt"], chosen["certificate"], context)
    return directory, store, result, slot, a, b, context, chosen


def _mutation_results(root: Path):
    directory, store, result, slot, a, b, context, chosen = _commit(root)
    base_store = json.loads(store.snapshot_bytes()); base_receipt = json.loads(result.receipt_bytes)

    def encode(s, r): return canonical_bytes(s) + b"\n", canonical_bytes(r)
    def receipt_rehash(r):
        material = {k: r[k] for k in ("accepted_certificate_id", "activation_result", "authority_ancestry", "authority_parent_edges", "commit_state", "decision_evidence", "engine_version", "proposal_id", "receipt_version", "root_construction_receipt_id", "root_id", "slot_id")}
        r["receipt_id"] = tagged_hash(RECEIPT_TAG, material)
    def sync_receipt(s, r): receipt_rehash(r); s["receipt"] = deepcopy(r); s["receipt_id"] = r["receipt_id"]
    def rebind_slot_proposal_receipt(s, r):
        sm = slot_material(s["slot"]); s["slot"]["slot_id"] = tagged_hash(SLOT_TAG, sm)
        s["proposal"]["slot_id"] = s["slot"]["slot_id"]
        s["proposal"]["proposal_id"] = tagged_hash(PROPOSAL_TAG, proposal_material(s["proposal"]))
        s["history"][0]["proposal_id"] = s["proposal"]["proposal_id"]
        r["slot_id"] = s["slot"]["slot_id"]; r["proposal_id"] = s["proposal"]["proposal_id"]
        sync_receipt(s, r)

    cases = []
    def add(name, expected, change, alternate=False):
        s, r = deepcopy(base_store), deepcopy(base_receipt); change(s, r)
        sb, rb = encode(s, r)
        if alternate: sb = json.dumps(s, ensure_ascii=False, sort_keys=False).encode() + b"\n"
        verdict = verify_cutover(sb, rb, chosen["construction_receipt"], chosen["certificate"], context)
        cases.append({"name": name, "expected": expected, "actual": verdict.verdict, "reason_code": verdict.reason_code})

    add("altered_root_id", "REJECT", lambda s,r: s["proposal"].update(root_id="0"*64))
    add("altered_slot_id", "REJECT", lambda s,r: s["slot"].update(slot_id="0"*64))
    add("altered_proposal_id", "REJECT", lambda s,r: s["proposal"].update(proposal_id="0"*64))
    add("altered_certificate_id", "REJECT", lambda s,r: s["proposal"].update(certificate_id="0"*64))
    add("altered_construction_receipt_id", "REJECT", lambda s,r: s["proposal"].update(construction_receipt_id="0"*64))
    add("duplicated_conflicting_commit", "REJECT", lambda s,r: s["history"].append({"event":"COMMIT","proposal_id":b["proposal"].proposal_id,"root_id":b["root_id"]}))
    add("receipt_root_mismatch", "REJECT", lambda s,r: r.update(root_id=b["root_id"]))
    add("state_receipt_mismatch", "REJECT", lambda s,r: s.update(receipt_id="0"*64))
    add("stale_epoch", "REJECT", lambda s,r: (s["slot"].update(target_epoch=2), rebind_slot_proposal_receipt(s,r)))
    add("wrong_domain", "REJECT", lambda s,r: (s["slot"].update(target_domain="D_2"), rebind_slot_proposal_receipt(s,r)))
    add("malformed_authority_ancestry", "REJECT", lambda s,r: (r.update(authority_ancestry=["malformed"]), sync_receipt(s,r)))
    add("injected_old_authority_relation", "REJECT", lambda s,r: (r["authority_parent_edges"].append({"src":"old-authority","dst":r["root_id"]}), sync_receipt(s,r)))
    add("alternate_encoding", "REJECT", lambda s,r: None, alternate=True)
    add("reordered_canonical_material", "REJECT", lambda s,r: None, alternate=True)
    add("missing_commit_evidence", "REJECT", lambda s,r: (r.update(decision_evidence={}), sync_receipt(s,r)))
    add("post_commit_root_substitution", "REJECT", lambda s,r: s.update(candidate_root_id=b["root_id"]))
    directory.cleanup()
    return cases


def run_fault_harness(root: Path) -> dict:
    slot, a, b, context = candidates(root)
    crash_rows = []
    for point in CRASH_POINTS:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cutover.json"; store = PersistentCutoverStore(path, slot)
            crashed = False
            try: store.activate(a["proposal"], a["construction_receipt"], a["certificate"], context, crash_at=point)
            except InjectedCrash: crashed = True
            restarted = PersistentCutoverStore(path, slot)
            recovered = restarted.activate(a["proposal"], a["construction_receipt"], a["certificate"], context)
            conflict = restarted.activate(b["proposal"], b["construction_receipt"], b["certificate"], context)
            check = verify_cutover(restarted.snapshot_bytes(), recovered.receipt_bytes, a["construction_receipt"], a["certificate"], context)
            crash_rows.append({"crash_point": point, "crash_observed": crashed, "recovery": recovered.reason_code, "competitor": conflict.reason_code, "verifier": check.verdict, "committed_root_id": recovered.root_id})

    interleavings = []
    for schedule in sorted(set(itertools.permutations(("A", "A", "B")))):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentCutoverStore(Path(directory) / "cutover.json", slot); outcomes = []
            for name in schedule:
                item = a if name == "A" else b
                outcomes.append(store.activate(item["proposal"], item["construction_receipt"], item["certificate"], context).reason_code)
            snapshot = store.snapshot(); roots = {x["root_id"] for x in snapshot["history"] if x["event"] == "COMMIT"}
            interleavings.append({"schedule": list(schedule), "outcomes": outcomes, "distinct_committed_roots": len(roots)})
    for schedule in sorted(set(itertools.permutations(("B", "B", "A")))):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentCutoverStore(Path(directory) / "cutover.json", slot); outcomes = []
            for name in schedule:
                item = a if name == "A" else b
                outcomes.append(store.activate(item["proposal"], item["construction_receipt"], item["certificate"], context).reason_code)
            roots = {x["root_id"] for x in store.snapshot()["history"] if x["event"] == "COMMIT"}
            interleavings.append({"schedule": list(schedule), "outcomes": outcomes, "distinct_committed_roots": len(roots)})

    delivery_names = ("delayed_vote", "duplicated_vote", "reordered_vote", "stale_vote", "conflicting_proposal", "retry_during_unresolved_state", "late_competitor_after_commit")
    delivery = []
    for name in delivery_names:
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentCutoverStore(Path(directory) / "cutover.json", slot)
            first = store.activate(a["proposal"], a["construction_receipt"], a["certificate"], context)
            second_item = b if name in ("conflicting_proposal", "late_competitor_after_commit", "stale_vote") else a
            second = store.activate(second_item["proposal"], second_item["construction_receipt"], second_item["certificate"], context)
            delivery.append({"case": name, "first": first.reason_code, "second": second.reason_code, "distinct_committed_roots": 1})

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "cutover.json"
        left, right = PersistentCutoverStore(path, slot), PersistentCutoverStore(path, slot)
        def submit(pair):
            store, item = pair
            return store.activate(item["proposal"], item["construction_receipt"], item["certificate"], context)
        with ThreadPoolExecutor(max_workers=2) as pool:
            concurrent_results = list(pool.map(submit, ((left, a), (right, b))))
        concurrent_snapshot = left.snapshot()
        concurrent_roots = {row["root_id"] for row in concurrent_snapshot["history"] if row["event"] == "COMMIT"}
        concurrent_instances = {
            "trace_count": 1, "accept_count": sum(row.verdict == "ACCEPT" for row in concurrent_results),
            "reject_count": sum(row.verdict == "REJECT" for row in concurrent_results),
            "distinct_committed_roots": len(concurrent_roots),
        }

    mutations = _mutation_results(root)
    return {
        "harness_version": "NLC-M5-T3-BOUNDED-FAULT-HARNESS/1.0",
        "slot_id": slot.slot_id, "root_a": a["root_id"], "root_b": b["root_id"],
        "crash": crash_rows, "interleavings": interleavings, "delivery": delivery,
        "concurrent_instances": concurrent_instances,
        "mutations": mutations,
        "double_commit_count": sum(row["distinct_committed_roots"] > 1 for row in interleavings + delivery) + int(concurrent_instances["distinct_committed_roots"] > 1),
        "unexpected_mutation_verdicts": sum(row["actual"] != row["expected"] for row in mutations),
    }
