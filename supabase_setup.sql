-- Setup relacional para persistência do app no Supabase
-- Cria tabelas normalizadas (relacionais) para permitir outras interfaces além do Streamlit.

-- UUID
create extension if not exists pgcrypto;

-- updated_at automático
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- =====================
-- USUÁRIOS
-- =====================
create table if not exists public.usuarios (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  nome text not null,
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Garante defaults mesmo se a tabela já existia
alter table public.usuarios alter column created_at set default now();
alter table public.usuarios alter column updated_at set default now();
alter table public.usuarios alter column created_at set not null;
alter table public.usuarios alter column updated_at set not null;

drop trigger if exists trg_usuarios_updated_at on public.usuarios;
create trigger trg_usuarios_updated_at
before update on public.usuarios
for each row execute function public.set_updated_at();

-- =====================
-- CATEGORIAS
-- =====================
create table if not exists public.categorias (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.usuarios(id) on delete cascade,
  nome text not null,
  tipo text not null check (tipo in ('receita','despesa')),
  icone text,
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.categorias alter column created_at set default now();
alter table public.categorias alter column updated_at set default now();
alter table public.categorias alter column created_at set not null;
alter table public.categorias alter column updated_at set not null;
create index if not exists idx_categorias_user_id on public.categorias(user_id);
create index if not exists idx_categorias_user_tipo on public.categorias(user_id, tipo);

drop trigger if exists trg_categorias_updated_at on public.categorias;
create trigger trg_categorias_updated_at
before update on public.categorias
for each row execute function public.set_updated_at();

-- =====================
-- CONTAS
-- =====================
create table if not exists public.contas (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.usuarios(id) on delete cascade,
  nome text not null,
  tipo text not null check (tipo in ('banco','carteira','cartao_credito')),
  saldo_inicial numeric not null default 0,
  data_saldo_inicial date,
  dia_fechamento int,
  dia_vencimento int,
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.contas alter column created_at set default now();
alter table public.contas alter column updated_at set default now();
alter table public.contas alter column created_at set not null;
alter table public.contas alter column updated_at set not null;
create index if not exists idx_contas_user_id on public.contas(user_id);

drop trigger if exists trg_contas_updated_at on public.contas;
create trigger trg_contas_updated_at
before update on public.contas
for each row execute function public.set_updated_at();

-- =====================
-- RECORRENTES
-- =====================
create table if not exists public.transacoes_recorrentes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.usuarios(id) on delete cascade,
  conta_id uuid references public.contas(id) on delete set null,
  categoria_id uuid references public.categorias(id) on delete set null,
  descricao text not null,
  valor numeric not null default 0,
  tipo text not null check (tipo in ('receita','despesa')),
  dia_do_mes int not null check (dia_do_mes between 1 and 31),
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.transacoes_recorrentes alter column created_at set default now();
alter table public.transacoes_recorrentes alter column updated_at set default now();
alter table public.transacoes_recorrentes alter column created_at set not null;
alter table public.transacoes_recorrentes alter column updated_at set not null;
create index if not exists idx_recorrentes_user_id on public.transacoes_recorrentes(user_id);

drop trigger if exists trg_recorrentes_updated_at on public.transacoes_recorrentes;
create trigger trg_recorrentes_updated_at
before update on public.transacoes_recorrentes
for each row execute function public.set_updated_at();

-- =====================
-- TRANSAÇÕES
-- =====================
create table if not exists public.transacoes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.usuarios(id) on delete cascade,
  conta_id uuid references public.contas(id) on delete set null,
  categoria_id uuid references public.categorias(id) on delete set null,
  descricao text not null,
  valor numeric not null default 0,
  tipo text not null check (tipo in ('receita','despesa')),
  data date not null,
  status text not null default 'realizada' check (status in ('realizada','prevista','substituida')),
  modo_lancamento text not null default 'manual',
  recorrente_id uuid references public.transacoes_recorrentes(id) on delete set null,
  transacao_prevista_id uuid references public.transacoes(id) on delete set null,
  observacao text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.transacoes alter column created_at set default now();
alter table public.transacoes alter column updated_at set default now();
alter table public.transacoes alter column created_at set not null;
alter table public.transacoes alter column updated_at set not null;
create index if not exists idx_transacoes_user_data on public.transacoes(user_id, data desc);
create index if not exists idx_transacoes_user_tipo on public.transacoes(user_id, tipo);
create index if not exists idx_transacoes_user_categoria on public.transacoes(user_id, categoria_id);
create index if not exists idx_transacoes_user_conta on public.transacoes(user_id, conta_id);

drop trigger if exists trg_transacoes_updated_at on public.transacoes;
create trigger trg_transacoes_updated_at
before update on public.transacoes
for each row execute function public.set_updated_at();

-- =====================
-- ORÇAMENTOS
-- =====================
create table if not exists public.orcamentos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.usuarios(id) on delete cascade,
  categoria_id uuid not null references public.categorias(id) on delete cascade,
  valor_limite numeric not null default 0,
  periodo text not null default 'mensal',
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, categoria_id)
);

alter table public.orcamentos alter column created_at set default now();
alter table public.orcamentos alter column updated_at set default now();
alter table public.orcamentos alter column created_at set not null;
alter table public.orcamentos alter column updated_at set not null;
create index if not exists idx_orcamentos_user_id on public.orcamentos(user_id);

drop trigger if exists trg_orcamentos_updated_at on public.orcamentos;
create trigger trg_orcamentos_updated_at
before update on public.orcamentos
for each row execute function public.set_updated_at();

-- =====================
-- INVESTIMENTOS
-- =====================
create table if not exists public.investimentos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.usuarios(id) on delete cascade,
  nome text not null,
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.investimentos alter column created_at set default now();
alter table public.investimentos alter column updated_at set default now();
alter table public.investimentos alter column created_at set not null;
alter table public.investimentos alter column updated_at set not null;
create index if not exists idx_investimentos_user_id on public.investimentos(user_id);

drop trigger if exists trg_investimentos_updated_at on public.investimentos;
create trigger trg_investimentos_updated_at
before update on public.investimentos
for each row execute function public.set_updated_at();

-- =====================
-- SALDOS DE INVESTIMENTOS
-- =====================
create table if not exists public.investimentos_saldos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.usuarios(id) on delete cascade,
  investimento_id uuid not null references public.investimentos(id) on delete cascade,
  data_referencia date not null,
  data_conhecido_em date,
  saldo numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, investimento_id, data_referencia)
);

