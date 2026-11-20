"""Regras das métricas de visitas: anônimas, sem cookie e sem guardar IP."""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.metrics.rules import (
    EVENT_NAMES,
    build_hit,
    clean_path,
    device_of,
    is_bot,
    referrer_host,
    visitor_id,
)

DAY = date(2026, 11, 19)
PHONE = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 Chrome/131.0 Mobile Safari/537.36"
DESKTOP = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
)
OWN = ("compendio-catolico.com",)


@pytest.mark.parametrize(
    "ua",
    [
        "Googlebot/2.1 (+http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; bingbot/2.0)",
        "Mozilla/5.0 HeadlessChrome/131.0",
        "facebookexternalhit/1.1",
        "WhatsApp/2.23",
        "curl/8.0",
        "",
    ],
)
def test_should_treat_crawlers_previews_and_empty_agents_as_bots(ua: str) -> None:
    assert is_bot(ua)


def test_should_count_real_browsers() -> None:
    assert not is_bot(PHONE)
    assert not is_bot(DESKTOP)


def test_should_tell_phone_from_computer() -> None:
    assert device_of(PHONE) == "celular"
    assert (
        device_of("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)") == "celular"
    )
    assert device_of(DESKTOP) == "computador"


def test_visitor_id_is_stable_in_a_day_and_changes_the_next() -> None:
    today = visitor_id("200.1.2.3", PHONE, DAY, "segredo")
    assert today == visitor_id("200.1.2.3", PHONE, DAY, "segredo")
    assert today != visitor_id("200.1.2.3", PHONE, date(2026, 11, 20), "segredo")
    assert today != visitor_id("200.1.2.4", PHONE, DAY, "segredo")
    # Não dá para voltar ao IP: é um hash curto, sem o IP dentro.
    assert "200.1.2.3" not in today
    assert len(today) == 16


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/santos/francisco-de-assis", "/santos/francisco-de-assis"),
        ("/busca?q=maria", "/busca"),
        ("/santos/#fontes", "/santos"),
        ("/", "/"),
        ("santos", None),
        ("//evil.com/x", None),
        ("/" + "a" * 300, None),
        ("", None),
    ],
)
def test_should_keep_only_a_clean_internal_path(raw: str, expected: str | None) -> None:
    assert clean_path(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://www.google.com/search?q=santo", "google.com"),
        ("https://l.instagram.com/?u=x", "l.instagram.com"),
        ("https://compendio-catolico.com/santos", None),
        ("https://www.compendio-catolico.com/", None),
        ("android-app://com.google.android.gm/", None),
        ("", None),
        ("lixo", None),
    ],
)
def test_should_keep_only_the_external_referrer_domain(
    raw: str, expected: str | None
) -> None:
    assert referrer_host(raw, OWN) == expected


def test_build_hit_for_a_page_view() -> None:
    hit = build_hit(
        {
            "tipo": "pagina",
            "caminho": "/santos?x=1",
            "referencia": "https://www.google.com/",
        },
        ip="200.1.2.3",
        user_agent=PHONE,
        day=DAY,
        secret="segredo",
        own_hosts=OWN,
    )
    assert hit is not None
    assert (hit.kind, hit.path, hit.event, hit.referrer, hit.device) == (
        "pagina",
        "/santos",
        None,
        "google.com",
        "celular",
    )
    assert hit.visitor == visitor_id("200.1.2.3", PHONE, DAY, "segredo")


def test_build_hit_for_a_known_event_only() -> None:
    common = {
        "ip": "1.1.1.1",
        "user_agent": DESKTOP,
        "day": DAY,
        "secret": "s",
        "own_hosts": OWN,
    }
    hit = build_hit(
        {"tipo": "evento", "caminho": "/velas", "evento": "candle_lit"}, **common
    )
    assert hit is not None and hit.event == "candle_lit"
    assert (
        build_hit({"tipo": "evento", "caminho": "/", "evento": "inventado"}, **common)
        is None
    )
    assert "candle_lit" in EVENT_NAMES


def test_build_hit_drops_bots_and_garbage() -> None:
    args = {"ip": "1.1.1.1", "day": DAY, "secret": "s", "own_hosts": OWN}
    assert (
        build_hit({"tipo": "pagina", "caminho": "/"}, user_agent="Googlebot", **args)
        is None
    )
    assert (
        build_hit({"tipo": "outro", "caminho": "/"}, user_agent=DESKTOP, **args) is None
    )
    assert (
        build_hit({"tipo": "pagina", "caminho": "x"}, user_agent=DESKTOP, **args)
        is None
    )
    assert build_hit("nao e objeto", user_agent=DESKTOP, **args) is None  # type: ignore[arg-type]
