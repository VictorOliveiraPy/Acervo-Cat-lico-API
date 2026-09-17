Você é o responsável pelo redesign completo de UI/UX do Compêndio Católico.

SITE EM PRODUÇÃO:
https://www.compendio-catolico.com/

OBJETIVO PRINCIPAL

Quero elevar o Compêndio Católico de um site de conteúdo/consulta para uma experiência digital católica moderna, sofisticada, editorial e memorável.

O projeto já possui um acervo e funcionalidades importantes.

NÃO quero reconstruir o produto do zero.

NÃO quero perder funcionalidades existentes.

NÃO quero alterar regras de negócio, APIs, banco de dados ou arquitetura sem uma necessidade técnica real.

O trabalho principal é FRONTEND + UI/UX + DESIGN SYSTEM + EXPERIÊNCIA DO USUÁRIO.

A ideia central do novo produto é:

"Católico sem parecer antiquado."

O usuário deve entrar no site e pensar:

"Isso parece uma biblioteca católica digital moderna."

e não:

"Isso é apenas uma lista de artigos."

============================================================
REGRA Nº 1 — NÃO CODIFIQUE IMEDIATAMENTE
============================================================

Antes de modificar qualquer arquivo:

1. Analise o repositório inteiro.
2. Identifique a stack utilizada.
3. Identifique framework e versão.
4. Identifique sistema de estilos.
5. Identifique componentes existentes.
6. Identifique layouts.
7. Identifique páginas e rotas.
8. Identifique componentes reutilizáveis.
9. Identifique chamadas de API.
10. Identifique como os dados são carregados.
11. Identifique funcionalidades existentes.
12. Identifique comportamento responsivo.
13. Identifique SEO.
14. Identifique acessibilidade.
15. Identifique possíveis problemas de performance.
16. Execute o projeto localmente.
17. Navegue pelo site real/local.
18. Faça uma inspeção visual das principais páginas.
19. Verifique o console do navegador.
20. Verifique erros de runtime.

NÃO faça mudanças antes dessa análise.

Primeiro quero um diagnóstico.

============================================================
ETAPA 1 — AUDITORIA DO PRODUTO
============================================================

Faça uma auditoria completa do frontend.

Analise:

HOME
HEADER
NAVEGAÇÃO
BUSCA
CATEGORIAS
PÁGINAS DE CONTEÚDO
LITURGIA
VELA
CARDS
FOOTER
MOBILE
DESKTOP
TABLET
LOADING STATES
EMPTY STATES
ERROR STATES
SEO
ACESSIBILIDADE
PERFORMANCE
TIPOGRAFIA
CORES
ESPAÇAMENTO
HIERARQUIA VISUAL
CONSISTÊNCIA DOS COMPONENTES
CTA
MICROINTERAÇÕES

Para cada problema encontrado, classifique:

- crítico
- importante
- melhoria

Mas NÃO quero rankings subjetivos sobre o conteúdo católico.

Estamos avaliando somente UX/UI/produto.

Também identifique:

O que deve ser mantido
O que deve ser melhorado
O que deve ser reorganizado
O que pode ser removido visualmente sem remover funcionalidade
O que deve ser criado

============================================================
ETAPA 2 — ENTENDER A IDENTIDADE DO PRODUTO
============================================================

O Compêndio Católico deve transmitir:

TRADIÇÃO
+
CONHECIMENTO
+
ESPIRITUALIDADE
+
TECNOLOGIA

Quero evitar completamente:

- visual genérico de site religioso
- excesso de dourado
- excesso de vinho
- excesso de ornamentos
- cruzes decorativas em excesso
- imagens religiosas genéricas
- vitrais exagerados
- fontes medievais
- aparência infantil
- aparência de template
- aparência de dashboard
- excesso de sombras
- excesso de gradientes
- excesso de animações
- glassmorphism sem propósito
- elementos decorativos que atrapalhem leitura
- visual "AI generated"

O resultado deve ser sofisticado.

Pense em:

biblioteca digital
+
enciclopédia
+
revista/editorial
+
produto tecnológico moderno.

============================================================
ETAPA 3 — DIREÇÃO VISUAL
============================================================

Crie uma direção visual consistente.

PALETA

Base:

Off-white / marfim

Texto:

Carvão / quase preto

Cor de identidade:

Vinho litúrgico profundo

Cor de apoio:

Verde escuro / oliva

Detalhes:

Dourado envelhecido utilizado com extrema moderação.

O dourado NÃO deve dominar a interface.

TIPOGRAFIA

