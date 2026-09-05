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
    PECADOS = "pecados"
    LITURGIA = "liturgia"
    SACRAMENTOS = "sacramentos"
    VIRTUDES = "virtudes"
    MANDAMENTOS = "mandamentos"
    BIBLIA = "biblia"
    DEVOCOES = "devocoes"
    GLOSSARIO = "glossario"
    CALENDARIO_LITURGICO = "calendario-liturgico"
    NOVISSIMOS = "novissimos"
    ORDENS_RELIGIOSAS = "ordens-religiosas"
    ESTRUTURA_IGREJA = "estrutura-igreja"
    SANTUARIOS = "santuarios"
    DOCUMENTOS_MAGISTERIO = "documentos-magisterio"
    BEATOS_CANONIZACAO = "beatos-canonizacao"
    IGREJA_BRASIL = "igreja-brasil"
    SACRAMENTAIS = "sacramentais"
    APOLOGETICA = "apologetica"


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


class Pecado(ContentEntry):
    """Pecado capital ou outra categoria clássica de pecado, com a virtude que lhe é oposta.

    `ordem` segue a sequência tradicional dos sete pecados capitais (1 a 7)
    quando aplicável; entradas que não fazem parte dessa lista (ex.: a
    distinção entre pecado mortal e venial) deixam o campo nulo.
    """

    categoria: Literal[Category.PECADOS] = Category.PECADOS
    ordem: int | None = Field(default=None, ge=1)
    virtude_oposta: str | None = None


class Sacramento(ContentEntry):
    """Um dos sete sacramentos, com matéria, forma, ministro e efeitos —
    a estrutura clássica da teologia sacramental católica."""

    categoria: Literal[Category.SACRAMENTOS] = Category.SACRAMENTOS
    ordem: int | None = Field(default=None, ge=1)
    materia: str | None = None
    forma: str | None = None
    ministro: str | None = None
    efeitos: str | None = None
    paragrafos_ccc: list[str] = Field(default_factory=list)


class TipoVirtude(str, Enum):
    """Classificação de uma entrada de virtude/dom/bem-aventurança."""

    TEOLOGAL = "teologal"
    CARDEAL = "cardeal"
    DOM_ESPIRITO_SANTO = "dom_espirito_santo"
    FRUTO_ESPIRITO_SANTO = "fruto_espirito_santo"
    BEM_AVENTURANCA = "bem_aventuranca"
    OBRA_MISERICORDIA_CORPORAL = "obra_misericordia_corporal"
    OBRA_MISERICORDIA_ESPIRITUAL = "obra_misericordia_espiritual"


class Virtude(ContentEntry):
    """Virtude teologal ou cardeal, dom/fruto do Espírito Santo,
    bem-aventurança ou obra de misericórdia — o lado positivo da vida moral,
    complementar à categoria Pecados."""

    categoria: Literal[Category.VIRTUDES] = Category.VIRTUDES
    tipo: TipoVirtude
    ordem: int | None = Field(default=None, ge=1)
    referencia_biblica: str | None = None


class TipoMandamento(str, Enum):
    DECALOGO = "decalogo"
    IGREJA = "igreja"


class Mandamento(ContentEntry):
    """Um dos Dez Mandamentos ou um preceito da Igreja, comentado
    individualmente com referência bíblica."""

    categoria: Literal[Category.MANDAMENTOS] = Category.MANDAMENTOS
    tipo: TipoMandamento
    ordem: int | None = Field(default=None, ge=1)
    referencia_biblica: str | None = None
    paragrafos_ccc: list[str] = Field(default_factory=list)


class TestamentoBiblico(str, Enum):
    ANTIGO = "antigo"
    NOVO = "novo"


class LivroBiblia(ContentEntry):
    """Um dos 73 livros do cânon bíblico católico."""

    categoria: Literal[Category.BIBLIA] = Category.BIBLIA
    ordem: int | None = Field(default=None, ge=1)
    testamento: TestamentoBiblico
    genero_literario: str | None = None
    autor_tradicional: str | None = None
    data_composicao: str | None = None
    deuterocanonico: bool = False


class Devocao(ContentEntry):
    """Prática devocional popular católica (novenas, Via-Sacra, Sagrado
    Coração, escapulário etc.), distinta de uma oração-texto isolada."""

    categoria: Literal[Category.DEVOCOES] = Category.DEVOCOES
    ordem: int | None = Field(default=None, ge=1)
    origem: str | None = None


class TermoGlossario(ContentEntry):
    """Verbete de vocabulário litúrgico, canônico ou devocional."""

    categoria: Literal[Category.GLOSSARIO] = Category.GLOSSARIO


class TempoLiturgico(ContentEntry):
    """Tempo, cor ou grau de celebração do Ano Litúrgico."""

    categoria: Literal[Category.CALENDARIO_LITURGICO] = Category.CALENDARIO_LITURGICO
    ordem: int | None = Field(default=None, ge=1)
    cor_liturgica: str | None = None


