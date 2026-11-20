"""Links assinados do Cloudflare R2 (API compatível com S3, assinatura SigV4).

A API guarda a chave do R2 e entrega só links que valem alguns minutos, para um
arquivo e um método: o gerador de vídeos e o painel enviam direto ao R2 sem nunca
ver a chave. Sem SDK: são umas poucas linhas de HMAC, conferidas contra o exemplo
oficial da AWS nos testes.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote

import httpx


@dataclass(frozen=True)
class R2Config:
    account_id: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    # Endereço público do bucket (domínio próprio), para montar o link de leitura.
    public_base_url: str
    endpoint_host: str | None = None
    region: str = "auto"
    path_style: bool = True

    @property
    def host(self) -> str:
        return self.endpoint_host or f"{self.account_id}.r2.cloudflarestorage.com"

    def public_url(self, key: str) -> str:
        return f"{self.public_base_url.rstrip('/')}/{key}"


def _sign(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def presign_url(
    config: R2Config,
    method: str,
    key: str,
    *,
    expires_seconds: int,
    now: datetime | None = None,
) -> str:
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    amz_date = moment.strftime("%Y%m%dT%H%M%SZ")
    date = moment.strftime("%Y%m%d")
    scope = f"{date}/{config.region}/s3/aws4_request"
    path = f"/{config.bucket}/{key}" if config.path_style else f"/{key}"
    canonical_path = quote(path, safe="/-_.~")

    params = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": f"{config.access_key_id}/{scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires_seconds),
        "X-Amz-SignedHeaders": "host",
    }
    query = "&".join(
        f"{quote(k, safe='-_.~')}={quote(v, safe='-_.~')}"
        for k, v in sorted(params.items())
    )
    canonical = "\n".join(
        [
            method,
            canonical_path,
            query,
            f"host:{config.host}\n",
            "host",
            "UNSIGNED-PAYLOAD",
        ]
    )
    to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical.encode()).hexdigest(),
        ]
    )
    signing_key = _sign(
        _sign(
            _sign(
                _sign(f"AWS4{config.secret_access_key}".encode(), date), config.region
            ),
            "s3",
        ),
        "aws4_request",
    )
    signature = hmac.new(signing_key, to_sign.encode(), hashlib.sha256).hexdigest()
    return f"https://{config.host}{canonical_path}?{query}&X-Amz-Signature={signature}"


async def delete_object(config: R2Config, key: str) -> None:
    """Apaga um arquivo do bucket. Arquivo que já não existe não é erro."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.delete(
            presign_url(config, "DELETE", key, expires_seconds=60)
        )
    if response.status_code not in (200, 204, 404):
        response.raise_for_status()
