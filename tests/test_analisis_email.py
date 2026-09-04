"""Tests for analisis_email templates + Resend client parsing."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from workers.analisis_email.job import resolve_notify_email
from workers.analisis_email.resend_client import send_email
from workers.analisis_email.templates import build_email, ipfs_url, normalize_lang


SAMPLE_ROW = {
    "id": "11111111-1111-1111-1111-111111111111",
    "tier": "estandar",
    "wallet": "0xabcABC0000000000000000000000000000000001",
    "grade": "B",
    "grade_label": "Bueno",
    "idioma": "es",
    "pdf_cid": "bafyPdfCidExample",
    "analisis_cid": "bafyAnalisisCid",
    "evidencia_cid": "bafyEvidenciaCid",
    "notify_email": "hello@walpulse.com",
}


def test_normalize_lang_defaults():
    assert normalize_lang(None) == "es"
    assert normalize_lang("EN") == "en"
    assert normalize_lang("xx") == "es"


def test_ipfs_url():
    assert ipfs_url("QmX") == "https://gateway.pinata.cloud/ipfs/QmX"
    assert ipfs_url(None) is None
    assert ipfs_url("  ") is None


def test_build_email_es_contains_pdf_and_disclaimer():
    content = build_email(SAMPLE_ROW)
    assert content["lang"] == "es"
    assert "listo" in content["subject"].lower()
    assert "bafyPdfCidExample" in content["html"]
    assert "bafyPdfCidExample" in content["text"]
    assert "screening oficial" in content["html"].lower() or "screening" in content["text"].lower()
    assert SAMPLE_ROW["wallet"] in content["html"]
    assert SAMPLE_ROW["id"] in content["text"]


@pytest.mark.parametrize("idioma,needle", [("en", "ready"), ("pt", "pronta")])
def test_build_email_i18n_subject(idioma: str, needle: str):
    row = {**SAMPLE_ROW, "idioma": idioma}
    content = build_email(row)
    assert needle in content["subject"].lower()


def test_build_email_requires_pdf_cid():
    with pytest.raises(ValueError, match="missing_pdf_cid"):
        build_email({**SAMPLE_ROW, "pdf_cid": None})


def test_send_email_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RESEND_KEY", "re_test")

    class _Resp:
        def read(self) -> bytes:
            return json.dumps({"id": "msg_abc"}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    with patch("urllib.request.urlopen", return_value=_Resp()) as mock_open:
        out = send_email(
            to="a@b.com",
            subject="Hi",
            html="<p>x</p>",
            text="x",
        )
        assert out["id"] == "msg_abc"
        mock_open.assert_called_once()


def test_send_email_http_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RESEND_KEY", "re_test")
    err = HTTPError(
        "https://api.resend.com/emails",
        401,
        "Unauthorized",
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(b'{"message":"invalid"}'),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(RuntimeError, match="resend_http_401"):
            send_email(to="a@b.com", subject="Hi", html="<p>x</p>", text="x")


def test_send_email_missing_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RESEND_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="missing_resend_key"):
        send_email(to="a@b.com", subject="Hi", html="<p>x</p>", text="x")


def test_resolve_notify_email_prefers_request_email():
    sb = MagicMock()
    row = {
        "email": "req@example.com",
        "notify_email": "list@example.com",
        "cliente_id": "cid",
    }
    assert resolve_notify_email(sb, row) == "req@example.com"
    sb.rpc.assert_not_called()


def test_resolve_notify_email_uses_notify_email_then_cliente():
    sb = MagicMock()
    assert resolve_notify_email(sb, {"notify_email": "list@example.com"}) == "list@example.com"

    sb.rpc.return_value.execute.return_value.data = "cliente@example.com"
    assert resolve_notify_email(sb, {"cliente_id": "cid", "email": "  "}) == "cliente@example.com"
    sb.rpc.assert_called_once_with("get_cliente_email", {"p_cliente_id": "cid"})