alter table public.investimentos_saldos alter column created_at set default now();
alter table public.investimentos_saldos alter column updated_at set default now();
alter table public.investimentos_saldos alter column created_at set not null;
alter table public.investimentos_saldos alter column updated_at set not null;
create index if not exists idx_investimentos_saldos_user_id on public.investimentos_saldos(user_id);
create index if not exists idx_investimentos_saldos_inv_data on public.investimentos_saldos(investimento_id, data_referencia);

drop trigger if exists trg_investimentos_saldos_updated_at on public.investimentos_saldos;
create trigger trg_investimentos_saldos_updated_at
before update on public.investimentos_saldos
for each row execute function public.set_updated_at();

-- =====================
-- RLS (opcional)
-- =====================
-- Recomendado: habilitar RLS para permitir uso com SUPABASE_ANON_KEY + Supabase Auth.

-- Permissões básicas (ajuste conforme sua política)
grant usage on schema public to anon, authenticated;
grant select, insert, update, delete on all tables in schema public to authenticated;

-- Usuários (perfil)
alter table public.usuarios enable row level security;
drop policy if exists usuarios_select_own on public.usuarios;
create policy usuarios_select_own on public.usuarios
  for select
  to authenticated
  using (auth.uid() = id);

drop policy if exists usuarios_upsert_own on public.usuarios;
create policy usuarios_upsert_own on public.usuarios
  for insert
  to authenticated
  with check (auth.uid() = id);

drop policy if exists usuarios_update_own on public.usuarios;
create policy usuarios_update_own on public.usuarios
  for update
  to authenticated
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- Helper para tabelas com user_id
-- (categorias, contas, recorrentes, transacoes, orcamentos, investimentos, investimentos_saldos)

