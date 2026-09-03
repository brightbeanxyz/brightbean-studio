# Social Content AI — auditoria arquitetural

> Fase 1, revisão auditada `d85fce1`. Este documento registra a implementação
> existente e o plano. Nenhuma feature das fases seguintes foi implementada.

## Resumo executivo

BrightBean Studio já é um monólito Django modular e multi-tenant funcional.
Organizações contêm workspaces; conteúdo, aprovação, agenda, publicação, mídia,
analytics, REST e MCP já existem. Social Content AI deve ser uma camada
adjacente ao Composer e Analytics, sem substituir esses domínios.

Existe `apps.intelligence`, mas ele integra um serviço opcional BrightBean
Intelligence (subscription, billing, provisioning e playground), não o motor
editorial pedido. O novo domínio deve usar o namespace
`content_intelligence`, preservando o app existente.

## Mapa da arquitetura atual

| Área | Implementação | Responsabilidade |
|---|---|---|
| Identidade | `apps.accounts` | User, auth/allauth, Google SSO, sessões, TOTP |
| Tenancy | `apps.organizations`, `apps.workspaces` | Organização → workspaces/clientes |
| RBAC | `apps.members` | Papéis de org/workspace, custom roles e permissões |
| Credenciais | `apps.credentials`, `apps.common.encryption` | Segredos e tokens criptografados |
| Social/OAuth | `apps.social_accounts`, `providers/` | Conexão, refresh, saúde e APIs oficiais |
| Conteúdo | `apps.composer` | Ideias, posts, variantes, templates e versões |
| Aprovação | `apps.approvals`, `apps.client_portal` | Estados, ações, comentários e cliente |
| Agenda | `apps.calendar` | Slots, queues, recorrência e calendário |
| Publicação | `apps.publisher` | Poll, providers, retry, limites e audit log |
| Mídia | `apps.media_library` | Local/S3, folders, variantes, versões e uploads |
| Analytics | `apps.analytics` | Snapshots, sync, métricas e dashboards |
| REST | `apps.api`, `apps.api_keys` | Ninja, escopo, quotas, idempotência e auditoria |
| MCP | `apps.mcp`, `apps.oauth_server` | HTTP, API key/OAuth 2.1 e tools |
| UI | `templates`, `static`, `theme` | Django, HTMX, Alpine.js e Tailwind |
| Jobs | `django-background-tasks` | Worker e tarefas recorrentes |

Stack: Python 3.12+, Django 5.x, Django Ninja, HTMX, Alpine.js, Tailwind,
PostgreSQL (SQLite local), Gunicorn, Caddy e Docker. Licença AGPL-3.0.

## Autenticação, multiusuário, workspaces e RBAC

`User` usa UUID/e-mail. Há Django auth, allauth, Google SSO, rate limit de
login, aceite de termos, sessões e campos TOTP criptografados.

`Organization` é o agregado superior. `Workspace` pertence a uma organização e
é a fronteira de cliente, com timezone, branding básico, hashtags, primeiro
comentário e modo de aprovação. Contas, posts, calendário e analytics são
workspace-scoped; mídia pode ser do workspace ou compartilhada na organização.
Managers scoped, middleware, decorators e filtros protegem o isolamento.

Papéis de org: `owner`, `admin`, `member`. Papéis de workspace: `owner`,
`manager`, `editor`, `contributor`, `client`, `viewer`, mais `CustomRole`.
Permissões cobrem posts, aprovação, publicação, social, analytics, inbox,
workspace e mídia.

Não renomear papéis existentes. Adicionar `strategist`, `creator` e `reviewer`
como presets e permissões `manage_brand`, `generate_content`,
`manage_editorial_strategy`, `schedule_posts`, `manage_billing`. Preservar
memberships/custom roles e manter `publish_directly` como barreira final.

## Social accounts e OAuth

`SocialAccount` guarda conta nativa, tokens OAuth criptografados, refresh,
expiração, saúde, webhooks e reconexão. Credenciais de app vêm do ambiente ou
de `PlatformCredential` por organização. OAuth usa state assinado, PKCE quando
aplicável e seleção de Page/Company.

Há providers oficiais para Facebook, Instagram (Facebook Login e Direct),
LinkedIn Personal/Company, TikTok, YouTube, Pinterest, Threads, Bluesky, Google
Business, Mastodon e DEV.to. Reutilizar integralmente:

- `providers/linkedin.py`, `linkedin_personal.py`, `linkedin_company.py`;
- `providers/instagram.py`, `instagram_login.py`;
- factory/DTOs, callbacks, refresh/revoke, health checks e criptografia.

Nenhum fluxo novo usará scraping, Selenium ou Playwright.

