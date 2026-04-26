create extension if not exists pg_cron;
create extension if not exists pg_net;

create schema if not exists private;

create table if not exists private.app_secrets (
  name text primary key,
  secret text not null,
  updated_at timestamptz not null default now()
);

create or replace function private.read_secret(secret_name text)
returns text
language plpgsql
security definer
set search_path = public, private
as $$
declare
  secret_value text;
begin
  begin
    execute $query$
      select decrypted_secret
      from vault.decrypted_secrets
      where name = $1
      order by created_at desc
      limit 1
    $query$
    into secret_value
    using secret_name;
  exception
    when invalid_schema_name or undefined_table then
      secret_value := null;
  end;

  if secret_value is null or secret_value = '' then
    select secret
    into secret_value
    from private.app_secrets
    where name = secret_name
    limit 1;
  end if;

  return secret_value;
end;
$$;

create or replace function private.invoke_netlify_sync_all()
returns bigint
language plpgsql
security definer
set search_path = public, private
as $$
declare
  request_id bigint;
  app_url text;
  cron_secret text;
begin
  select private.read_secret('netlify_app_url')
  into app_url;

  select private.read_secret('netlify_cron_secret')
  into cron_secret;

  if app_url is null or app_url = '' then
    raise exception 'Secret netlify_app_url is missing';
  end if;

  if cron_secret is null or cron_secret = '' then
    raise exception 'Secret netlify_cron_secret is missing';
  end if;

  select net.http_post(
    url := rtrim(app_url, '/') || '/api/cron/sync-all',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Cron-Secret', cron_secret
    ),
    body := jsonb_build_object(
      'source', 'supabase-cron',
      'triggered_at', now()
    )
  )
  into request_id;

  return request_id;
end;
$$;

do $$
declare
  existing_job_id bigint;
begin
  select jobid
  into existing_job_id
  from cron.job
  where jobname = 'netlify-sync-all-every-30-minutes'
  limit 1;

  if existing_job_id is not null then
    perform cron.unschedule(existing_job_id);
  end if;
end;
$$;

select cron.schedule(
  'netlify-sync-all-every-30-minutes',
  '*/30 * * * *',
  $$select private.invoke_netlify_sync_all();$$
);
