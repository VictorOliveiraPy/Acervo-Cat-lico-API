"""Testes do parsing do payload da fonte externa — função pura, sem rede.

`fetch_liturgia`/`HttpLiturgiaGateway.fetch` de verdade nunca são chamados
aqui, só `parse_liturgia`.
"""

from __future__ import annotations

from datetime import date

from app.infrastructure.liturgia.http_gateway import parse_liturgia

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
    liturgia = parse_liturgia(date(2026, 9, 8), PAYLOAD_DIA_DE_SEMANA)

    # Then
    assert liturgia.data == date(2026, 9, 8)
    assert liturgia.cor_liturgica == "branco"
    assert liturgia.celebracao == "Tempo: Comum Festa: Natividade de Nossa Senhora"
    assert liturgia.primeira_leitura.referencia == "Primeira leitura: Miqueias 5, 1-4"
    assert "Belém" in liturgia.primeira_leitura.texto
    assert liturgia.salmo.referencia == "Salmo 70 (71); 12 (13)"
    assert "Exulto de alegria" in liturgia.salmo.texto
    assert liturgia.segunda_leitura is None
    assert liturgia.evangelho.referencia == "Evangelho de Jesus Cristo segundo São Mateus 1, 1-16.18-23"
    assert "origem de Jesus Cristo" in liturgia.evangelho.texto
    assert liturgia.fonte == "sagradaliturgia.com.br"


def test_should_parse_sunday_payload_with_second_reading() -> None:
    # When
    liturgia = parse_liturgia(date(2026, 9, 13), PAYLOAD_DOMINGO)

    # Then
    assert liturgia.segunda_leitura is not None
    assert liturgia.segunda_leitura.referencia == "Segunda leitura: Romanos 14, 7-9"
    assert liturgia.segunda_leitura.texto == "texto da segunda leitura"
    assert liturgia.evangelho.referencia == "Evangelho de Jesus Cristo segundo São Marcos 8, 27-35"


def test_parse_should_strip_html_tags_from_celebracao() -> None:
    # When
    liturgia = parse_liturgia(date(2026, 9, 8), PAYLOAD_DIA_DE_SEMANA)

    # Then
    assert "<b>" not in (liturgia.celebracao or "")
    assert "<br/>" not in (liturgia.celebracao or "")
