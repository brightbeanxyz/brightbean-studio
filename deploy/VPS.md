# Deploy em VPS

## Requisitos

Ubuntu 22.04+, Docker Engine e Docker Compose plugin. Aponte um domínio para o IP da VPS e abra somente as portas 22, 80 e 443.

## Primeiro deploy

```bash
git clone <URL_DO_REPOSITORIO> social-content-ai
cd social-content-ai
cp .env.production.example .env
chmod 600 .env
# edite .env e substitua todos os valores replace-*
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

O serviço `migrate` aplica o schema antes de liberar `app` e `worker`. O worker `process_tasks` mantém publicação, lembretes e tarefas recorrentes ativos continuamente.

## Operação

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f app worker
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec postgres pg_dump -U postgres brightbean > backup-$(date +%F).sql
```

O PostgreSQL não é exposto publicamente no perfil de produção. O Caddy termina TLS automaticamente para `APP_DOMAIN`; atualize o domínio no `.env` antes do primeiro deploy.
