"""Two independently valid parentless-root candidates for one T3 slot."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

from m1.canonical import canonical_bytes
from nlc.m5.t1.builder import build_certificate
from nlc.m5.t1.fixtures import baseline
from nlc.m5.t2.constructor import construct_root, issue_vote
from nlc.m5.t2.model import SYNTHETIC_CREDENTIALS
from .canonical import PARENT_TAG, make_proposal, make_slot, tagged_hash
from .model import FENCE_IDENTITY


def candidates(root: Path):
    cert_a, context = baseline(root)
    cert_b = replace(cert_a, nonce="nonce:m5t3-competing-root-0002")
    values = []
    for label, cert in (("RootA", cert_a), ("RootB", cert_b)):
        raw = build_certificate(cert)
        votes = [issue_vote(name, SYNTHETIC_CREDENTIALS[name], raw, context) for name in SYNTHETIC_CREDENTIALS]
        result = construct_root(raw, context, votes)
        values.append({"label": label, "certificate": raw, "construction_receipt": result.receipt_bytes, "root_id": result.root_id})
    parent = {
        "m5_t1_head": "170a902dead907c2998b87d833ed7e5f0875ba6c",
        "m5_t2_freeze_sha256": "83eae112f6fac7cd02602e3aa32bc6dd70148ec31575b846b0e1c4523c675c30",
        "m5_t2_head": "598570a67482c6b4173aa2b604c904b4775c5f6c",
        "m5_t2_tree": "0ade1a878f784085715b9d76bf314ab4da61f07f",
    }
    slot = make_slot("D_1", 1, 1, "NLC:SYNTHETIC:PRIMARY", FENCE_IDENTITY, tagged_hash(PARENT_TAG, parent))
    for item in values:
        t2 = json.loads(item["construction_receipt"])
        item["proposal"] = make_proposal(item["root_id"], t2["certificate_id"], hashlib.sha256(item["construction_receipt"]).hexdigest(), slot.slot_id, "Cerberus_T3_Cutover", "1.0")
    return slot, values[0], values[1], context