alter table public.categorias enable row level security;
drop policy if exists categorias_select_own on public.categorias;
create policy categorias_select_own on public.categorias for select to authenticated using (auth.uid() = user_id);
drop policy if exists categorias_insert_own on public.categorias;
create policy categorias_insert_own on public.categorias for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists categorias_update_own on public.categorias;
create policy categorias_update_own on public.categorias for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists categorias_delete_own on public.categorias;
create policy categorias_delete_own on public.categorias for delete to authenticated using (auth.uid() = user_id);

alter table public.contas enable row level security;
drop policy if exists contas_select_own on public.contas;
create policy contas_select_own on public.contas for select to authenticated using (auth.uid() = user_id);
drop policy if exists contas_insert_own on public.contas;
create policy contas_insert_own on public.contas for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists contas_update_own on public.contas;
create policy contas_update_own on public.contas for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists contas_delete_own on public.contas;
create policy contas_delete_own on public.contas for delete to authenticated using (auth.uid() = user_id);

alter table public.transacoes_recorrentes enable row level security;
drop policy if exists recorrentes_select_own on public.transacoes_recorrentes;
create policy recorrentes_select_own on public.transacoes_recorrentes for select to authenticated using (auth.uid() = user_id);
drop policy if exists recorrentes_insert_own on public.transacoes_recorrentes;
create policy recorrentes_insert_own on public.transacoes_recorrentes for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists recorrentes_update_own on public.transacoes_recorrentes;
create policy recorrentes_update_own on public.transacoes_recorrentes for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists recorrentes_delete_own on public.transacoes_recorrentes;
create policy recorrentes_delete_own on public.transacoes_recorrentes for delete to authenticated using (auth.uid() = user_id);

alter table public.transacoes enable row level security;
drop policy if exists transacoes_select_own on public.transacoes;
create policy transacoes_select_own on public.transacoes for select to authenticated using (auth.uid() = user_id);
drop policy if exists transacoes_insert_own on public.transacoes;
create policy transacoes_insert_own on public.transacoes for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists transacoes_update_own on public.transacoes;
create policy transacoes_update_own on public.transacoes for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists transacoes_delete_own on public.transacoes;
create policy transacoes_delete_own on public.transacoes for delete to authenticated using (auth.uid() = user_id);

alter table public.orcamentos enable row level security;
drop policy if exists orcamentos_select_own on public.orcamentos;
create policy orcamentos_select_own on public.orcamentos for select to authenticated using (auth.uid() = user_id);
drop policy if exists orcamentos_insert_own on public.orcamentos;
create policy orcamentos_insert_own on public.orcamentos for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists orcamentos_update_own on public.orcamentos;
create policy orcamentos_update_own on public.orcamentos for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists orcamentos_delete_own on public.orcamentos;
create policy orcamentos_delete_own on public.orcamentos for delete to authenticated using (auth.uid() = user_id);

alter table public.investimentos enable row level security;
drop policy if exists investimentos_select_own on public.investimentos;
create policy investimentos_select_own on public.investimentos for select to authenticated using (auth.uid() = user_id);
drop policy if exists investimentos_insert_own on public.investimentos;
create policy investimentos_insert_own on public.investimentos for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists investimentos_update_own on public.investimentos;
create policy investimentos_update_own on public.investimentos for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists investimentos_delete_own on public.investimentos;
create policy investimentos_delete_own on public.investimentos for delete to authenticated using (auth.uid() = user_id);

alter table public.investimentos_saldos enable row level security;
drop policy if exists investimentos_saldos_select_own on public.investimentos_saldos;
create policy investimentos_saldos_select_own on public.investimentos_saldos for select to authenticated using (auth.uid() = user_id);
drop policy if exists investimentos_saldos_insert_own on public.investimentos_saldos;
create policy investimentos_saldos_insert_own on public.investimentos_saldos for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists investimentos_saldos_update_own on public.investimentos_saldos;
create policy investimentos_saldos_update_own on public.investimentos_saldos for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists investimentos_saldos_delete_own on public.investimentos_saldos;
create policy investimentos_saldos_delete_own on public.investimentos_saldos for delete to authenticated using (auth.uid() = user_id);
