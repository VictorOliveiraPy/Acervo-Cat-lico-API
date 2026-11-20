"""Rotas do estúdio: reels públicos, painel (segredo interno) e gerador (token próprio)."""

from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.infrastructure.studio.in_memory_repository import (
    InMemoryReelRepository,
    InMemoryVideoRequestRepository,
)
from app.main import app

SECRET = "segredo-do-site"
TOKEN = "token-do-gerador"
ADMIN = {"X-Internal-Secret": SECRET}
WORKER = {"X-Estudio-Token": TOKEN}
REEL = {
    "slug": "sao-jose",
    "titulo": "São José",
    "legenda": "O pai que cala.",
    "tema": "santos",
    "largura": 720,
    "altura": 1280,
    "video_url": "https://img.compendio-catolico.com/reels/sao-jose.mp4",
    "capa_url": "/reels/sao-jose.jpg",
}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    for key, value in {
        "internal_api_secret": SECRET,
        "estudio_token": TOKEN,
        "r2_account_id": "conta",
        "r2_bucket": "compendio",
        "r2_access_key_id": "chave",
        "r2_secret_access_key": "segredo",
    }.items():
        monkeypatch.setattr(settings, key, value)
    with TestClient(app) as test_client:
        test_client.app.state.reel_repository = InMemoryReelRepository()
        test_client.app.state.video_request_repository = (
            InMemoryVideoRequestRepository()
        )
        yield test_client


def test_public_list_shows_only_published_reels(client: TestClient) -> None:
    client.post("/api/admin/reels", json={**REEL, "publicado": True}, headers=ADMIN)
    client.post("/api/admin/reels", json={**REEL, "slug": "rascunho"}, headers=ADMIN)

    body = client.get("/api/reels").json()
    assert body["total"] == 1 and [r["slug"] for r in body["itens"]] == ["sao-jose"]
    assert client.get("/api/reels?tema=missa").json()["total"] == 0
    assert client.get("/api/reels?tema=inventado").status_code == 422


def test_admin_routes_need_the_internal_secret(client: TestClient) -> None:
    assert client.get("/api/admin/reels").status_code == 401
    assert (
        client.post(
            "/api/admin/reels", json=REEL, headers={"X-Internal-Secret": "x"}
        ).status_code
        == 401
    )
    assert (
        client.post("/api/estudio/proximo", headers=ADMIN).status_code == 401
    )  # segredo do site não abre o gerador


