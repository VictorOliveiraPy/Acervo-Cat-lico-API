"""Modelos Pydantic v2 do acervo de conteúdo católico.

O acervo é um catálogo somente-leitura: não há banco de dados, cada categoria
mora em um arquivo JSON em `app/data/`. Estes modelos são, portanto, o contrato
com o frontend **e** o validador do conteúdo editorial — um JSON malformado ou
com campo desconhecido derruba o boot em vez de virar erro 500 em produção.

Campos de data/local são `str | None` (e não `int`/`date`) de propósito: o
acervo precisa registrar "c. 1181" ou "século VIII (tradição)" sem inventar
precisão que a fonte histórica não tem. Onde a data é certa e numérica
(concílios, proclamação de doutores), o campo é `int`.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class Category(str, Enum):
    """Categorias do acervo. O valor é o segmento usado na URL da API."""

    SANTOS = "santos"
    PAPAS = "papas"
    CONCILIOS = "concilios"
    MILAGRES_EUCARISTICOS = "milagres-eucaristicos"
    DOUTORES_IGREJA = "doutores-igreja"
    CATECISMO = "catecismo"
    CRISMA = "crisma"
    HISTORIA = "historia"
    NOSSA_SENHORA = "nossa-senhora"
    LIVROS = "livros"
    ORACOES = "oracoes"


class ContentEntry(BaseModel):
    """Campos comuns a toda entrada do acervo.

    `extra="forbid"` é intencional: erro de digitação em chave de JSON
    (ex.: "festas" em vez de "festa") deve falhar na carga, não sumir calado.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    slug: str = Field(pattern=SLUG_PATTERN)
    titulo: str = Field(min_length=1)
    resumo: str = Field(min_length=1)
    corpo: str = Field(min_length=1)
    categoria: Category
    tags: list[str] = Field(default_factory=list)
    imagem: str | None = None
    imagem_credito: str | None = None
    """Crédito exigido pela licença da imagem (ex.: "Foto: Fulano — CC BY-SA
    4.0"). `None` quando a imagem é de domínio público ou CC0, onde crédito
    não é obrigatório (ainda que seja boa prática). Nunca preenchido sem
    `imagem` também estar preenchida."""
    fontes: list[str] = Field(default_factory=list)


class Santo(ContentEntry):
    """Santo ou santa. Datas de nascimento/morte antigas podem ser aproximadas."""

    categoria: Literal[Category.SANTOS] = Category.SANTOS
    festa: str | None = None
    patronato: list[str] = Field(default_factory=list)
    nascimento: str | None = None
    morte: str | None = None


class Papa(ContentEntry):
    """Romano Pontífice. `numero_ordem` segue a lista oficial do Annuario."""

    categoria: Literal[Category.PAPAS] = Category.PAPAS
    numero_ordem: int | None = Field(default=None, ge=1)
    pontificado_inicio: str | None = None
    pontificado_fim: str | None = None


class Concilio(ContentEntry):
    """Concílio ecumênico. `numero_ordem` é a posição na lista dos ecumênicos."""

    categoria: Literal[Category.CONCILIOS] = Category.CONCILIOS
    numero_ordem: int | None = Field(default=None, ge=1)
    ano_inicio: int | None = None
    ano_fim: int | None = None
    local: str | None = None


class MilagreEucaristico(ContentEntry):
    """Milagre eucarístico com documentação eclesiástica reconhecida."""

    categoria: Literal[Category.MILAGRES_EUCARISTICOS] = Category.MILAGRES_EUCARISTICOS
    local: str | None = None
    ano: str | None = None


class Catecismo(ContentEntry):
    """Parte/seção do Catecismo da Igreja Católica.

    `ordem` mantém a sequência canônica das partes (1 a 4) na listagem;
    `paragrafos_ccc` guarda as faixas de parágrafos, ex.: "26-1065".
    """

    categoria: Literal[Category.CATECISMO] = Category.CATECISMO
    ordem: int | None = Field(default=None, ge=1)
    paragrafos_ccc: list[str] = Field(default_factory=list)


class Crisma(ContentEntry):
    """Tema de catequese de Confirmação, ancorado em parágrafos do CIC."""

    categoria: Literal[Category.CRISMA] = Category.CRISMA
    ordem: int | None = Field(default=None, ge=1)
    paragrafos_ccc: list[str] = Field(default_factory=list)


class DoutorIgreja(ContentEntry):
    """Doutor ou Doutora da Igreja."""

    categoria: Literal[Category.DOUTORES_IGREJA] = Category.DOUTORES_IGREJA
    titulo_honorifico: str | None = None
    ano_proclamacao: int | None = None