Quero considerar uma combinação:

Títulos:
Cormorant Garamond
ou
Libre Baskerville
ou outra serif equivalente.

Interface:
Inter
ou
Geist
ou equivalente.

A escolha final deve respeitar a stack existente.

Não adicione uma biblioteca apenas para trocar fonte se houver uma solução melhor já disponível.

============================================================
ETAPA 4 — DESIGN SYSTEM
============================================================

Antes de sair criando componentes diferentes para cada página, estabeleça um pequeno design system.

Defina tokens consistentes para:

- cores
- background
- foreground
- muted
- border
- accent
- typography
- radius
- spacing
- shadows
- containers
- breakpoints

Crie componentes reutilizáveis quando fizer sentido:

Button
Input
SearchInput
Card
ContentCard
CategoryCard
SectionHeader
Badge
Breadcrumb
Navigation
Header
Footer
EmptyState
LoadingState
ErrorState
ContentMeta
RelatedContent
etc.

IMPORTANTE:

Não crie abstrações desnecessárias.

Se dois componentes são suficientemente simples e diferentes, não force uma abstração apenas para "seguir arquitetura".

Prefira código simples, legível e sustentável.

============================================================
ETAPA 5 — NOVA HOME
============================================================

A Home deve ser completamente reorganizada.

A hierarquia deve ser muito mais clara.

A primeira pergunta da Home deve ser:

"O que você quer descobrir sobre a fé?"

------------------------------------------------------------
HERO
------------------------------------------------------------

Criar uma área inicial sofisticada.

Sugestão conceitual:

COMPÊNDIO CATÓLICO

Conheça. Compreenda. Viva a fé.

Uma biblioteca digital sobre a fé,
a história e a tradição da Igreja.

E logo abaixo:

"O que você deseja conhecer?"

Campo de busca grande e protagonista.

A busca deve ser um dos elementos mais importantes da Home.

Não quero uma Home que comece simplesmente com uma lista de categorias.

------------------------------------------------------------
EXPLORAR A FÉ
------------------------------------------------------------

Criar uma seção visual para exploração.

Em vez de apresentar dezenas de categorias simultaneamente, agrupe em grandes áreas.

Exemplos:

Jesus e a Bíblia
Santos e Santidade
Doutrina e Catecismo
História da Igreja
Liturgia
Nossa Senhora
Orações
Documentos da Igreja

Cada bloco pode apresentar:

- título
- descrição curta
- quantidade de conteúdos
- ícone ou imagem discreta
- CTA

O usuário deve querer explorar.

Não invente números.

Use os dados reais existentes.

------------------------------------------------------------
DESCUBRA ALGO NOVO
------------------------------------------------------------

Criar uma seção editorial.

Título:

"Descubra algo novo"

Mostrar conteúdos reais do acervo.

Exemplo conceitual:

São Nicolau de Mira

Santos

Breve descrição.

[Conhecer]

Os cards devem parecer editoriais e não itens de banco de dados.

Se houver imagens reais disponíveis no sistema, utilizá-las.

Se não houver, NÃO inventar imagens religiosas genéricas automaticamente.

Nesse caso, criar uma solução visual elegante sem imagem.

------------------------------------------------------------
LITURGIA DO DIA
------------------------------------------------------------

Dar mais destaque para a Liturgia do Dia.

Criar uma experiência visual elegante mostrando:

- data
- tempo litúrgico
- festa/memória
- Evangelho
- referência bíblica
- CTA

Exemplo:

LITURGIA DE HOJE

15 de setembro

Nossa Senhora das Dores

Evangelho

Lc 7, 11–17

[Ler a liturgia]

Os dados devem vir do sistema existente.

NÃO inventar conteúdo.

A seção deve passar a sensação de:

"Posso voltar aqui todos os dias."

------------------------------------------------------------
VELA
------------------------------------------------------------

A funcionalidade de acender vela deve receber tratamento especial.

Conceito:

ACENDA UMA VELA

Por alguém que você ama.
Por uma intenção.
Por uma oração.

[Acender uma vela]

A experiência deve ser:

calma
espiritual
minimalista
bonita
contemplativa

Evitar efeitos exagerados.

Se já existir uma experiência funcional de vela, preservar toda a lógica e melhorar apenas a apresentação/UX.

------------------------------------------------------------
ACERVO
------------------------------------------------------------

Não despejar todo o acervo na Home.

A Home deve apresentar uma seleção inteligente.

O restante deve estar disponível através de:

categorias
busca
exploração
conteúdos relacionados

