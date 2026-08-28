"""List Sourcify Parquet export v2 files via GCS-compatible XML API."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

EXPORT_BASE = "https://export.sourcify.dev"
V2_PREFIX = "v2"
GCS_NS = {"s3": "http://doc.s3.amazonaws.com/2006-03-01"}
USER_AGENT = "walpulse-workers-sourcify-verified"


@dataclass(frozen=True)
class ExportFile:
    table_name: str
    file_key: str
    etag: str
    size: int
    last_modified: str | None

    @property
    def download_url(self) -> str:
        return f"{EXPORT_BASE}/{self.file_key}"


def _parse_list_xml(xml_text: str, table_name: str) -> tuple[list[ExportFile], str | None, bool]:
    root = ET.fromstring(xml_text)
    files: list[ExportFile] = []
    for contents in root.findall("s3:Contents", GCS_NS):
        key_el = contents.find("s3:Key", GCS_NS)
        etag_el = contents.find("s3:ETag", GCS_NS)
        size_el = contents.find("s3:Size", GCS_NS)
        modified_el = contents.find("s3:LastModified", GCS_NS)
        if key_el is None or key_el.text is None:
            continue
        key = key_el.text.strip()
        if not key.endswith(".parquet"):
            continue
        etag = (etag_el.text or "").strip().strip('"')
        size = int((size_el.text or "0").strip()) if size_el is not None else 0
        modified = (modified_el.text or "").strip() if modified_el is not None else None
        files.append(
            ExportFile(
                table_name=table_name,
                file_key=key,
                etag=etag,
                size=size,
                last_modified=modified,
            )
        )
    truncated_el = root.find("s3:IsTruncated", GCS_NS)
    truncated = (truncated_el.text or "").strip().lower() == "true" if truncated_el is not None else False
    marker_el = root.find("s3:NextMarker", GCS_NS)
    marker = marker_el.text.strip() if marker_el is not None and marker_el.text else None
    return files, marker, truncated


def list_export_files(table_name: str, *, max_keys: int = 1000) -> list[ExportFile]:
    """List all Parquet files for a Sourcify export table."""
    prefix = f"{V2_PREFIX}/{table_name}/"
    marker: str | None = None
    all_files: list[ExportFile] = []

    while True:
        params: dict[str, str] = {"prefix": prefix, "max-keys": str(max_keys)}
        if marker:
            params["marker"] = marker
        url = f"{EXPORT_BASE}/?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(req, timeout=120) as resp:
                xml_text = resp.read().decode("utf-8")
        except HTTPError as e:
            raise RuntimeError(f"export list failed for {table_name}: HTTP {e.code}") from e
        except URLError as e:
            raise RuntimeError(f"export list failed for {table_name}: {e}") from e

        batch, next_marker, truncated = _parse_list_xml(xml_text, table_name)
        all_files.extend(batch)
        if not truncated:
            break
        marker = next_marker
        if not marker:
            break

    all_files.sort(key=lambda f: f.file_key)
    return all_files


def iter_all_tables(table_names: list[str]) -> Iterator[ExportFile]:
    for name in table_names:
        yield from list_export_files(name)
