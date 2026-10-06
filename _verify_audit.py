"""Verificação manual (não é teste) dos achados da auditoria.

Confirmado contra o `app` real: contrato de erro unificado, headers de
segurança, docs desligados em produção e o rate limit configurável.
Roda com: `.venv\\Scripts\\python.exe _verify_audit.py`
"""

from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("ENVIRONMENT", "development")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, condition, detail))


with TestClient(app) as client:
    # 1) Validação de parâmetro → 422 no contrato {code,message,details}
    r = client.get("/api/search", params={"q": "a"})
    body = r.json()
    check("422 status", r.status_code == 422, str(r.status_code))
    check("422 contract code", body.get("code") == "validation_error", str(body.get("code")))
    check("422 contract keys", set(body) == {"code", "message", "details"}, str(set(body)))
    check(
        "422 no raw input echoed",
        all("input" not in e for e in body.get("details", {}).get("errors", [])),
    )

    # 2) Categoria inexistente cai na rota coringa do acervo → AppException 404
    r = client.get("/api/rota-que-nao-existe")
    body = r.json()
    check("404 (acervo) status", r.status_code == 404, str(r.status_code))
    check(
        "404 (acervo) contract code",
        body.get("code") == "CATEGORY_NOT_FOUND",
        str(body.get("code")),
    )
    check("404 (acervo) contract keys", set(body) == {"code", "message", "details"}, str(set(body)))

    # 2b) Rota FORA do prefixo /api → handler do Starlette normaliza
    r = client.get("/rota-fora-do-api")
    body = r.json()
    check("404 (Starlette) status", r.status_code == 404, str(r.status_code))
    check("404 (Starlette) contract code", body.get("code") == "NOT_FOUND", str(body.get("code")))
    check("404 (Starlette) contract keys", set(body) == {"code", "message", "details"}, str(set(body)))

    # 3) Método errado → 405 normalizado
    r = client.put("/api/categories")
    body = r.json()
    check("405 status", r.status_code == 405, str(r.status_code))
    check("405 contract code", body.get("code") == "METHOD_NOT_ALLOWED", str(body.get("code")))
    check("405 contract keys", set(body) == {"code", "message", "details"}, str(set(body)))

    # 4) Headers de segurança em resposta normal
    r = client.get("/api/health")
    h = r.headers
    check("nosniff", h.get("x-content-type-options") == "nosniff", str(h.get("x-content-type-options")))
    check("frame DENY", h.get("x-frame-options") == "DENY", str(h.get("x-frame-options")))
    check("referrer", h.get("referrer-policy") == "no-referrer", str(h.get("referrer-policy")))
    check("sem HSTS em dev", "strict-transport-security" not in h, str(h.get("strict-transport-security")))

    # 5) Acervo normal continua funcionando
    r = client.get("/api/health")
    check("health ok", r.status_code == 200 and r.json()["status"] == "ok", str(r.status_code))

# 6) Docs desligados quando ENVIRONMENT=production
import importlib  # noqa: E402

import app.core.config as config_module  # noqa: E402
import app.main as main_module  # noqa: E402

with patch.dict(os.environ, {"ENVIRONMENT": "production", "DEBUG": "false"}):
    config_module.get_settings.cache_clear()
    prod_settings = config_module.Settings()
    check("prod invariants ok", prod_settings.is_production is True)
    with patch.object(main_module, "settings", prod_settings):
        prod_app = main_module.FastAPI(
            title="prod-check",
            lifespan=lambda _app: None,  # type: ignore[arg-type]
            **main_module._docs_kwargs(),
        )
        main_module.app.add_middleware  # noqa: B018 — só para deixar explícito que não reusamos
        from app.core.security_headers import SecurityHeadersMiddleware  # noqa: E402

        prod_app.add_middleware(SecurityHeadersMiddleware, enable_hsts=prod_settings.is_production)
        with TestClient(prod_app) as prod_client:
            check("docs off (prod)", prod_client.get("/docs").status_code == 404)
            check("openapi off (prod)", prod_client.get("/openapi.json").status_code == 404)
    config_module.get_settings.cache_clear()

# 7) Rate limit configurável
from app.core.rate_limiting import build_rate_limiter  # noqa: E402

with patch("app.core.rate_limiting.settings") as fake_settings:
    fake_settings.rate_limit_enabled = False
    limiter = build_rate_limiter(window_seconds=60.0)
    limiter.check("1.2.3.4")
    try:
        limiter.check("1.2.3.4")
        check("rate limit desligável", True)
    except Exception as exc:  # noqa: BLE001
        check("rate limit desligável", False, repr(exc))

# 8) Handler de DataIntegrityError não vaza o detalhe interno
from app.core.exceptions import DataIntegrityError  # noqa: E402
from app.interface.exception_handlers import register_exception_handlers  # noqa: E402

leak_app = main_module.FastAPI()
register_exception_handlers(leak_app)


@leak_app.get("/boom")
def _boom() -> None:
    raise DataIntegrityError("constraint uq_velas_nome violada na tabela velas")


with TestClient(leak_app, raise_server_exceptions=False) as leak_client:
    r = leak_client.get("/boom")
    body = r.json()
    check("DataIntegrity 500", r.status_code == 500, str(r.status_code))
    check("DataIntegrity code", body.get("code") == "INTERNAL_ERROR", str(body.get("code")))
    check(
        "DataIntegrity sem vazamento",
        "constraint" not in str(body) and "velas" not in str(body),
        str(body),
    )

failed = [c for c in checks if not c[1]]
for name, ok, detail in checks:
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" -> {detail}" if detail and not ok else ""))
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks OK")
raise SystemExit(1 if failed else 0)
