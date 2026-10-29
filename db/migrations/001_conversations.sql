-- AutoLab conversations (interface.md 13). Schema "autolab": not exposed by Supabase's public REST API (only
-- "public" is), so only the AutoLab server, connected with the database password, reads and writes these tables.
-- Large files (3D structures, MD animations) stay on the Modal volume; their references are stored here.

create schema if not exists autolab;

create table if not exists autolab.conversations (
    id                  text primary key,
    title               text not null,
    goal                text not null,
    domain              text,
    status              text not null check (status in ('answered', 'queued', 'running', 'stopping', 'done',
                                                        'interrupted', 'error')),
    scope               jsonb,            -- classification of the request (intent, status, constraints)
    error               text,
    source              text not null default 'live',  -- 'live', or 'imported:<results folder>'
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    cancel_requested_at timestamptz,
    deleted_at          timestamptz       -- soft delete: the computation caches are kept anyway
);
create index if not exists conversations_recent on autolab.conversations (updated_at desc) where deleted_at is null;

create table if not exists autolab.messages (
    id              bigserial primary key,
    conversation_id text not null references autolab.conversations (id) on delete cascade,
    role            text not null check (role in ('user', 'assistant')),
    kind            text not null,        -- request, scope, follow_up, answer, notice, summary, report
    content         text not null,
    question_key    text,                 -- normalised follow-up question, to answer it again without a model call
    data            jsonb,
    created_at      timestamptz not null default now()
);
create index if not exists messages_by_conversation on autolab.messages (conversation_id, id);
create index if not exists messages_question on autolab.messages (conversation_id, question_key)
    where question_key is not null;

create table if not exists autolab.events (     -- every event of the research, in order (the steps come from them)
    conversation_id text not null references autolab.conversations (id) on delete cascade,
    seq             integer not null,
    type            text not null,
    step            text not null,
    candidate_id    text,
    data            jsonb not null,
    ts              timestamptz not null,
    primary key (conversation_id, seq)
);

create table if not exists autolab.results (    -- the whole result of a research (source of truth for its report)
    conversation_id text primary key references autolab.conversations (id) on delete cascade,
    result          jsonb not null,
    created_at      timestamptz not null default now()
);

create table if not exists autolab.candidates ( -- one row per candidate material, for queries and follow-ups
    conversation_id text not null references autolab.conversations (id) on delete cascade,
    candidate_id    text not null,
    formula         text,
    parent          text,
    substitution    jsonb,
    status          text,
    excluded_at     text,
    e_hull          double precision,
    gap_optb88      double precision,
    d_ratio         double precision,
    md_verdict      text,
    novelty         text,
    data            jsonb not null,
    primary key (conversation_id, candidate_id)
);

create table if not exists autolab.artifacts (  -- visual files on the Modal volume (3D structures, MD animations)
    conversation_id text not null references autolab.conversations (id) on delete cascade,
    name            text not null,          -- e.g. structures/it1-c2.json, md/it1-c2_seed0.json, index.json
    kind            text not null,          -- structure, md, index
    path            text not null,          -- path on the volume
    meta            jsonb,
    primary key (conversation_id, name)
);

create table if not exists autolab.schema_migrations (
    version    text primary key,
    applied_at timestamptz not null default now()
);
