import os
import json
from typing import Any
from dotenv import load_dotenv
from vercel.blob import BlobClient, AsyncBlobClient

load_dotenv()

token = os.getenv("BLOB_READ_WRITE_TOKEN")

print("[BLOB DEBUG] token present:", bool(token))
print("[BLOB DEBUG] token length:", len(token) if token else 0)
print("[BLOB DEBUG] token prefix:", token[:12] if token else "NONE")
print("[BLOB DEBUG] store id present:", bool(os.getenv("BLOB_STORE_ID")))

def get_blob_client() -> BlobClient:
    """Create a Vercel Blob client."""
    return BlobClient()

async def get_blob(blob_path: str):
    print(
        "[BLOB DEBUG] token present:",
        bool(os.getenv("BLOB_READ_WRITE_TOKEN"))
    )
    print(
        "[BLOB DEBUG] store id present:",
        bool(os.getenv("BLOB_STORE_ID"))
    )

    client = AsyncBlobClient()
    return await client.get(blob_path, access="private",token=os.getenv("BLOB_READ_WRITE_TOKEN"),)

def upload_bytes(data: bytes, blob_path: str, content_type: str) -> str:
    print(f"[BLOB UPLOAD] Starting: {blob_path}")
    print(f"[BLOB UPLOAD] Size: {len(data)} bytes")
    print(f"[BLOB UPLOAD] Token present: {bool(os.getenv('BLOB_READ_WRITE_TOKEN'))}")

    client = get_blob_client()

    print("[BLOB UPLOAD] Client created")

    result = client.put(
        blob_path,
        data,
        access="private",
        content_type=content_type,
        add_random_suffix=False,
        overwrite=True,
        token=os.getenv("BLOB_READ_WRITE_TOKEN"),
    )

    print(f"[BLOB UPLOAD] PUT returned: {result}")
    print(f"[BLOB UPLOAD] URL: {result.url}")

    return result.url
    
def upload_file(
    local_path: str,
    blob_path: str,
    content_type: str,
) -> str:
    """
    Read a local file and upload it to Vercel Blob.

    Returns the Blob URL.
    """
    with open(local_path, "rb") as file:
        data = file.read()

    return upload_bytes(
        data=data,
        blob_path=blob_path,
        content_type=content_type,
    )


def upload_json(
    data: Any,
    blob_path: str,
) -> str:
    """
    Convert Python data to JSON and upload it to Vercel Blob.
    """
    payload = json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return upload_bytes(
        data=payload,
        blob_path=blob_path,
        content_type="application/json",
    )


def upload_evidence(
    trace_id: int,
    evidence_data: Any,
) -> str:
    """Upload a trace's evidence bundle."""
    return upload_json(
        data=evidence_data,
        blob_path=f"citrus/evidence/evidence_{trace_id}.json",
    )


def upload_graph(
    trace_id: int,
    graph_path: str,
) -> str:
    """Upload a generated investigation graph."""
    return upload_file(
        local_path=graph_path,
        blob_path=f"citrus/graphs/graph_{trace_id}.html",
        content_type="text/html",
    )


def upload_report(
    trace_id: int,
    report_path: str,
) -> str:
    """Upload a generated PDF investigation report."""
    return upload_file(
        local_path=report_path,
        blob_path=f"citrus/reports/report_{trace_id}.pdf",
        content_type="application/pdf",
    )