class PeriodoHistorico(ContentEntry):
    """Período amplo da história da Igreja (recorte didático, não dogmático)."""

    categoria: Literal[Category.HISTORIA] = Category.HISTORIA
    periodo: str | None = None


class TipoMariano(str, Enum):
    """Natureza de uma entrada mariana: dogma definido, aparição ou título."""

    DOGMA = "dogma"
    APARICAO = "aparicao"
    TITULO = "titulo"


class NossaSenhora(ContentEntry):
    """Dogma mariano, aparição aprovada ou título de devoção a Nossa Senhora.

    Só entram aqui aparições com reconhecimento eclesiástico formal (ex.:
    Lourdes, Guadalupe, Aparecida) — a mesma regra editorial do restante do
    acervo: nada de aparição sem reconhecimento oficial da Igreja.
    """

    categoria: Literal[Category.NOSSA_SENHORA] = Category.NOSSA_SENHORA
    tipo: TipoMariano
    ano: str | None = None
    local: str | None = None


class Livro(ContentEntry):
    """Indicação de leitura — clássico espiritual ou obra de referência."""

    categoria: Literal[Category.LIVROS] = Category.LIVROS
    autor: str | None = None
    ano_publicacao: str | None = None
    genero: str | None = None


class Oracao(ContentEntry):
    """Oração tradicional católica.

    `texto` é o corpo verbatim da oração — preserva quebras de linha (uma por
    verso/frase) porque é isso que o frontend renderiza como o texto a ser
    rezado. `corpo` (herdado de `ContentEntry`) continua sendo a explicação em
    prosa (origem, contexto, uso) — nunca o texto da própria oração.
    """

    categoria: Literal[Category.ORACOES] = Category.ORACOES
    texto: str = Field(min_length=1)
    uso: str | None = None
    origem: str | None = None


# União discriminada por `categoria`: garante que a resposta serializada
# carregue os campos próprios da subclasse (e não só os da base).
AnyEntry = Annotated[
    Union[
        Santo,
        Papa,
        Concilio,
        MilagreEucaristico,
        Catecismo,
        Crisma,
        DoutorIgreja,
        PeriodoHistorico,
        NossaSenhora,
        Livro,
        Oracao,
    ],
    Field(discriminator="categoria"),
]

# Usado pelo repositório para saber qual arquivo/modelo pertence a cada rota.
ENTRY_MODEL_BY_CATEGORY: dict[Category, type[ContentEntry]] = {
    Category.SANTOS: Santo,
    Category.PAPAS: Papa,
    Category.CONCILIOS: Concilio,
    Category.MILAGRES_EUCARISTICOS: MilagreEucaristico,
    Category.DOUTORES_IGREJA: DoutorIgreja,
    Category.CATECISMO: Catecismo,
    Category.CRISMA: Crisma,
    Category.HISTORIA: PeriodoHistorico,
    Category.NOSSA_SENHORA: NossaSenhora,
    Category.LIVROS: Livro,
    Category.ORACOES: Oracao,
}


class DatasetMeta(BaseModel):
    """Metadados editoriais do arquivo JSON de uma categoria.

    `status` e `aviso` existem para deixar explícito, no próprio dado, que o
    acervo é um conjunto inicial de exemplos — não um catálogo definitivo.
    """

    model_config = ConfigDict(extra="forbid")

    categoria: Category
    nome: str
    descricao: str
    status: Literal["exemplos-iniciais"]
    aviso: str
    revisao_editorial: str | None = None
    fontes_gerais: list[str] = Field(default_factory=list)


class Dataset(BaseModel):
    """Arquivo de dados de uma categoria: metadados + itens."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    meta: DatasetMeta = Field(alias="_meta")
    itens: list[AnyEntry]


class CategoryInfo(BaseModel):
    """Resumo de uma categoria para a tela inicial / menu."""

    categoria: Category
    nome: str
    descricao: str
    total: int
    aviso: str


class SearchResult(BaseModel):
    """Ocorrência de busca com o trecho de contexto onde o termo apareceu."""

    categoria: Category
    slug: str
    titulo: str
    trecho: str


class EntryPage(BaseModel):
    """Página de entradas de uma categoria."""

    categoria: Category
    total: int
    limit: int
    offset: int
    itens: list[AnyEntry]


class HealthStatus(BaseModel):
    """Retorno de /api/health — útil para readiness probe."""

    status: Literal["ok"]
    categorias: int
    total_entradas: int
