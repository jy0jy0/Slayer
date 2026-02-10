-- user_google_tokens: Google OAuth token 저장 테이블
create table if not exists public.user_google_tokens (
  user_id uuid primary key references auth.users(id) on delete cascade,
  access_token text not null,
  refresh_token text,
  token_expires_at timestamptz not null,
  scopes text not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- RLS 활성화
alter table public.user_google_tokens enable row level security;

-- 본인 row만 조회 가능
create policy "Users can view own tokens"
  on public.user_google_tokens for select
  using (auth.uid() = user_id);

-- 본인 row만 삽입 가능
create policy "Users can insert own tokens"
  on public.user_google_tokens for insert
  with check (auth.uid() = user_id);

-- 본인 row만 수정 가능
create policy "Users can update own tokens"
  on public.user_google_tokens for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- updated_at 자동 갱신 트리거
create or replace function public.handle_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger on_user_google_tokens_updated
  before update on public.user_google_tokens
  for each row execute function public.handle_updated_at();