## Composer, content library e aprovação

`Post` guarda conteúdo base, autor, categoria, tags, notas e datas proposta,
agendada/publicada. Cada destino possui `PlatformPost`, overrides e estado
independente. O status agregado é derivado dos filhos.

Estados atuais: `draft`, `pending_review`, `pending_client`, `approved`,
`changes_requested`, `rejected`, `scheduled`, `publishing`, `published`,
`failed`, `on_hold`. A máquina já protege transições. `GENERATED` deve ser
origem/metadado, mantendo o post como `draft`; `ARCHIVED` deve ser campo
ortogonal (`archived_at`). `PostVersion` já guarda snapshots imutáveis.
Categorias, tags, templates, clonagem, ideias/Kanban, CSV e overrides também
serão reutilizados. Geração termina em `composer.services.create_post` como
draft.

O workspace já suporta aprovação nenhuma, opcional, interna ou interna +
cliente. Services registram `ApprovalAction`, comentários, change request,
reject, hold/resume e lote. Há reminders/escalation e portal por magic link.

- `MANUAL`: aprovação obrigatória; humano agenda.
- `SEMI_AUTOMATIC`: aprovação em lote + slots após aprovação.
- `AUTOMATIC`: somente por policy ativa, versionada e auditável.

Automatic nasce desabilitado. Toda decisão registra policy, versão, inputs,
resultado e justificativa. Geração nunca aprova/publica sozinha.

## Scheduler, jobs e publishing

`PostingSlot`, `Queue`, `QueueEntry`, `RecurrenceRule` e eventos já oferecem
agenda e recorrência. Horário proposto é separado do agendamento efetivo.

Publisher registra ciclo de 15 segundos em `post_migrate`. O engine busca posts
vencidos, verifica aprovação/estado, resolve/renova credenciais, respeita
limites e chama provider oficial. Tentativas geram `PublishLog`;
`RateLimitState` é por conta. Primeiro comentário tem estado/retry próprio.

AI apenas propõe horário ou cria drafts. Agendamento real passa pelos services
e checks atuais; nunca chama `PublishEngine` diretamente. Jobs de publicação,
analytics, reminders, inbox, notifications, sessões, idempotência e mídia usam
um worker. LLM/imagem pode causar starvation; medir e separar workers antes de
carga relevante, sem trocar infraestrutura na Fase 2.

## Mídia e Visual Brief

`MediaAsset` suporta imagens, vídeos, GIF/documento, escopo org/workspace,
folders, dimensões, thumbnail, tags, processamento, variantes e versões. Há
storage local/S3, uploads web/REST/MCP e presigned em duas fases com inspeção,
quota e idempotência.

`VisualBrief` será novo, ligado a Brand e opcionalmente Generation/Post. Assets
gerados serão registrados pelos media-library services e anexados via
`PostMedia`; blobs não ficarão no brief.

## Analytics

`AccountInsightsSnapshot` e `PostInsightsSnapshot` guardam séries diárias.
Tasks fazem backfill/sync; providers traduzem métricas; services calculam
séries, deltas, engagement e fallbacks. REST/MCP usam builders comuns.

Adicionar sem alterar snapshots brutos: `ContentPerformanceScore` versionado,
`ContentInsight` com evidência/confiança e `EditorialRecommendation` com estado
e justificativa. Métrica ausente não vira zero. Scores normalizam plataforma,
tamanho da conta, janela e objetivo.

## REST, MCP e API

REST fica em `/api/v1/`, OpenAPI em `/api/v1/docs`. Há me, accounts, posts,
mídia e analytics, com permissões, allowlists, rate limit, quotas, idempotência,
transações e audit log.

MCP fica em `/api/v1/mcp`, via API key ou OAuth 2.1. Tools atuais:
`list_accounts`, `create_draft`, `schedule_post`, `get_post`, `list_posts`,
`cancel_post`, `schedule_draft`, `search_media`, `get_media`, `upload_media`,
`request_media_upload`, `finalize_media_upload`, `get_account_analytics` e
`get_post_analytics`.

Não duplicar tools existentes. Routers e MCP handlers novos serão adapters
finos sobre services comuns. `approve_post` exige `approve_posts`; gerar não
concede aprovar/agendar/publicar.

## Deployment e credenciais

Docker dev possui migration, app, worker, Tailwind e PostgreSQL. Produção usa
Gunicorn/Caddy. Há manifests Railway, Render e Heroku. Migrations precedem
app/worker e registram tarefas recorrentes. Configuração vem de `.env`; storage
é local ou S3/R2 (obrigatório em filesystem efêmero).

