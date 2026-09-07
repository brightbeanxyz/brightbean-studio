# Social Content AI — acompanhamento

Atualizado em 2026-09-07. Base: `72009cd` e alterações locais descritas abaixo.
Este documento registra o estado atual; a auditoria arquitetural original permanece
como registro histórico da Fase 1.

## Implementado no código

| Área | Evidência |
| --- | --- |
| Perfis de marca por workspace | `6b5919c`, `apps.brands` |
| Estratégia versionada e planos editoriais | `50a1714` |
| Geração de texto e conversão em rascunhos | `9632697`, `c932fcb` |
| Geração de imagem e visual brief | `e77be84` |
| Biblioteca, campanhas e filtros | `311fae0`, `1778f65` |
| Item de plano convertido em rascunho | `7d7fa08` |
| Agendamento pelo calendário | `fbc9e5e` |
| Scripts de implantação, backup e acesso interno | `93dce49` a `72009cd` |

Presença no código não implica validação completa de integrações externas.

## Correção validada, aguardando implantação

O agendamento pelo plano passou a chamar a mesma proteção de aprovação do
Composer antes de criar rascunhos ou alterar estados de publicação. Workspaces
com `required_internal` ou `required_internal_and_client` devem seguir o fluxo
de aprovação; possuir `publish_directly` não dispensa essa exigência.

- Regressão reproduzida antes da correção.
- SQLite: 20 testes de agendamento, biblioteca e planos passaram.
- PostgreSQL 16.15: a primeira execução apresentou 4 falhas e 16 testes passando.
  As falhas vieram de `FOR UPDATE` sobre relações opcionais nas consultas de
  criação e agendamento de rascunhos. As duas consultas agora usam
  `select_for_update(of=("self",))`, preservando o bloqueio do item do plano.
- PostgreSQL após a correção: 20 testes passaram em 40,59 segundos, em Linux,
  Python 3.12.14 e Django 5.1.15, usando o código local em containers temporários.
  Os containers foram removidos ao final. O banco de produção não foi utilizado.
- Lint do novo arquivo de testes, formatação e `git diff --check`: passaram.
- Produção: esta correção ainda não foi implantada.

Escopo executado com `DJANGO_SETTINGS_MODULE=config.settings.test` e variáveis
`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` apontando para PostgreSQL isolado:

```text
python -m pytest -p no:cacheprovider apps/content_intelligence/tests/test_plan_scheduling.py apps/content_intelligence/tests/test_library.py apps/content_intelligence/tests/test_editorial_plans.py
```

Essa validação cobre aprovação, permissões, criação de rascunhos, planos e
biblioteca. Não é um teste de publicação real em redes sociais nem um teste de
concorrência entre múltiplos workers.

## Próxima etapa: modos de operação

Ainda não existem `AutomationPolicy` ou registro de decisões no novo domínio.
O modo de aprovação do workspace é uma configuração existente e não deve ser
confundido com os novos modos de operação.

1. Manual: aprovação humana obrigatória; agendamento acionado por pessoa.
2. Semiautomático: aprovação em lote; seleção de slots somente após todas as
   aprovações exigidas, inclusive a do cliente quando aplicável.
3. Automático: política ativa, versionada, por workspace, com decisão auditável.
   Deve nascer desabilitado e não habilitar publicação por efeito de geração.

A primeira entrega dessa etapa deve estabelecer política, versões imutáveis,
permissões e histórico de decisões. A integração com jobs de agendamento vem
depois, reutilizando aprovações e serviços existentes.

## Pendências posteriores do roadmap

- Scores derivados, insights e recomendações explicáveis sobre analytics.
- Learning loop com aceite ou rejeição humana.
- Novos presets de permissões e adapters REST/MCP do domínio editorial.
- Seed NEXUS parametrizado por workspace.
- Regressão das integrações oficiais, concorrência e observabilidade.

## Alterações locais preexistentes

`requirements.txt` (Redis), atalhos/túnel PowerShell e certificado local em
`deploy/` já estavam alterados ou sem commit antes desta correção. Não fazem
parte da correção de aprovação.
