# Auditoria de imagens — 3 estratégias

Data: 2026-09-17
Escopo: imagens do Acervo Católico

## Diagnóstico atual

- 1.258 entradas possuem imagem.
- 1.251 imagens usam `upload.wikimedia.org`.
- 288 imagens possuem `imagem_credito` preenchido.
- O frontend usa URLs remotas e depende da disponibilidade da Wikimedia.
- O frontend já usa `next/image`, mas está com `unoptimized: true` por causa do limite de otimização da Vercel.
- O backend valida a presença dos campos, mas não verifica atualmente se a URL resolve, se o arquivo é uma imagem ou se continua disponível.

## Sugestão 1 — Baixar e versionar no repositório

### Como funcionaria

1. Criar um script que percorre todos os JSONs.
2. Baixar cada URL válida para uma pasta de assets.
3. Validar status HTTP, `Content-Type`, tamanho e extensão.
4. Atualizar os registros para caminhos locais.
5. Manter URL original, autor, licença e crédito em um manifesto.
6. Executar a validação no CI antes do deploy.

### Vantagens

- Imagens ficam disponíveis mesmo quando a Wikimedia estiver instável.
- Deploy reproduzível.
- Não depende de um serviço externo em tempo de acesso.
- Fácil de testar localmente.

### Riscos e custos

- O repositório pode crescer muito com aproximadamente 1.258 arquivos.
- Cada atualização de imagem aumenta o tamanho do Git.
- É necessário conferir licença e atribuição antes do download.
- A Vercel pode aumentar o tempo e o tamanho do deploy.

### Avaliação

- Confiabilidade: alta.
- Complexidade: média.
- Custo operacional: baixo.
- Escalabilidade: baixa a média.

## Sugestão 2 — Storage/CDN externo com manifesto versionado

### Como funcionaria

1. Criar um bucket, por exemplo Cloudflare R2 ou storage compatível.
2. Baixar e validar as imagens em um script de sincronização.
3. Armazenar as imagens no bucket, não no Git.
4. Gerar um manifesto com URL local/CDN, URL original, licença e crédito.
5. Atualizar os JSONs ou o backend para usar a URL do CDN.
6. Rodar a sincronização no CI ou manualmente antes de cada lote.
7. Configurar fallback para uma imagem local neutra.

### Vantagens

- Não aumenta o tamanho do repositório.
- CDN melhora disponibilidade e velocidade.
- Permite trocar, redimensionar e invalidar imagens sem novo commit de código.
- Escala melhor para todo o acervo.

### Riscos e custos

- Exige configurar storage, domínio e permissões.
- Pode gerar custo, mesmo que baixo.
- O bucket também precisa de backup e controle de acesso.
- É necessário manter o manifesto e os créditos sincronizados.

### Avaliação

- Confiabilidade: muito alta.
- Complexidade: média/alta.
- Custo operacional: baixo/médio.
- Escalabilidade: alta.

## Sugestão 3 — Proxy/cache com fallback no backend

### Como funcionaria

1. Manter a URL original nos JSONs.
2. Criar uma rota ou processo de proxy que busca a imagem.
3. Armazenar uma cópia em cache quando a imagem for acessada.
4. Servir a cópia local/cache nas próximas requisições.
5. Validar periodicamente o status da URL original.
6. Entregar uma imagem reserva se a origem estiver indisponível.

### Vantagens

- Não exige baixar as 1.258 imagens de uma vez.
- Preserva a origem original no conteúdo.
- Permite migração gradual.
- Pode reduzir o risco de uma falha pontual da Wikimedia.

### Riscos e custos

- Primeira visita ainda pode depender da Wikimedia.
- A implementação de cache, headers e expiração é mais complexa.
- Pode criar problemas de banda e armazenamento no Render.
- Proxy precisa tratar abuso, hotlinking e limites de requisição.
- Não resolve completamente uma imagem que já tenha sido removida.

### Avaliação

- Confiabilidade: média/alta.
- Complexidade: alta.
- Custo operacional: médio.
- Escalabilidade: média.

## Comparação

| Critério | Repositório | Storage/CDN | Proxy/cache |
|---|---:|---:|---:|
| Evita imagem quebrada | Alta | Muito alta | Média/alta |
| Tamanho do Git | Ruim | Excelente | Excelente |
| Custo inicial | Baixo | Médio | Médio |
| Complexidade | Média | Média/alta | Alta |
| Escala para 1.258 imagens | Média | Alta | Média |
| Facilidade de rollback | Alta | Alta | Média |
| Dependência externa em runtime | Não | Baixa | Parcial |

## Recomendação

A opção preferida é a **Sugestão 2 — Storage/CDN externo com manifesto versionado**.

Ela oferece a melhor combinação de disponibilidade, desempenho e crescimento sem transformar o Git em depósito de imagens. A Sugestão 1 é adequada para um protótipo ou para um lote pequeno. A Sugestão 3 deve ser usada somente se houver necessidade de migração gradual.

## Checklist antes da implementação

- [ ] Escolher uma das três estratégias.
- [ ] Confirmar domínio/storage disponível.
- [ ] Definir política de backup.
- [ ] Validar licença de cada imagem.
- [ ] Preservar autor, URL original e crédito.
- [ ] Definir imagem fallback local.
- [ ] Criar script de validação HTTP e `Content-Type`.
- [ ] Testar uma categoria pequena antes das 1.258 imagens.
- [ ] Medir tamanho, tempo de build e Core Web Vitals.
- [ ] Fazer commit separado para a migração de imagens.

## Decisão pendente

Nenhuma imagem foi movida ou baixada por este arquivo. A implementação deve começar somente depois da escolha de uma estratégia.
