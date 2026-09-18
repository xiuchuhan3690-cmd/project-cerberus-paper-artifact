"""Independent finite protocol/adapter inventory barrier."""
from .canonical import decision


def verify(artifact,context):
    if artifact.get("protocol_adapter_id")!=context.protocol_adapter_id: return decision("PROTOCOL_ADAPTER",artifact,context,"REJECT","LEGACY_OR_UNKNOWN_ADAPTER")
    if artifact.get("protocol_adapter_version")!=context.protocol_adapter_version: return decision("PROTOCOL_ADAPTER",artifact,context,"REJECT","ADAPTER_VERSION_MISMATCH")
    return decision("PROTOCOL_ADAPTER",artifact,context,"PASS","NATIVE_ADAPTER_BOUND")
