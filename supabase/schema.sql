-- 「삶」 — 매일의 단상
-- 적용: Supabase 대시보드 SQL Editor 또는 MCP apply_migration

-- ── 관리자 이메일 ────────────────────────────────────────
-- 로그인 매직링크를 받을 주소. 이 값 하나가 쓰기 권한 전체를 결정한다.
-- 바꾸려면 아래 함수의 반환값만 수정하면 된다.
create or replace function public.admin_email()
returns text language sql immutable as $$
  select 'aprilleaf@gmail.com'
$$;

-- ── 테이블 ───────────────────────────────────────────────
create table if not exists public.life_entries (
  id          uuid primary key default gen_random_uuid(),
  written_on  date        not null default current_date,
  body        text        not null,
  published   boolean     not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index if not exists life_entries_written_on_idx
  on public.life_entries (written_on desc, created_at desc);

-- updated_at 자동 갱신
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists life_entries_touch on public.life_entries;
create trigger life_entries_touch
  before update on public.life_entries
  for each row execute function public.touch_updated_at();

-- ── 보안 (RLS) ───────────────────────────────────────────
-- 저장소가 공개이고 publishable key도 공개되므로, 방어선은 전적으로 여기다.
alter table public.life_entries enable row level security;

drop policy if exists "anyone reads published"  on public.life_entries;
drop policy if exists "admin reads all"         on public.life_entries;
drop policy if exists "admin inserts"           on public.life_entries;
drop policy if exists "admin updates"           on public.life_entries;
drop policy if exists "admin deletes"           on public.life_entries;

-- 공개된 글은 누구나 읽는다
create policy "anyone reads published"
  on public.life_entries for select
  to anon, authenticated
  using (published = true);

-- 관리자는 미공개 초안까지 읽는다
create policy "admin reads all"
  on public.life_entries for select
  to authenticated
  using ((auth.jwt() ->> 'email') = public.admin_email());

-- 쓰기는 관리자만
create policy "admin inserts"
  on public.life_entries for insert
  to authenticated
  with check ((auth.jwt() ->> 'email') = public.admin_email());

create policy "admin updates"
  on public.life_entries for update
  to authenticated
  using      ((auth.jwt() ->> 'email') = public.admin_email())
  with check ((auth.jwt() ->> 'email') = public.admin_email());

create policy "admin deletes"
  on public.life_entries for delete
  to authenticated
  using ((auth.jwt() ->> 'email') = public.admin_email());
