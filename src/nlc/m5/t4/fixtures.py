"""Causally isolated finite new/old epoch authority fixtures."""

from __future__ import annotations
from copy import deepcopy
import hashlib,json
from pathlib import Path
from .canonical import seal_artifact
from .model import ARTIFACT_VERSION,EpochContext


T3_VECTOR_SHA256="0646c510046d36dc0356d0f8119d7a2f8cddfd287cd0a9324da23286c6492e5e"


def context(root:Path)->EpochContext:
    raw=(root/"vectors/NLC_M5_T3_CutoverSlot_Canonical_Vectors_v1.json").read_bytes()
    if hashlib.sha256(raw).hexdigest()!=T3_VECTOR_SHA256: raise ValueError("FROZEN_T3_VECTOR_MISMATCH")
    vector=json.loads(raw); receipt=vector["receipt"]; slot=vector["slot"]
    return EpochContext(vector["root_a"],slot["slot_id"],receipt["receipt_id"],vector["receipt_sha256"],slot["target_domain"],slot["target_epoch"],"NLC:NS:NEW:D_1:E1","NLC-NAMESPACE/NEW/1.0","NLC:VERIFIER-DOMAIN:NEW:D_1:E1","NLC-NEW-EPOCH-VERIFIER/1.0","NLC:SYNTHETIC-CRYPTO-ROOT:NEW:E1","NLC-NATIVE-AUTHORITY-GRAMMAR/1.0","NLC:NATIVE-AUTHORITY-ADAPTER","1.0")


def valid(ctx:EpochContext)->dict:
    return seal_artifact({"artifact_version":ARTIFACT_VERSION,"authority_claim":"NATIVE_NEW_EPOCH_AUTHORITY","cryptographic_root_id":ctx.cryptographic_root_id,"cutover_receipt_id":ctx.cutover_receipt_id,"cutover_receipt_sha256":ctx.cutover_receipt_sha256,"cutover_slot_id":ctx.cutover_slot_id,"grammar_id":ctx.semantic_grammar_id,"namespace_id":ctx.namespace_id,"namespace_version":ctx.namespace_version,"protocol_adapter_id":ctx.protocol_adapter_id,"protocol_adapter_version":ctx.protocol_adapter_version,"request_format":"NATIVE_CLOSED_AUTHORITY_OBJECT","root_id":ctx.active_root_id,"target_domain":ctx.target_domain,"target_epoch":ctx.target_epoch,"verifier_domain_id":ctx.verifier_domain_id,"verifier_version":ctx.verifier_version})


def mutate(base:dict,**changes)->dict:
    value=deepcopy(base); value.update(changes); return seal_artifact(value)


def corpus(ctx):
    base=valid(ctx)
    return {
        "B1_OLD_NAMESPACE":mutate(base,namespace_id="NLC:NS:OLD:D_0:E0"),
        "B2_OLD_VERIFIER":mutate(base,verifier_domain_id="NLC:VERIFIER-DOMAIN:OLD:D_0:E0"),
        "B3_OLD_CRYPTO_ROOT":mutate(base,cryptographic_root_id="NLC:SYNTHETIC-CRYPTO-ROOT:OLD:E0"),
        "B4_OLD_GRAMMAR":mutate(base,grammar_id="NLC-LEGACY-AUTHORITY-GRAMMAR/0.9"),
        "B5_LEGACY_ADAPTER":mutate(base,protocol_adapter_id="NLC:LEGACY-AUTHORITY-ADAPTER"),
        "B6_VALID_NEW_EPOCH":base,
    }
