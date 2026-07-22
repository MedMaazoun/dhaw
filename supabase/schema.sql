-- Dhaw ضو — table des signalements citoyens
-- À coller dans Supabase → SQL Editor → Run

create table if not exists public.reports (
  id         bigint generated always as identity primary key,
  deleg_id   text not null check (char_length(deleg_id) <= 8),
  kind       text not null check (kind in ('out', 'back')),
  created_at timestamptz not null default now()
);

create index if not exists reports_created_idx on public.reports (created_at desc);

alter table public.reports enable row level security;

-- lecture publique (clé anon)
create policy "lecture publique"
  on public.reports for select
  to anon using (true);

-- insertion publique contrôlée (clé anon)
create policy "signalement public"
  on public.reports for insert
  to anon with check (kind in ('out','back') and char_length(deleg_id) <= 8);

-- Nettoyage automatique (> 48 h) : Database → Cron Jobs (extension pg_cron) :
--   select cron.schedule('purge-reports', '0 * * * *',
--     $$delete from public.reports where created_at < now() - interval '48 hours'$$);
