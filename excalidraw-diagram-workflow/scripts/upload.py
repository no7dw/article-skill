#!/usr/bin/env python3
"""
Upload an .excalidraw file to excalidraw.com and print a shareable URL.

Usage:
    python scripts/upload.py <path-to-file.excalidraw>
"""

import base64
import json
import os
import struct
import sys
import urllib.request
import zlib

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    print("Error: 'cryptography' package is required. Install it with: pip install cryptography")
    sys.exit(1)

UPLOAD_URL = "https://json.excalidraw.com/api/v2/post/"


def concat_buffers(*buffers: bytes) -> bytes:
    parts = [struct.pack(">I", 1)]
    for buf in buffers:
        parts.append(struct.pack(">I", len(buf)))
        parts.append(buf)
    return b"".join(parts)


def upload(excalidraw_json: str) -> str:
    file_metadata = json.dumps({}).encode("utf-8")
    inner_payload = concat_buffers(file_metadata, excalidraw_json.encode("utf-8"))
    compressed = zlib.compress(inner_payload)

    raw_key = os.urandom(16)
    iv = os.urandom(12)
    encrypted = AESGCM(raw_key).encrypt(iv, compressed, None)

    encoding_meta = json.dumps(
        {"version": 2, "compression": "pako@1", "encryption": "AES-GCM"}
    ).encode("utf-8")
    payload = concat_buffers(encoding_meta, iv, encrypted)

    request = urllib.request.Request(UPLOAD_URL, data=payload, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Upload failed with HTTP {response.status}")
        result = json.loads(response.read().decode("utf-8"))

    file_id = result.get("id")
    if not file_id:
        raise RuntimeError(f"Upload returned no file ID. Response: {result}")

    key_b64 = base64.urlsafe_b64encode(raw_key).rstrip(b"=").decode("ascii")
    return f"https://excalidraw.com/#json={file_id},{key_b64}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/upload.py <path-to-file.excalidraw>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    try:
        document = json.loads(content)
    except json.JSONDecodeError as exc:
        print(f"Error: File is not valid JSON: {exc}")
        sys.exit(1)

    if "elements" not in document:
        print("Warning: File does not contain an 'elements' key. Uploading anyway.")

    print(upload(content))


if __name__ == "__main__":
    main()
