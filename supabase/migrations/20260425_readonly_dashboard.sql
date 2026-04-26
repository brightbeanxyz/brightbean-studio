create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  full_name text,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1)),
    new.raw_user_meta_data ->> 'avatar_url'
  )
  on conflict (id) do update
  set
    email = excluded.email,
    full_name = coalesce(excluded.full_name, public.profiles.full_name),
    avatar_url = coalesce(excluded.avatar_url, public.profiles.avatar_url),
    updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  owner_user_id uuid not null references auth.users (id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.workspace_members (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null default 'owner' check (role in ('owner', 'manager', 'editor', 'viewer')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, user_id)
);

create table if not exists public.channel_groups (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  name text not null,
  description text not null default '',
  position integer not null default 0,
  is_favorite boolean not null default false,
  is_archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.social_accounts (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  channel_group_id uuid references public.channel_groups (id) on delete set null,
  connected_by uuid references auth.users (id) on delete set null,
  platform text not null check (platform in ('facebook', 'youtube', 'tiktok')),
  account_platform_id text not null,
  account_name text not null,
  account_handle text not null default '',
  avatar_url text not null default '',
  follower_count bigint not null default 0,
  connection_status text not null default 'connected' check (connection_status in ('connected', 'warning', 'error', 'disconnected')),
  last_error text not null default '',
  last_health_check_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, platform, account_platform_id)
);

create table if not exists public.social_account_tokens (
  social_account_id uuid primary key references public.social_accounts (id) on delete cascade,
  access_token text not null,
  refresh_token text not null default '',
  token_expires_at timestamptz,
  scope text not null default '',
  token_metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.daily_channel_metrics (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  social_account_id uuid not null references public.social_accounts (id) on delete cascade,
  metric_date date not null,
  followers bigint not null default 0,
  followers_gained bigint not null default 0,
  reach bigint not null default 0,
  impressions bigint not null default 0,
  engagement bigint not null default 0,
  video_views bigint not null default 0,
  watch_time_seconds bigint not null default 0,
  comments bigint not null default 0,
  shares bigint not null default 0,
  saves bigint not null default 0,
  raw jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (social_account_id, metric_date)
);

create table if not exists public.content_snapshots (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  social_account_id uuid not null references public.social_accounts (id) on delete cascade,
  platform_content_id text not null,
  title text not null default '',
  caption text not null default '',
  content_type text not null default 'post',
  thumbnail_url text not null default '',
  permalink text not null default '',
  published_at timestamptz,
  snapshot_date date not null default current_date,
  reach bigint not null default 0,
  engagement bigint not null default 0,
  comments bigint not null default 0,
  shares bigint not null default 0,
  saves bigint not null default 0,
  followers_gained bigint not null default 0,
  performance_score integer not null default 0,
  video_views bigint not null default 0,
  watch_time_seconds bigint not null default 0,
  raw jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (social_account_id, platform_content_id)
);

create table if not exists public.inbox_messages (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  social_account_id uuid not null references public.social_accounts (id) on delete cascade,
  platform_message_id text not null,
  platform text not null,
  message_type text not null default 'comment',
  sender_name text not null default '',
  sender_handle text not null default '',
  sender_avatar_url text not null default '',
  body text not null default '',
  status text not null default 'unread',
  sentiment text not null default 'neutral',
  received_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (social_account_id, platform_message_id)
);

create table if not exists public.user_settings (
  user_id uuid primary key references auth.users (id) on delete cascade,
  email_notifications boolean not null default true,
  push_notifications boolean not null default true,
  alert_notifications boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_workspace_members_user_id on public.workspace_members (user_id);
create index if not exists idx_channel_groups_workspace_id on public.channel_groups (workspace_id);
create index if not exists idx_social_accounts_workspace_id on public.social_accounts (workspace_id);
create index if not exists idx_daily_channel_metrics_workspace_date on public.daily_channel_metrics (workspace_id, metric_date desc);
create index if not exists idx_content_snapshots_workspace_published on public.content_snapshots (workspace_id, published_at desc);
create index if not exists idx_inbox_messages_workspace_received on public.inbox_messages (workspace_id, received_at desc);

drop trigger if exists touch_workspaces_updated_at on public.workspaces;
create trigger touch_workspaces_updated_at before update on public.workspaces for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_workspace_members_updated_at on public.workspace_members;
create trigger touch_workspace_members_updated_at before update on public.workspace_members for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_channel_groups_updated_at on public.channel_groups;
create trigger touch_channel_groups_updated_at before update on public.channel_groups for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_social_accounts_updated_at on public.social_accounts;
create trigger touch_social_accounts_updated_at before update on public.social_accounts for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_daily_channel_metrics_updated_at on public.daily_channel_metrics;
create trigger touch_daily_channel_metrics_updated_at before update on public.daily_channel_metrics for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_content_snapshots_updated_at on public.content_snapshots;
create trigger touch_content_snapshots_updated_at before update on public.content_snapshots for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_inbox_messages_updated_at on public.inbox_messages;
create trigger touch_inbox_messages_updated_at before update on public.inbox_messages for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_user_settings_updated_at on public.user_settings;
create trigger touch_user_settings_updated_at before update on public.user_settings for each row execute procedure public.touch_updated_at();
drop trigger if exists touch_profiles_updated_at on public.profiles;
create trigger touch_profiles_updated_at before update on public.profiles for each row execute procedure public.touch_updated_at();

alter table public.profiles enable row level security;
alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;
alter table public.channel_groups enable row level security;
alter table public.social_accounts enable row level security;
alter table public.social_account_tokens enable row level security;
alter table public.daily_channel_metrics enable row level security;
alter table public.content_snapshots enable row level security;
alter table public.inbox_messages enable row level security;
alter table public.user_settings enable row level security;

create policy "profiles_select_own" on public.profiles
for select to authenticated
using (auth.uid() = id);

create policy "profiles_update_own" on public.profiles
for update to authenticated
using (auth.uid() = id)
with check (auth.uid() = id);

create policy "workspaces_member_select" on public.workspaces
for select to authenticated
using (
  exists (
    select 1
    from public.workspace_members wm
    where wm.workspace_id = workspaces.id
      and wm.user_id = auth.uid()
  )
);

create policy "workspace_members_member_select" on public.workspace_members
for select to authenticated
using (
  exists (
    select 1
    from public.workspace_members wm
    where wm.workspace_id = workspace_members.workspace_id
      and wm.user_id = auth.uid()
  )
);

create policy "channel_groups_member_select" on public.channel_groups
for select to authenticated
using (
  exists (
    select 1
    from public.workspace_members wm
    where wm.workspace_id = channel_groups.workspace_id
      and wm.user_id = auth.uid()
  )
);

create policy "social_accounts_member_select" on public.social_accounts
for select to authenticated
using (
  exists (
    select 1
    from public.workspace_members wm
    where wm.workspace_id = social_accounts.workspace_id
      and wm.user_id = auth.uid()
  )
);

create policy "social_account_tokens_member_select" on public.social_account_tokens
for select to authenticated
using (
  exists (
    select 1
    from public.social_accounts sa
    join public.workspace_members wm on wm.workspace_id = sa.workspace_id
    where sa.id = social_account_tokens.social_account_id
      and wm.user_id = auth.uid()
  )
);

create policy "daily_channel_metrics_member_select" on public.daily_channel_metrics
for select to authenticated
using (
  exists (
    select 1
    from public.workspace_members wm
    where wm.workspace_id = daily_channel_metrics.workspace_id
      and wm.user_id = auth.uid()
  )
);

create policy "content_snapshots_member_select" on public.content_snapshots
for select to authenticated
using (
  exists (
    select 1
    from public.workspace_members wm
    where wm.workspace_id = content_snapshots.workspace_id
      and wm.user_id = auth.uid()
  )
);

create policy "inbox_messages_member_select" on public.inbox_messages
for select to authenticated
using (
  exists (
    select 1
    from public.workspace_members wm
    where wm.workspace_id = inbox_messages.workspace_id
      and wm.user_id = auth.uid()
  )
);

create policy "user_settings_select_own" on public.user_settings
for select to authenticated
using (auth.uid() = user_id);

create policy "user_settings_update_own" on public.user_settings
for update to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
