"""Assinatura de links do R2 (SigV4 do S3), conferida contra o exemplo oficial da AWS."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

from app.infrastructure.storage.r2 import R2Config, presign_url

# Exemplo da documentação da AWS ("Authenticating Requests: Using Query Parameters").
AWS_EXAMPLE = R2Config(
    account_id="",
    bucket="examplebucket",
    access_key_id="AKIAIOSFODNN7EXAMPLE",
    secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    public_base_url="",
    endpoint_host="examplebucket.s3.amazonaws.com",
    region="us-east-1",
    path_style=False,
)


def test_signature_matches_the_official_aws_example() -> None:
    url = presign_url(
        AWS_EXAMPLE,
        "GET",
        "test.txt",
        expires_seconds=86400,
        now=datetime(2013, 5, 24, tzinfo=UTC),
    )
    query = parse_qs(urlsplit(url).query)
    assert url.startswith("https://examplebucket.s3.amazonaws.com/test.txt?")
    assert query["X-Amz-Credential"] == [
        "AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request"
    ]
    assert query["X-Amz-Signature"] == [
        "aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404"
    ]


def test_r2_uses_the_account_endpoint_path_style_and_auto_region() -> None:
    config = R2Config(
        account_id="abc123",
        bucket="compendio",
        access_key_id="chave",
        secret_access_key="segredo",
        public_base_url="https://img.compendio-catolico.com",
    )
    url = presign_url(
        config,
        "PUT",
        "reels/meu video.mp4",
        expires_seconds=900,
        now=datetime(2026, 11, 20, tzinfo=UTC),
    )
    parts = urlsplit(url)
    assert parts.netloc == "abc123.r2.cloudflarestorage.com"
    assert parts.path == "/compendio/reels/meu%20video.mp4"
    assert parse_qs(parts.query)["X-Amz-Credential"] == [
        "chave/20261120/auto/s3/aws4_request"
    ]
    assert parse_qs(parts.query)["X-Amz-Expires"] == ["900"]
    assert (
        config.public_url("reels/x.mp4")
        == "https://img.compendio-catolico.com/reels/x.mp4"
    )
