-- รันใน Supabase → SQL Editor (ครั้งเดียว)
create table public.profiles (
  user_id       uuid primary key references auth.users(id) on delete cascade,
  display_name  text   check (char_length(display_name) <= 60),
  desired_title text   check (char_length(desired_title) <= 100),
  categories    text[] not null default '{}' check (cardinality(categories) <= 20),
  work_types    text[] not null default '{}' check (cardinality(work_types) <= 3),
  consent_at    timestamptz,
  updated_at    timestamptz not null default now()
);

alter table public.profiles enable row level security;  -- ห้ามข้าม: ถ้าไม่เปิด ใครก็อ่านโปรไฟล์ทุกคนได้

create policy "read own"   on public.profiles for select using (auth.uid() = user_id);
create policy "insert own" on public.profiles for insert with check (auth.uid() = user_id);
create policy "update own" on public.profiles for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "delete own" on public.profiles for delete using (auth.uid() = user_id);
