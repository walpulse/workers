"""Pin PDF bytes to Pinata (pinFileToIPFS)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


PINATA_PIN_FILE = "https://api.pinata.cloud/pinning/pinFileToIPFS"


def _auth_attempts() -> list[tuple[str, dict[str, str]]]:
    attempts: list[tuple[str, dict[str, str]]] = []
    jwt = (os.environ.get("PINATA_JWT") or "").strip()
    if jwt:
        attempts.append(("jwt", {"Authorization": f"Bearer {jwt}"}))
    api_key = (os.environ.get("PINATA_API_KEY") or "").strip()
    api_secret = (os.environ.get("PINATA_API_SECRET") or "").strip()
    if api_key and api_secret:
        attempts.append(
            (
                "api_key",
                {
                    "pinata_api_key": api_key,
                    "pinata_secret_api_key": api_secret,
                },
            )
        )
    return attempts


def _multipart_body(
    *,
    filename: str,
    pdf_bytes: bytes,
    metadata_name: str,
) -> tuple[bytes, str]:
    boundary = "----WalpulsePinataBoundary7MA4YWxkTrZu0gW"
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(value.encode("utf-8"))
        parts.append(b"\r\n")

    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        (
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode()
    )
    parts.append(pdf_bytes)
    parts.append(b"\r\n")

    meta = json.dumps({"name": metadata_name})
    add_field("pinataMetadata", meta)
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def pin_pdf_to_pinata(
    pdf_bytes: bytes,
    *,
    request_id: str,
    timeout_s: int = 60,
) -> str:
    """Upload PDF; return IpfsHash CID. Tries JWT then API key/secret."""
    attempts = _auth_attempts()
    if not attempts:
        raise RuntimeError("missing_pinata_credentials")

    filename = f"analisis-{request_id}.pdf"
    body, content_type = _multipart_body(
        filename=filename,
        pdf_bytes=pdf_bytes,
        metadata_name=filename,
    )

    last_err = "pinata_unknown"
    for label, auth_headers in attempts:
        headers = {**auth_headers, "Content-Type": content_type}
        req = urllib.request.Request(
            PINATA_PIN_FILE,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                payload: Any = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:400]
            last_err = f"pinata_{label}_http_{e.code}:{detail}"
            if e.code in (401, 403):
                continue
            raise RuntimeError(last_err) from e
        except urllib.error.URLError as e:
            last_err = f"pinata_{label}_url:{e}"
            raise RuntimeError(last_err) from e

        cid = payload.get("IpfsHash") or payload.get("cid")
        if not cid or not isinstance(cid, str):
            raise RuntimeError(f"pinata_{label}_missing_cid")
        return cid

    raise RuntimeError(last_err)
