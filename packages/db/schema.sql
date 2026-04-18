-- padel-atlas-de database schema
-- Target: Supabase (Postgres 15) with PostGIS extension
-- Run this in Supabase SQL Editor after creating the project.

create extension if not exists postgis;
create extension if not exists pgcrypto;

create table if not exists operators (
    id uuid primary key default gen_random_uuid(),
    name text not null unique,
    website text,
    created_at timestamptz not null default now()
);

create table if not exists courts (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    address text,
    city text,
    postal_code text,
    country text not null default 'DE',
    lat double precision not null,
    lng double precision not null,
    location geography(point, 4326) generated always as (st_setsrid(st_makepoint(lng, lat), 4326)::geography) stored,
    court_count integer,
    indoor boolean,
    outdoor boolean,
    operator_id uuid references operators(id) on delete set null,
    booking_url text,
    confidence numeric(3,2) not null default 0.50 check (confidence >= 0 and confidence <= 1),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists courts_location_idx on courts using gist(location);
create index if not exists courts_city_idx on courts(city);
create index if not exists courts_operator_idx on courts(operator_id);

create table if not exists sources (
    id uuid primary key default gen_random_uuid(),
    court_id uuid not null references courts(id) on delete cascade,
    source_type text not null check (source_type in ('osm', 'google_places', 'playtomic', 'matchi', 'dpv', 'padel_atlas', 'manual')),
    source_url text,
    source_ref text,
    raw_data jsonb,
    fetched_at timestamptz not null default now()
);

create unique index if not exists sources_unique_ref
    on sources(source_type, source_ref) where source_ref is not null;
create index if not exists sources_court_idx on sources(court_id);

create or replace function touch_updated_at() returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists courts_touch_updated_at on courts;
create trigger courts_touch_updated_at
    before update on courts
    for each row execute function touch_updated_at();