============================================================
ETAPA 6 — BUSCA
============================================================

A busca é uma das funcionalidades centrais do Compêndio.

Quero que ela pareça uma ferramenta de conhecimento.

Melhorar:

- campo
- resultados
- filtros
- categorias
- agrupamento
- destaque de termos
- navegação
- loading
- empty state
- erros
- mobile

Exemplo conceitual:

Usuário pesquisa:

"divindade de Cristo"

Resultado pode apresentar conteúdos relacionados existentes no sistema.

IMPORTANTE:

Não implemente inteligência artificial apenas para criar uma aparência de IA.

Se no futuro houver "Pergunte ao Compêndio", a interface pode ser preparada para isso.

Mas não alterar arquitetura para implementar IA agora sem necessidade.

============================================================
ETAPA 7 — PÁGINAS DE CATEGORIA
============================================================

As páginas de categoria devem ser mais agradáveis.

Exemplo:

SANTOS

Conheça homens e mulheres que testemunharam
a fé ao longo da história da Igreja.

[Busca dentro da categoria]

Depois:

cards / lista de conteúdos.

Deve existir hierarquia clara entre:

categoria
descrição
filtros
conteúdo
paginação

Não transformar tudo em cards gigantes.

O usuário precisa conseguir consultar rapidamente.

============================================================
ETAPA 8 — PÁGINAS DE CONTEÚDO
============================================================

Redesenhar completamente a experiência de leitura.

O conteúdo deve parecer uma publicação editorial.

Exemplo:

CONCÍLIOS ECUMÊNICOS

Concílio de Constantinopla I

381

Constantinopla

--------------------------------

POR QUE ELE FOI IMPORTANTE?

Texto...

--------------------------------

O QUE A IGREJA ENSINOU?

Texto...

--------------------------------

CONTEXTO HISTÓRICO

Texto...

--------------------------------

DOCUMENTOS RELACIONADOS

Cards...

--------------------------------

CONTINUE SUA LEITURA

Conteúdos relacionados.

Preservar todo o conteúdo existente.

Não resumir ou apagar informação apenas para deixar a página visualmente mais limpa.

Melhorar a apresentação do conteúdo.

============================================================
ETAPA 9 — CONTEÚDOS RELACIONADOS
============================================================

Essa funcionalidade deve ser fortalecida.

Sempre que o sistema já tiver relacionamentos, mostrar:

"Continue sua leitura"

ou

"Conteúdos relacionados"

Exemplo:

Concílio de Constantinopla I

→ Concílio de Niceia
→ Espírito Santo
→ Credo Niceno-Constantinopolitano
→ Arianismo
→ Concílio de Éfeso
→ Padres da Igreja

Utilizar dados reais.

Não inventar relacionamentos.

============================================================
ETAPA 10 — NAVEGAÇÃO
============================================================

Desktop:

Criar header limpo, elegante e simples.

Mobile:

Priorizar acesso rápido.

Avaliar uma navegação inferior com:

Início
Buscar
Liturgia
Vela

Somente implementar se realmente melhorar a experiência.

Não criar navegação duplicada ou confusa.

A navegação deve ser extremamente intuitiva.

============================================================
ETAPA 11 — MOBILE FIRST
============================================================

Mobile NÃO deve ser tratado como uma versão menor do desktop.

Faça uma análise específica.

Testar:

320px
360px
375px
390px
414px
768px
1024px
1280px
1440px+

Verificar:

- header
- menu
- hero
- busca
- cards
- leitura
- botões
- textos
- imagens
- tabelas
- listas
- navegação
- footer

Não permitir:

overflow horizontal
texto cortado
botões pequenos demais
elementos sobrepostos
cards quebrados
fontes ilegíveis
áreas de toque pequenas

============================================================
ETAPA 12 — ACESSIBILIDADE
============================================================

Preservar e melhorar:

- contraste
- semântica HTML
- labels
- aria quando necessário
- navegação por teclado
- focus states
- headings
- alt text
- áreas clicáveis
- redução de movimento quando aplicável

Não remover focus outlines simplesmente para estética.

============================================================
ETAPA 13 — SEO
============================================================

NÃO quebrar SEO.

Preservar:

- URLs existentes
- metadata
- title
- description
- headings
- canonical
- sitemap
- robots
- breadcrumbs
- conteúdo indexável
- dados estruturados existentes

Não alterar URLs existentes sem necessidade.

Se identificar melhorias, implemente somente quando forem seguras.

============================================================
ETAPA 14 — PERFORMANCE
============================================================

