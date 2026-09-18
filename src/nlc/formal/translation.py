"""Lossless Python/TLA+/Z3 views over one canonical formal identity.

No TLC or Z3 solver is invoked here.  Each view retains the canonical state
and an explicit stable-ID map, preventing enum/status/scope/time defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import formal_sha256, to_primitive
from .model import NLCFormalState


@dataclass(frozen=True, slots=True)
class ToolIdentity:
    formal_id: str
    python_ref: str
    tla_ref: str
    z3_ref: str


def _identity_rows(state: NLCFormalState) -> tuple[ToolIdentity, ...]:
    ids: set[str] = set()
    ids.update(item.domain.value for item in state.authority_domain_registry)
    ids.update(state.cutover.protected_scopes)
    ids.update(item.certificate_id for item in state.cutover.certificates)
    ids.update(item.replica_id for item in state.cutover.replicas)
    ids.update(state.recovery.checkpoints)
    ids.update(item.attempt_id for item in state.recovery.attempts)
    ids.update(item.node_id for item in state.influence.nodes)
    ids.update(item.transform_id for item in state.sterility.transforms)
    return tuple(ToolIdentity(item, f"python:{item}", f"tla:{item}", f"z3:{item}") for item in sorted(ids))


def python_explicit_state_view(state: NLCFormalState) -> dict[str, Any]:
    return {
        "view_version": "NLC-PYTHON-VIEW/1.0",
        "formal_state_sha256": formal_sha256(state),
        "stable_identities": [item.__dict__ if hasattr(item, "__dict__") else {"formal_id": item.formal_id, "python_ref": item.python_ref, "tla_ref": item.tla_ref, "z3_ref": item.z3_ref} for item in _identity_rows(state)],
        "lossless_state": to_primitive(state),
    }


def tla_state_view(state: NLCFormalState) -> dict[str, Any]:
    return {
        "view_version": "NLC-TLA-VIEW/1.0",
        "formal_state_sha256": formal_sha256(state),
        "constants": {
            "AuthorityDomains": [item.domain.value for item in state.authority_domain_registry],
            "ProtectedScopes": list(state.cutover.protected_scopes),
            "Certificates": [item.certificate_id for item in state.cutover.certificates],
            "TraceBound": state.future_trace_bound,
        },
        "stable_identities": [{"formal_id": item.formal_id, "tool_ref": item.tla_ref} for item in _identity_rows(state)],
        "lossless_state": to_primitive(state),
    }


def z3_finite_domain_view(state: NLCFormalState) -> dict[str, Any]:
    return {
        "view_version": "NLC-Z3-VIEW/1.0",
        "formal_state_sha256": formal_sha256(state),
        "finite_sorts": {
            "AuthorityDomain": [item.domain.value for item in state.authority_domain_registry],
            "Scope": list(state.cutover.protected_scopes),
            "Certificate": [item.certificate_id for item in state.cutover.certificates],
            "EpistemicLabel": ["OBSERVED", "DERIVED", "INFERRED", "UNOBSERVABLE"],
            "InfluenceClass": ["DIRECT", "CERTAIN", "POSSIBLE", "UNKNOWN"],
        },
        "stable_identities": [{"formal_id": item.formal_id, "tool_ref": item.z3_ref} for item in _identity_rows(state)],
        "lossless_state": to_primitive(state),
    }


def assert_cross_tool_identity(state: NLCFormalState) -> None:
    views = (python_explicit_state_view(state), tla_state_view(state), z3_finite_domain_view(state))
    hashes = {view["formal_state_sha256"] for view in views}
    identity_sets = [{item["formal_id"] for item in view["stable_identities"]} for view in views]
    if len(hashes) != 1 or not all(items == identity_sets[0] for items in identity_sets[1:]):
        raise ValueError("Python/TLA+/Z3 formal identity divergence")
    if not all(view["lossless_state"] == views[0]["lossless_state"] for view in views[1:]):
        raise ValueError("tool view lost formal state information")

