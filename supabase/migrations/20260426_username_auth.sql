alter table public.profiles
add column if not exists username text;

update public.profiles
set username = lower(regexp_replace(coalesce(nullif(username, ''), split_part(coalesce(email, 'user'), '@', 1)), '[^a-zA-Z0-9_]+', '_', 'g'))
where username is null or username = '';

create unique index if not exists profiles_username_lower_unique
on public.profiles (lower(username))
where username is not null and username <> '';

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  next_username text;
begin
  next_username := lower(
    regexp_replace(
      coalesce(
        nullif(new.raw_user_meta_data ->> 'username', ''),
        split_part(new.email, '@', 1)
      ),
      '[^a-zA-Z0-9_]+',
      '_',
      'g'
    )
  );

  insert into public.profiles (id, email, full_name, avatar_url, username)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1)),
    new.raw_user_meta_data ->> 'avatar_url',
    next_username
  )
  on conflict (id) do update
  set
    email = excluded.email,
    full_name = coalesce(excluded.full_name, public.profiles.full_name),
    avatar_url = coalesce(excluded.avatar_url, public.profiles.avatar_url),
    username = coalesce(nullif(excluded.username, ''), public.profiles.username),
    updated_at = now();
  return new;
end;
$$;