class Novissimo(ContentEntry):
    """Uma das \"últimas coisas\" (novíssimos): morte, juízo, céu, inferno,
    purgatório."""

    categoria: Literal[Category.NOVISSIMOS] = Category.NOVISSIMOS
    ordem: int | None = Field(default=None, ge=1)


class OrdemReligiosa(ContentEntry):
    """Ordem, congregação ou família religiosa católica."""

    categoria: Literal[Category.ORDENS_RELIGIOSAS] = Category.ORDENS_RELIGIOSAS
    fundador: str | None = None
    ano_fundacao: str | None = None
    carisma: str | None = None


class ElementoEstrutural(ContentEntry):
    """Elemento da estrutura de governo e organização da Igreja Católica."""

    categoria: Literal[Category.ESTRUTURA_IGREJA] = Category.ESTRUTURA_IGREJA
    ordem: int | None = Field(default=None, ge=1)


class Santuario(ContentEntry):
    """Santuário ou basílica de peregrinação católica."""

    categoria: Literal[Category.SANTUARIOS] = Category.SANTUARIOS
    local: str | None = None
    pais: str | None = None
    ano: str | None = None


class DocumentoMagisterio(ContentEntry):
    """Documento do magistério pontifício ou conciliar (encíclica,
    constituição, exortação etc.)."""

    categoria: Literal[Category.DOCUMENTOS_MAGISTERIO] = Category.DOCUMENTOS_MAGISTERIO
    tipo_documento: str | None = None
    papa_autor: str | None = None
    ano: str | None = None


class ProcessoCanonizacao(ContentEntry):
    """Etapa, título ou conceito do processo de beatificação e canonização."""

    categoria: Literal[Category.BEATOS_CANONIZACAO] = Category.BEATOS_CANONIZACAO
    ordem: int | None = Field(default=None, ge=1)


class IgrejaBrasil(ContentEntry):
    """Tema da história e organização da Igreja Católica no Brasil."""

    categoria: Literal[Category.IGREJA_BRASIL] = Category.IGREJA_BRASIL
    ordem: int | None = Field(default=None, ge=1)


class Sacramental(ContentEntry):
    """Sacramental: sinal sagrado que, por semelhança com os sacramentos,
    dispõe a receber a graça (água benta, medalhas, bênçãos etc.)."""

    categoria: Literal[Category.SACRAMENTAIS] = Category.SACRAMENTAIS
    ordem: int | None = Field(default=None, ge=1)


class QuestaoApologetica(ContentEntry):
    """Resposta católica a uma objeção clássica sobre a fé ou a prática da Igreja."""

    categoria: Literal[Category.APOLOGETICA] = Category.APOLOGETICA
    objecao: str | None = None


class Liturgia(ContentEntry):
    """Tema de vida litúrgica e sacramental prática: partes da Missa, adoração
    eucarística, preparação para a Confissão e afins.

    `ordem` mantém a sequência de uma sequência interna (ex.: as partes da
    Missa, na ordem em que ocorrem no rito); `paragrafos_ccc` guarda as
    referências ao Catecismo, quando existem.
    """

    categoria: Literal[Category.LITURGIA] = Category.LITURGIA
    ordem: int | None = Field(default=None, ge=1)
    paragrafos_ccc: list[str] = Field(default_factory=list)


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
        Pecado,
        Liturgia,
        Sacramento,
        Virtude,
        Mandamento,
        LivroBiblia,
        Devocao,
        TermoGlossario,
        TempoLiturgico,
        Novissimo,
        OrdemReligiosa,
        ElementoEstrutural,
        Santuario,
        DocumentoMagisterio,
        ProcessoCanonizacao,
        IgrejaBrasil,
        Sacramental,
        QuestaoApologetica,
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
    Category.PECADOS: Pecado,
    Category.LITURGIA: Liturgia,
    Category.SACRAMENTOS: Sacramento,
    Category.VIRTUDES: Virtude,
    Category.MANDAMENTOS: Mandamento,
    Category.BIBLIA: LivroBiblia,
    Category.DEVOCOES: Devocao,
    Category.GLOSSARIO: TermoGlossario,
    Category.CALENDARIO_LITURGICO: TempoLiturgico,
    Category.NOVISSIMOS: Novissimo,
    Category.ORDENS_RELIGIOSAS: OrdemReligiosa,
    Category.ESTRUTURA_IGREJA: ElementoEstrutural,
    Category.SANTUARIOS: Santuario,
    Category.DOCUMENTOS_MAGISTERIO: DocumentoMagisterio,
    Category.BEATOS_CANONIZACAO: ProcessoCanonizacao,
    Category.IGREJA_BRASIL: IgrejaBrasil,
    Category.SACRAMENTAIS: Sacramental,
    Category.APOLOGETICA: QuestaoApologetica,
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
