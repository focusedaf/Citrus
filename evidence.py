import hashlib
import json
import os
import time
from config import EVIDENCE_DIR


def _canonical_json(data):
    return json.dumps(data, sort_keys=True, default=str)


def compute_hash(data):
   
    return hashlib.sha256(_canonical_json(data).encode("utf-8")).hexdigest()


def save_evidence(trace_id, address, raw_records, derived_edges, precomputed_hash=None):
    
    os.makedirs(EVIDENCE_DIR, exist_ok=True)

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

    path = os.path.join(EVIDENCE_DIR, f"evidence_{trace_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, default=str)

    return path, bundle_hash


def verify_evidence(trace_id):
  
    path = os.path.join(EVIDENCE_DIR, f"evidence_{trace_id}.json")
    if not os.path.exists(path):
        return {"exists": False}

    with open(path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    stored_hash = bundle.get("sha256")
    core = {
        "trace_id": bundle.get("trace_id"),
        "address": bundle.get("address"),
        "raw_records": bundle.get("raw_records"),
        "derived_edges": bundle.get("derived_edges"),
    }
    recomputed = compute_hash(core)

    return {
        "exists": True,
        "path": path,
        "stored_hash": stored_hash,
        "recomputed_hash": recomputed,
        "intact": stored_hash == recomputed,
        "collected_at": bundle.get("collected_at"),
    }