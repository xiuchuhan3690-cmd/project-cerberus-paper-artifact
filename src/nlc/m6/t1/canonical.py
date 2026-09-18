"""Strict canonical JSON helpers."""

from __future__ import annotations
import hashlib,json,unicodedata

class CanonicalError(ValueError): pass
def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise CanonicalError("DUPLICATE_FIELD")
        result[key]=value
    return result
def _norm(value):
    if value is None or isinstance(value,float): raise CanonicalError("MALFORMED_VALUE")
    if isinstance(value,(bool,int)): return value
    if isinstance(value,str): return unicodedata.normalize("NFC",value)
    if isinstance(value,list): return [_norm(item) for item in value]
    if isinstance(value,dict): return {unicodedata.normalize("NFC",key):_norm(item) for key,item in value.items()}
    raise CanonicalError("MALFORMED_VALUE")
def encode(value)->bytes:
    return json.dumps(_norm(value),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
def decode(raw:bytes):
    try: value=json.loads(raw.decode("utf-8"),object_pairs_hook=_pairs)
    except (UnicodeError,json.JSONDecodeError) as exc: raise CanonicalError("MALFORMED_JSON") from exc
    if encode(value)!=raw: raise CanonicalError("NON_CANONICAL_JSON")
    return value
def digest(domain:bytes,value)->str: return hashlib.sha256(domain+encode(value)).hexdigest()