def test_admin_creates_edits_and_deletes_a_reel(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    deleted: list[str] = []

    async def fake_delete(_config: object, key: str) -> None:
        deleted.append(key)

    monkeypatch.setattr("app.interface.studio.router.delete_object", fake_delete)

    assert client.post("/api/admin/reels", json=REEL, headers=ADMIN).status_code == 201
    assert client.post("/api/admin/reels", json=REEL, headers=ADMIN).status_code == 409
    assert (
        client.post(
            "/api/admin/reels", json={**REEL, "slug": "Ruim"}, headers=ADMIN
        ).status_code
        == 422
    )

    edited = client.patch(
        "/api/admin/reels/sao-jose",
        json={"titulo": "São José, pai", "publicado": True},
        headers=ADMIN,
    )
    assert edited.status_code == 200 and edited.json()["titulo"] == "São José, pai"
    assert (
        client.patch(
            "/api/admin/reels/sao-jose", json={"slug": "x"}, headers=ADMIN
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/api/admin/reels/nao-existe", json={"titulo": "x"}, headers=ADMIN
        ).status_code
        == 404
    )

    assert client.delete("/api/admin/reels/sao-jose", headers=ADMIN).status_code == 204
    # Só apaga do R2 o que está no nosso bucket; a capa antiga (/reels/...) fica no site.
    assert deleted == ["reels/sao-jose.mp4"]
    assert client.delete("/api/admin/reels/sao-jose", headers=ADMIN).status_code == 404


def test_admin_gets_a_short_lived_upload_link(client: TestClient) -> None:
    response = client.post(
        "/api/admin/uploads",
        json={"slug": "novo-video", "tipo": "video"},
        headers=ADMIN,
    )
    assert response.status_code == 200
    body = response.json()
    assert urlsplit(body["upload_url"]).netloc == "conta.r2.cloudflarestorage.com"
    assert (
        body["public_url"] == "https://img.compendio-catolico.com/reels/novo-video.mp4"
    )
    assert (
        client.post(
            "/api/admin/uploads", json={"slug": "x", "tipo": "zip"}, headers=ADMIN
        ).status_code
        == 422
    )


def test_full_studio_flow(client: TestClient) -> None:
    created = client.post(
        "/api/admin/pedidos",
        json={
            "tema": "A confissão",
            "pergunta": "O padre pode contar?",
            "formato": "cinema",
        },
        headers=ADMIN,
    )
    assert created.status_code == 201
    request_id = created.json()["id"]

    job = client.post("/api/estudio/proximo", headers=WORKER)
    assert job.status_code == 200 and job.json()["id"] == request_id
    assert client.post("/api/estudio/proximo", headers=WORKER).status_code == 204

    progress = client.post(
        f"/api/estudio/pedidos/{request_id}/andamento",
        json={"etapa": "Renderizando", "progresso": 40},
        headers=WORKER,
    )
    assert progress.status_code == 204
    assert (
        client.get("/api/admin/pedidos", headers=ADMIN).json()[0]["etapa"]
        == "Renderizando"
    )

    upload = client.post(
        f"/api/estudio/pedidos/{request_id}/upload",
        json={"slug": "a-confissao", "tipo": "capa"},
        headers=WORKER,
    )
    assert upload.json()["public_url"].endswith("/reels/a-confissao.jpg")

    done = client.post(
        f"/api/estudio/pedidos/{request_id}/pronto",
        json={
            "slug": "a-confissao",
            "titulo": "A confissão",
            "legenda": "O sigilo.",
            "largura": 720,
            "altura": 1280,
        },
        headers=WORKER,
    )
    assert done.status_code == 201
    reel = done.json()
    # Pronto não é publicado: o vídeo espera a revisão no painel.
    assert reel["publicado"] is False and reel["video_url"].endswith(
        "/reels/a-confissao.mp4"
    )
    assert (
        client.get("/api/admin/pedidos", headers=ADMIN).json()[0]["status"] == "pronto"
    )
    assert client.get("/api/reels").json()["total"] == 0

    client.patch(
        "/api/admin/reels/a-confissao", json={"publicado": True}, headers=ADMIN
    )
    assert client.get("/api/reels").json()["total"] == 1


def test_worker_reports_errors_and_admin_can_retry(client: TestClient) -> None:
    request_id = client.post(
        "/api/admin/pedidos", json={"tema": "Missa"}, headers=ADMIN
    ).json()["id"]
    client.post("/api/estudio/proximo", headers=WORKER)
    client.post(
        f"/api/estudio/pedidos/{request_id}/erro",
        json={"mensagem": "O render falhou."},
        headers=WORKER,
    )
    listed = client.get("/api/admin/pedidos", headers=ADMIN).json()[0]
    assert (listed["status"], listed["erro"]) == ("erro", "O render falhou.")

    assert (
        client.post(
            f"/api/admin/pedidos/{request_id}/refazer", headers=ADMIN
        ).status_code
        == 200
    )
    assert (
        client.post("/api/estudio/proximo", headers=WORKER).json()["id"] == request_id
    )
    assert (
        client.post(f"/api/admin/pedidos/{request_id}/cancelar", headers=ADMIN).json()[
            "status"
        ]
        == "cancelado"
    )


def test_worker_gets_nothing_while_r2_is_not_configured(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Sem o R2, o vídeo não teria para onde ir: o pedido fica na fila em vez de
    # gastar meia hora de render e falhar no envio.
    client.post("/api/admin/pedidos", json={"tema": "Missa"}, headers=ADMIN)
    monkeypatch.setattr(settings, "r2_secret_access_key", None)
    assert client.post("/api/estudio/proximo", headers=WORKER).status_code == 503
    assert client.get("/api/admin/pedidos", headers=ADMIN).json()[0]["status"] == "na_fila"