Providers de IA precisam de secrets no ambiente ou modelo criptografado,
timeout/backoff, quotas, custo e erros sanitizados. Endpoint Ollama precisa de
allowlist para prevenir SSRF.

## Testes existentes

Foram encontrados 86 arquivos `test*.py`, cobrindo models, security, RBAC,
providers, OAuth/PKCE, composer, approval, calendar, publisher, analytics,
mídia, inbox, portal, REST e MCP, incluindo isolamento, transações,
idempotência, quotas e paridade REST/MCP.

A suíte não rodou porque `pytest` não está instalado. Nenhuma dependência foi
instalada nesta fase. Baseline obrigatório antes da Fase 2:

```text
pytest
ruff check .
ruff format --check .
mypy apps/ config/ --ignore-missing-imports
```

## Reutilização, modificações e módulos novos

Reutilizar: auth, tenancy, criptografia, social/OAuth, providers, Post/
PlatformPost/PostVersion, approvals, calendário/queues, Publisher, MediaAsset,
analytics snapshots, API keys, quotas, idempotência, auditoria, MCP/OAuth e
deploy.

Modificar incrementalmente:

- `apps.composer`: FKs opcionais Brand/plano/campanha/geração, origem/archive;
- `apps.members`: permissões/presets sem remover papéis;
- `apps.analytics`: derivados sobre snapshots;
- `apps.media_library`: integração de generated assets via services;
- `apps.api`, `apps.mcp`: adapters compartilhados;
- `apps.notifications`: eventos de geração/review/recomendação;
- `apps.settings_manager`: defaults de IA/policies quando apropriado.

Novos módulos:

- `apps.brands`: `BrandProfile`, `BrandPersona`, `ContentPillar`,
  `EditorialStrategy`, `EditorialStrategyVersion`;
- `apps.content_intelligence`: `ContentPlan`, `ContentPlanItem`,
  `GenerationRequest`, `GeneratedContent`, `VisualBrief`, scores, insights,
  recommendations, `AutomationPolicy`, decision log e adapters de IA.

Usar relações para entidades filtráveis e JSON para listas flexíveis. Impor
tenant consistente e percentuais Reach/Authority/Conversion somando 100.

## Impacto no banco

Somente migrations aditivas: tabelas, FKs opcionais e índices; sem remoção,
rename destrutivo ou dados obrigatórios. Índices por org/workspace/status/data.
O seed não pode adivinhar tenant: command idempotente
`seed_nexus_wellness --workspace <id>`.

## Dependências OAuth

Nenhuma nova biblioteca OAuth é necessária para LinkedIn/Instagram. Preservar
app credentials, redirect URIs, scopes, PKCE/state, tokens criptografados,
refresh/reconexão. Scopes extras de analytics dependem de aprovação externa e
devem degradar explicitamente. OAuth MCP permanece separado dos tokens sociais.

## Riscos

1. Vazamento entre tenants em queries/jobs/API/MCP.
2. Colisão com `apps.intelligence`.
3. Escalada gerar → aprovar → agendar → publicar.
4. Policy automática permissiva/não versionada.
5. Prompt injection e vazamento de dados a LLMs.
6. Secrets/prompts em logs ou retenção indevida.
7. SSRF via Ollama/URLs de mídia.
8. Worker bloqueado por chamadas longas.
9. Scores enviesados ou ausência tratada como zero.
10. Duplicidade/custo sem idempotência/quota.
11. Obrigações AGPL-3.0.

## Roadmap incremental proposto

1. Baseline: dependências, testes/lint/typecheck e ADRs.
2. Brand Profile: models/services/admin/UI/RBAC/isolamento.
3. Estratégia: pilares, versões 35/50/15 e planos sem LLM.
4. AI Agent: adapters, jobs, quotas e geração só para draft.
5. Visual Brief e registro seguro de assets.
6. Library: filtros, campaign, origem e arquivamento.
7. Manual/semi/automatic com policy/log; automatic off.
8. Regressão oficial LinkedIn/Instagram.
9. Scores/insights explicáveis.
10. Learning loop com aceite/rejeição humana.
11. Novos presets preservando memberships.
12. REST/MCP para Brand, planos, geração, brief, aprovação/sugestões.
13. Seed NEXUS por command idempotente.
14. E2E, concorrência, falhas, observabilidade, backup/deploy.

## Decisões antes da Fase 2

- Brand pertence a um workspace (recomendado) ou é compartilhada?
- Manter papéis antigos e adicionar novos como presets (recomendado)?
- Aprovar o namespace `content_intelligence`?
- Confirmar Automatic off e dependente de policy versionada?
- Aprovar seed parametrizado por workspace?

