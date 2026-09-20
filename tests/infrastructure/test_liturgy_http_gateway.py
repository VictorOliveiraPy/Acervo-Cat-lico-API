"""Testes do parsing do payload da fonte externa — função pura, sem rede.

`HttpLiturgyGateway.fetch` de verdade nunca é chamado aqui, só
`parse_liturgy`.
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.domain.liturgy.exceptions import LiturgyFetchError
from app.infrastructure.liturgy.http_gateway import HttpLiturgyGateway, parse_liturgy

# Trecho real da resposta da fonte externa para um dia de semana (sem
# segunda leitura), aparado para o que o parser lê.
PAYLOAD_DIA_DE_SEMANA = {
    "today": {
        "color": "branco",
        "entry_title": "<b>Tempo:</b> Comum<br/><b>Festa:</b> Natividade de Nossa Senhora",
        "readings": {
            "first_reading": {
                "title": "Primeira leitura: Miqueias 5, 1-4",
                "head": "Leitura da Profecia de Miquéias:",
                "text": "Assim diz o Senhor: 1Tu, Belém de Éfrata... [texto]",
                "footer": "- Palavra do Senhor",
                "footer_response": "- Graças a Deus",
            },
            "psalm": {
                "title": "Salmo 70 (71); 12 (13)",
                "response": "R: Exulto de alegria no Senhor.",
                "content_psalm": [
                    "- Sois meu apoio desde antes que eu nascesse...",
                    "- Uma vez que confiei no vosso amor...",
                ],
            },
            "gospel": {
                "title": "Proclamação do Evangelho de Jesus Cristo segundo São Mateus:",
                "head_title": "Evangelho de Jesus Cristo segundo São Mateus 1, 1-16.18-23",
                "head": "- Sois feliz, Virgem Maria...",
                "head_response": "- Aleluia, Aleluia, Aleluia.",
                "text": "A origem de Jesus Cristo foi assim... [texto]",
                "footer": "- Palavra da Salvação",
                "footer_response": "- Glória a Vós, Senhor",
            },
        },
    }
}

# Mesma forma, mas com segunda leitura (domingo/solenidade).
PAYLOAD_DOMINGO = {
    "today": {
        "color": "verde",
        "entry_title": "24o. Domingo do Tempo Comum",
        "readings": {
            "first_reading": {
                "title": "Primeira leitura: Isaías 50, 5-9a",
                "text": "texto da primeira leitura",
            },
            "psalm": {
                "title": "Salmo 114 (116)",
                "response": "R: Andarei na presença do Senhor.",
                "content_psalm": ["linha 1", "linha 2"],
            },
            "second_reading": {
                "title": "Segunda leitura: Romanos 14, 7-9",
                "head": "Leitura da Carta de São Paulo aos Romanos:",
                "text": "texto da segunda leitura",
            },
            "gospel": {
                "title": "Proclamação do Evangelho...",
                "head_title": "Evangelho de Jesus Cristo segundo São Marcos 8, 27-35",
                "text": "texto do evangelho",
            },
        },
    }
}


def test_should_parse_weekday_payload_without_second_reading() -> None:
    # When
    liturgy = parse_liturgy(date(2026, 9, 8), PAYLOAD_DIA_DE_SEMANA)

    # Then
    assert liturgy.date == date(2026, 9, 8)
    assert liturgy.liturgical_color == "branco"
    assert liturgy.celebration == "Tempo: Comum Festa: Natividade de Nossa Senhora"
    assert liturgy.first_reading.reference == "Primeira leitura: Miqueias 5, 1-4"
    assert "Belém" in liturgy.first_reading.text
    assert liturgy.psalm.reference == "Salmo 70 (71); 12 (13)"
    assert "Exulto de alegria" in liturgy.psalm.text
    assert liturgy.second_reading is None
    assert liturgy.gospel.reference == "Evangelho de Jesus Cristo segundo São Mateus 1, 1-16.18-23"
    assert "origem de Jesus Cristo" in liturgy.gospel.text
    assert liturgy.source == "sagradaliturgia.com.br"


def test_should_parse_sunday_payload_with_second_reading() -> None:
    # When
    liturgy = parse_liturgy(date(2026, 9, 13), PAYLOAD_DOMINGO)

    # Then
    assert liturgy.second_reading is not None
    assert liturgy.second_reading.reference == "Segunda leitura: Romanos 14, 7-9"
    assert liturgy.second_reading.text == "texto da segunda leitura"
    assert liturgy.gospel.reference == "Evangelho de Jesus Cristo segundo São Marcos 8, 27-35"


def test_parse_should_strip_html_tags_from_celebracao() -> None:
    # When
    liturgy = parse_liturgy(date(2026, 9, 8), PAYLOAD_DIA_DE_SEMANA)

    # Then
    assert "<b>" not in (liturgy.celebration or "")
    assert "<br/>" not in (liturgy.celebration or "")


async def test_should_raise_liturgy_fetch_error_when_the_external_source_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Achado real corrigido: sem isto, uma falha de rede da fonte externa
    subia como exceção crua até o use case, que precisava traduzi-la."""

    async def _boom(*args: object, **kwargs: object) -> httpx.Response:
        raise httpx.ConnectError("fonte externa fora do ar")

    monkeypatch.setattr(httpx.AsyncClient, "get", _boom)
    gateway = HttpLiturgyGateway()

    with pytest.raises(LiturgyFetchError):
        await gateway.fetch(date(2026, 9, 8))
