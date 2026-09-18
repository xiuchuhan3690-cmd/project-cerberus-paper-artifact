"""Independent closed semantic-grammar barrier; no compatibility bridge."""
from .canonical import decision


def verify(artifact,context):
    if artifact.get("grammar_id")!=context.semantic_grammar_id: return decision("SEMANTIC_GRAMMAR",artifact,context,"REJECT","OLD_OR_UNSUPPORTED_GRAMMAR")
    if artifact.get("request_format")!="NATIVE_CLOSED_AUTHORITY_OBJECT": return decision("SEMANTIC_GRAMMAR",artifact,context,"REJECT","PARSER_BRIDGE_OR_OPAQUE_FORMAT_PROHIBITED")
    return decision("SEMANTIC_GRAMMAR",artifact,context,"PASS","NATIVE_CLOSED_GRAMMAR_BOUND")