O redesign NÃO pode deixar o site mais lento.

Preservar/melhorar:

- Core Web Vitals
- carregamento inicial
- imagens
- lazy loading
- bundle
- SSR/SSG
- cache
- fontes
- JavaScript enviado ao cliente

Não adicionar bibliotecas pesadas apenas para animações.

Não adicionar dependências se CSS/HTML/React já resolverem.

============================================================
ETAPA 15 — ANIMAÇÕES
============================================================

Usar animações com muita moderação.

Preferir:

fade
slide sutil
hover
microinterações
transições curtas

Evitar:

parallax exagerado
efeitos brilhantes
particles
animações contínuas
efeitos religiosos chamativos
loading desnecessário

A interface deve continuar elegante mesmo com animações desativadas.

============================================================
ETAPA 16 — IMAGENS
============================================================

Imagens devem ter função.

Priorizar:

- arte sacra real quando disponível
- patrimônio histórico
- manuscritos
- arquitetura
- detalhes de arte religiosa
- imagens do próprio acervo

Evitar:

- stock photos genéricas
- imagens de pessoas posando
- imagens obviamente geradas por IA
- imagens religiosas clichês
- excesso de imagens

Se não houver uma imagem adequada, é melhor um design tipográfico sofisticado do que uma imagem ruim.

============================================================
ETAPA 17 — CONTEÚDO CATÓLICO
============================================================

NÃO alterar o conteúdo teológico existente apenas por estética.

NÃO inventar:

- santos
- datas
- documentos
- citações
- referências bíblicas
- números
- estatísticas
- eventos
- informações históricas

Quando precisar de dados para UI, utilizar os dados reais já existentes no sistema.

============================================================
ETAPA 18 — NÃO QUEBRAR O PRODUTO
============================================================

Antes de qualquer alteração, faça um inventário das funcionalidades.

Depois do redesign, TODAS devem continuar funcionando.

Verificar especialmente:

- busca
- categorias
- filtros
- páginas
- links
- navegação
- liturgia
- vela
- autenticação, se existir
- formulários
- compartilhamento
- SEO
- responsividade

Não remover código funcional simplesmente porque parece antigo.

Primeiro entenda.

============================================================
ETAPA 19 — IMPLEMENTAÇÃO INCREMENTAL
============================================================

NÃO faça 100 alterações simultaneamente sem validar.

Trabalhe em fases.

FASE A

Design system + tokens.

Validar.

FASE B

Header + navegação.

Validar.

FASE C

Hero + busca.

Validar.

FASE D

Explorar a fé.

Validar.

FASE E

Liturgia.

Validar.

FASE F

Descubra algo novo.

Validar.

FASE G

Vela.

Validar.

FASE H

Footer.

Validar.

FASE I

Categorias.

Validar.

FASE J

Páginas internas.

Validar.

FASE K

Busca/resultados.

Validar.

FASE L

Mobile.

Validar.

FASE M

Acessibilidade + SEO + performance.

Validar.

============================================================
ETAPA 20 — TESTES VISUAIS
============================================================

Depois de cada fase relevante:

1. Execute o projeto.
2. Abra no navegador.
3. Verifique console.
4. Verifique erros.
5. Navegue pelas páginas afetadas.
6. Teste desktop.
7. Teste mobile.
8. Compare com o comportamento anterior.
9. Verifique se alguma funcionalidade foi perdida.

Se houver browser automation disponível, utilize-a.

Faça screenshots das páginas principais antes/depois quando possível.

============================================================
ETAPA 21 — REGRESSÃO
============================================================

Antes de considerar o trabalho concluído:

Verifique:

HOME
BUSCA
CATEGORIAS
CONTEÚDO
LITURGIA
VELA
HEADER
FOOTER
MOBILE
DESKTOP

Verifique console.

Não pode haver:

- erro React
- hydration error
- broken link
- imagem quebrada
- overflow
- layout shift evidente
- componente duplicado
- conteúdo desaparecido
- botão sem ação
- rota quebrada

============================================================
REGRAS DE CÓDIGO
============================================================

Respeite a arquitetura atual.

Preferir:

código simples
componentes reutilizáveis
tipagem correta
boa separação de responsabilidades
sem overengineering

Não criar:

- abstrações inúteis
- dezenas de componentes para elementos triviais
- wrappers sem necessidade
- dependências desnecessárias
- arquitetura nova só porque parece mais bonita

Antes de instalar qualquer pacote:

1. Verifique se ele já existe.
2. Verifique se realmente é necessário.
3. Veja se o problema pode ser resolvido com a stack existente.

