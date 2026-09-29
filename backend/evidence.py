import hashlib
import json
import time


def _canonical_json(data):
    return json.dumps(data, sort_keys=True, default=str)


def compute_hash(data):
    return hashlib.sha256(
        _canonical_json(data).encode("utf-8")
    ).hexdigest()


def build_evidence(
    trace_id,
    address,
    raw_records,
    derived_edges,
    precomputed_hash=None,
):
    core = {
        "trace_id": trace_id,
        "address": address,
        "raw_records": raw_records,
        "derived_edges": derived_edges,
    }

    bundle_hash = precomputed_hash or compute_hash(core)

    bundle = dict(core)
    bundle["collected_at"] = int(time.time())
    bundle["sha256"] = bundle_hash

    content = json.dumps(
        bundle,
        indent=2,
        default=str,
    ).encode("utf-8")

    return content, bundle_hash