============================================================
REGRA ESPECIAL SOBRE ALTERAÇÕES
============================================================

Se encontrar algo que precise de mudança estrutural grande:

NÃO faça imediatamente.

Me informe:

- problema
- motivo
- impacto
- alternativa simples
- alternativa estrutural
- recomendação técnica

Somente depois prossiga.

============================================================
DIREÇÃO DE DESIGN
============================================================

Quero uma estética:

moderna
editorial
católica
sofisticada
acolhedora
minimalista
humana
atemporal

A referência conceitual é:

"Uma biblioteca católica digital do século XXI."

Não quero copiar visualmente nenhum site específico.

Quero absorver princípios de:

- publicação editorial
- bibliotecas digitais
- enciclopédias modernas
- produtos SaaS premium
- sites institucionais de alta qualidade
- patrimônio cultural

Mas mantendo identidade própria.

============================================================
CRITÉRIO FINAL DE SUCESSO
============================================================

Depois do redesign, o usuário deve conseguir:

1. Entender o que é o Compêndio em poucos segundos.
2. Encontrar qualquer conteúdo rapidamente.
3. Descobrir conteúdos novos naturalmente.
4. Ler artigos longos confortavelmente.
5. Consultar a Liturgia do Dia.
6. Utilizar a experiência de vela.
7. Navegar facilmente pelo celular.
8. Perceber uma identidade visual católica forte.
9. Sentir que o produto é moderno.
10. Não sentir que está navegando em um simples banco de dados.

============================================================
IMPORTANTE — NÃO INVENTAR SOLUÇÕES
============================================================

Se você não souber como determinada funcionalidade funciona:

PARE.

Investigue o código.

Se ainda não estiver claro:

explique o que encontrou e peça orientação.

Não assuma.

Não invente.

Não substitua uma implementação funcional por uma versão fictícia.

============================================================
ENTREGA FINAL
============================================================

Ao terminar, apresente um relatório contendo:

1. O que foi alterado.
2. Quais arquivos foram alterados.
3. Quais componentes foram criados.
4. Quais componentes foram reutilizados.
5. Quais dependências foram adicionadas.
6. Quais dependências foram removidas.
7. Quais funcionalidades foram preservadas.
8. Quais problemas de UX foram corrigidos.
9. Quais problemas de mobile foram corrigidos.
10. Melhorias de acessibilidade.
11. Melhorias de SEO.
12. Melhorias de performance.
13. Testes realizados.
14. Problemas restantes.
15. Sugestões futuras.

Não diga simplesmente "redesign concluído".

Quero um resumo técnico real do trabalho realizado.

============================================================
PRIORIDADE ABSOLUTA
============================================================

Em caso de conflito entre estética e funcionalidade:

FUNCIONALIDADE > PERFORMANCE > ACESSIBILIDADE > SEO > ESTÉTICA.

Em caso de conflito entre novidade e simplicidade:

SIMPLICIDADE.

Em caso de dúvida entre adicionar algo e não adicionar:

NÃO ADICIONE até entender se realmente melhora a experiência.

O objetivo não é colocar mais coisas na tela.

O objetivo é tornar o que já existe muito melhor.

============================================================
COMECE AGORA
============================================================

Primeiro:

ANALISE O PROJETO.

NÃO ALTERE CÓDIGO AINDA.

Me entregue:

1. Stack encontrada.
2. Estrutura do frontend.
3. Rotas principais.
4. Componentes principais.
5. Funcionalidades existentes.
6. Diagnóstico de UX/UI.
7. Problemas encontrados.
8. Proposta de nova arquitetura visual.
9. Design system proposto.
10. Ordem recomendada de implementação.

Somente depois dessa auditoria comece a implementação.

Para o seu caso, eu faria o redesign com uma regra de ouro:

Não queremos um site mais cheio. Queremos um site que pareça mais valioso













Sua auditoria está aprovada.

Agora NÃO implemente tudo de uma vez.

Comece somente pela FASE A: Design System + tokens + estrutura base.

Antes de alterar qualquer arquivo, liste exatamente quais arquivos pretende modificar e por quê.

Depois implemente somente essa fase.

Ao terminar, execute o projeto e faça uma verificação visual.

Não avance para a FASE B até validar que a FASE A não quebrou nada.


FASE A aprovada.

Agora execute somente a FASE B: Header + navegação.

Siga exatamente o plano aprovado.

Não altere outras áreas do sistema.

Depois teste desktop e mobile e me informe qualquer problema encontrado.