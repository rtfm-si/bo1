--
-- PostgreSQL database dump
--


-- Dumped from database version 16.11 (Debian 16.11-1.pgdg12+1)
-- Dumped by pg_dump version 16.11 (Debian 16.11-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--



--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--



--
-- Name: aal_level; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.aal_level AS ENUM (
    'aal1',
    'aal2',
    'aal3'
);


--
-- Name: code_challenge_method; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.code_challenge_method AS ENUM (
    's256',
    'plain'
);


--
-- Name: factor_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.factor_status AS ENUM (
    'unverified',
    'verified'
);


--
-- Name: factor_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.factor_type AS ENUM (
    'totp',
    'webauthn'
);


--
-- Name: one_time_token_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.one_time_token_type AS ENUM (
    'confirmation_token',
    'reauthentication_token',
    'recovery_token',
    'email_change_token_new',
    'email_change_token_current',
    'phone_change_token'
);


--
-- Name: create_next_month_partitions(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.create_next_month_partitions() RETURNS TABLE(table_name text, partition_name text, status text)
    LANGUAGE plpgsql
    AS $$
        DECLARE
            next_month DATE;
            partition_date DATE;
            tbl TEXT;
            part_name TEXT;
        BEGIN
            next_month := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '2 months');

            -- Loop through partitioned tables
            FOR tbl IN SELECT unnest(ARRAY['api_costs', 'session_events', 'contributions'])
            LOOP
                part_name := tbl || '_' || TO_CHAR(next_month, 'YYYY_MM');

                -- Check if partition already exists
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = part_name AND n.nspname = 'public'
                ) THEN
                    EXECUTE format(
                        'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                        part_name,
                        tbl,
                        next_month,
                        next_month + INTERVAL '1 month'
                    );

                    RETURN QUERY SELECT tbl, part_name, 'created'::TEXT;
                ELSE
                    RETURN QUERY SELECT tbl, part_name, 'already_exists'::TEXT;
                END IF;
            END LOOP;
        END;
        $$;


--
-- Name: FUNCTION create_next_month_partitions(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.create_next_month_partitions() IS 'Auto-create next month partitions for api_costs, session_events, contributions. Run monthly via cron.';


--
-- Name: list_partitions(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.list_partitions(parent_table text) RETURNS TABLE(partition_name text, start_range text, end_range text, row_count bigint)
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RETURN QUERY
            SELECT
                c.relname::TEXT,
                pg_get_expr(c.relpartbound, c.oid, true)::TEXT AS partition_range,
                NULL::TEXT,  -- Placeholder for end_range
                c.reltuples::BIGINT
            FROM pg_class c
            JOIN pg_inherits i ON i.inhrelid = c.oid
            JOIN pg_class p ON p.oid = i.inhparent
            WHERE p.relname = parent_table
            ORDER BY c.relname;
        END;
        $$;


--
-- Name: FUNCTION list_partitions(parent_table text); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.list_partitions(parent_table text) IS 'List all partitions with their date ranges and row counts';


--
-- Name: partition_sizes(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.partition_sizes(parent_table text) RETURNS TABLE(partition_name text, row_count bigint, total_size text, table_size text, indexes_size text)
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RETURN QUERY
            SELECT
                c.relname::TEXT,
                c.reltuples::BIGINT,
                pg_size_pretty(pg_total_relation_size(c.oid)),
                pg_size_pretty(pg_relation_size(c.oid)),
                pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid))
            FROM pg_class c
            JOIN pg_inherits i ON i.inhrelid = c.oid
            JOIN pg_class p ON p.oid = i.inhparent
            WHERE p.relname = parent_table
            ORDER BY c.relname;
        END;
        $$;


--
-- Name: FUNCTION partition_sizes(parent_table text); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.partition_sizes(parent_table text) IS 'Get size breakdown for all partitions of a table';


--
-- Name: refresh_session_cost_summary(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.refresh_session_cost_summary() RETURNS void
    LANGUAGE plpgsql
    AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY session_cost_summary;
        END;
        $$;


--
-- Name: FUNCTION refresh_session_cost_summary(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.refresh_session_cost_summary() IS 'Refresh session_cost_summary materialized view (call after session completes)';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: action_dependencies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_dependencies (
    action_id uuid NOT NULL,
    depends_on_action_id uuid NOT NULL,
    dependency_type character varying(30) DEFAULT 'finish_to_start'::character varying NOT NULL,
    lag_days integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT check_no_self_dependency CHECK ((action_id <> depends_on_action_id)),
    CONSTRAINT check_valid_dependency_type CHECK (((dependency_type)::text = ANY ((ARRAY['finish_to_start'::character varying, 'start_to_start'::character varying, 'finish_to_finish'::character varying])::text[])))
);


--
-- Name: TABLE action_dependencies; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.action_dependencies IS 'Action dependency relationships for automatic scheduling and blocking';


--
-- Name: COLUMN action_dependencies.action_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_dependencies.action_id IS 'Action that has a dependency';


--
-- Name: COLUMN action_dependencies.depends_on_action_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_dependencies.depends_on_action_id IS 'Action that must complete first';


--
-- Name: COLUMN action_dependencies.dependency_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_dependencies.dependency_type IS 'finish_to_start: predecessor must finish before successor starts, start_to_start: both start together, finish_to_finish: both finish together';


--
-- Name: COLUMN action_dependencies.lag_days; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_dependencies.lag_days IS 'Business days offset (positive = delay, negative = lead time). Example: finish_to_start with lag_days=2 means wait 2 days after predecessor finishes';


--
-- Name: action_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_tags (
    action_id uuid NOT NULL,
    tag_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: action_updates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.action_updates (
    id bigint NOT NULL,
    action_id uuid NOT NULL,
    user_id character varying(255) NOT NULL,
    update_type character varying(20) NOT NULL,
    content text NOT NULL,
    old_status character varying(20),
    new_status character varying(20),
    old_date date,
    new_date date,
    date_field character varying(50),
    progress_percent integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT check_date_change_field CHECK (((((update_type)::text = 'date_change'::text) AND (date_field IS NOT NULL)) OR ((update_type)::text <> 'date_change'::text))),
    CONSTRAINT check_progress_percent_range CHECK (((progress_percent IS NULL) OR ((progress_percent >= 0) AND (progress_percent <= 100)))),
    CONSTRAINT check_status_change_fields CHECK (((((update_type)::text = 'status_change'::text) AND (old_status IS NOT NULL) AND (new_status IS NOT NULL)) OR ((update_type)::text <> 'status_change'::text))),
    CONSTRAINT check_valid_update_type CHECK (((update_type)::text = ANY ((ARRAY['progress'::character varying, 'blocker'::character varying, 'note'::character varying, 'status_change'::character varying, 'date_change'::character varying, 'completion'::character varying])::text[])))
);


--
-- Name: TABLE action_updates; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.action_updates IS 'Activity feed and audit trail for action updates';


--
-- Name: COLUMN action_updates.update_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_updates.update_type IS 'Type of update: progress (milestone reached), blocker (blocked), note (general comment), status_change (status changed), date_change (date updated), completion (completed)';


--
-- Name: COLUMN action_updates.content; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_updates.content IS 'Human-readable update content or note';


--
-- Name: COLUMN action_updates.old_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_updates.old_status IS 'For status_change updates';


--
-- Name: COLUMN action_updates.new_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_updates.new_status IS 'For status_change updates';


--
-- Name: COLUMN action_updates.old_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_updates.old_date IS 'For date_change updates';


--
-- Name: COLUMN action_updates.new_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_updates.new_date IS 'For date_change updates';


--
-- Name: COLUMN action_updates.date_field; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_updates.date_field IS 'Which date field changed (target_start_date, etc.)';


--
-- Name: COLUMN action_updates.progress_percent; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.action_updates.progress_percent IS 'Progress percentage (0-100) for progress updates';


--
-- Name: action_updates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.action_updates_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: action_updates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.action_updates_id_seq OWNED BY public.action_updates.id;


--
-- Name: actions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.actions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255) NOT NULL,
    source_session_id character varying(255) NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    what_and_how text[] DEFAULT '{}'::text[] NOT NULL,
    success_criteria text[] DEFAULT '{}'::text[] NOT NULL,
    kill_criteria text[] DEFAULT '{}'::text[] NOT NULL,
    status character varying(20) DEFAULT 'todo'::character varying NOT NULL,
    priority character varying(20) DEFAULT 'medium'::character varying NOT NULL,
    category character varying(50) DEFAULT 'implementation'::character varying NOT NULL,
    timeline text,
    estimated_duration_days integer,
    target_start_date date,
    target_end_date date,
    estimated_start_date date,
    estimated_end_date date,
    actual_start_date timestamp with time zone,
    actual_end_date timestamp with time zone,
    blocking_reason text,
    blocked_at timestamp with time zone,
    auto_unblock boolean DEFAULT false NOT NULL,
    confidence numeric(3,2) DEFAULT 0.0 NOT NULL,
    source_section text,
    sub_problem_index integer,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    project_id uuid,
    replan_session_id character varying(255),
    replan_requested_at timestamp with time zone,
    replanning_reason text,
    deleted_at timestamp with time zone,
    CONSTRAINT check_action_confidence CHECK (((confidence >= 0.0) AND (confidence <= 1.0))),
    CONSTRAINT check_blocked_requires_reason CHECK (((((status)::text = 'blocked'::text) AND (blocking_reason IS NOT NULL)) OR ((status)::text <> 'blocked'::text))),
    CONSTRAINT check_estimated_duration_positive CHECK (((estimated_duration_days IS NULL) OR (estimated_duration_days > 0))),
    CONSTRAINT check_target_dates_logical CHECK (((target_end_date IS NULL) OR (target_start_date IS NULL) OR (target_end_date >= target_start_date))),
    CONSTRAINT check_valid_status CHECK (((status)::text = ANY ((ARRAY['todo'::character varying, 'in_progress'::character varying, 'blocked'::character varying, 'in_review'::character varying, 'done'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: TABLE actions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.actions IS 'Comprehensive action tracking table - replaces session_tasks JSONB with proper relational schema';


--
-- Name: COLUMN actions.id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.id IS 'UUID primary key';


--
-- Name: COLUMN actions.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.user_id IS 'Owner of the action (FK to users.user_id)';


--
-- Name: COLUMN actions.source_session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.source_session_id IS 'Session this action came from (FK to sessions.id)';


--
-- Name: COLUMN actions.title; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.title IS 'Short action title (5-10 words)';


--
-- Name: COLUMN actions.description; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.description IS 'Full action description';


--
-- Name: COLUMN actions.what_and_how; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.what_and_how IS 'Array of steps to complete the action';


--
-- Name: COLUMN actions.success_criteria; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.success_criteria IS 'Array of success measures';


--
-- Name: COLUMN actions.kill_criteria; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.kill_criteria IS 'Array of abandonment conditions';


--
-- Name: COLUMN actions.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.status IS 'Current status: todo, in_progress, blocked, in_review, done, cancelled';


--
-- Name: COLUMN actions.priority; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.priority IS 'Priority: high, medium, low';


--
-- Name: COLUMN actions.category; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.category IS 'Category: implementation, research, decision, communication';


--
-- Name: COLUMN actions.timeline; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.timeline IS 'Human-readable timeline (e.g., ''2 weeks'')';


--
-- Name: COLUMN actions.estimated_duration_days; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.estimated_duration_days IS 'Parsed duration in business days';


--
-- Name: COLUMN actions.target_start_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.target_start_date IS 'User-set target start date';


--
-- Name: COLUMN actions.target_end_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.target_end_date IS 'User-set target end date';


--
-- Name: COLUMN actions.estimated_start_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.estimated_start_date IS 'Auto-calculated from dependencies';


--
-- Name: COLUMN actions.estimated_end_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.estimated_end_date IS 'Auto-calculated from start + duration';


--
-- Name: COLUMN actions.actual_start_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.actual_start_date IS 'Actual start timestamp';


--
-- Name: COLUMN actions.actual_end_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.actual_end_date IS 'Actual completion timestamp';


--
-- Name: COLUMN actions.auto_unblock; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.auto_unblock IS 'Auto-unblock when dependencies complete';


--
-- Name: COLUMN actions.confidence; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.confidence IS 'AI extraction confidence (0.0-1.0)';


--
-- Name: COLUMN actions.source_section; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.source_section IS 'Which synthesis section this came from';


--
-- Name: COLUMN actions.sub_problem_index; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.sub_problem_index IS 'Which sub-problem/focus area this belongs to';


--
-- Name: COLUMN actions.sort_order; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.sort_order IS 'User-defined sort order within status column';


--
-- Name: COLUMN actions.project_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.project_id IS 'Optional parent project - actions can exist independently or belong to a project';


--
-- Name: COLUMN actions.deleted_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.actions.deleted_at IS 'Soft delete timestamp. NULL means not deleted. Admins can view deleted actions.';


--
-- Name: api_costs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs (
    id bigint NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
)
PARTITION BY RANGE (created_at);


--
-- Name: api_costs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.api_costs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: api_costs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.api_costs_id_seq OWNED BY public.api_costs.id;


--
-- Name: api_costs_2025_05; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2025_05 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2025_06; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2025_06 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2025_07; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2025_07 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2025_08; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2025_08 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2025_09; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2025_09 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2025_10; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2025_10 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2025_11; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2025_11 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2025_12; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2025_12 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2026_01; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2026_01 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2026_02; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2026_02 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2026_03; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2026_03 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2026_04; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2026_04 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: api_costs_2026_05; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_costs_2026_05 (
    id bigint DEFAULT nextval('public.api_costs_id_seq'::regclass) NOT NULL,
    request_id uuid DEFAULT gen_random_uuid() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    session_id character varying(255),
    user_id character varying(255),
    provider character varying(50) NOT NULL,
    model_name character varying(100),
    operation_type character varying(50) NOT NULL,
    node_name character varying(100),
    phase character varying(50),
    persona_name character varying(100),
    round_number integer,
    sub_problem_index integer,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer GENERATED ALWAYS AS ((input_tokens + output_tokens)) STORED,
    cache_creation_tokens integer DEFAULT 0 NOT NULL,
    cache_read_tokens integer DEFAULT 0 NOT NULL,
    cache_hit boolean DEFAULT false NOT NULL,
    input_cost numeric(12,8) DEFAULT 0 NOT NULL,
    output_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_write_cost numeric(12,8) DEFAULT 0 NOT NULL,
    cache_read_cost numeric(12,8) DEFAULT 0 NOT NULL,
    total_cost numeric(12,8) NOT NULL,
    optimization_type character varying(50),
    cost_without_optimization numeric(12,8),
    latency_ms integer,
    status character varying(20) DEFAULT 'success'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    contribution_id integer,
    recommendation_id integer,
    CONSTRAINT check_cost_positive CHECK ((total_cost >= (0)::numeric)),
    CONSTRAINT check_provider CHECK (((provider)::text = ANY ((ARRAY['anthropic'::character varying, 'voyage'::character varying, 'brave'::character varying, 'tavily'::character varying])::text[])))
);


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    id integer NOT NULL,
    user_id character varying(255),
    action character varying(100) NOT NULL,
    resource_type character varying(50) NOT NULL,
    resource_id character varying(255),
    details json,
    ip_address character varying(45),
    user_agent character varying(500),
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- Name: beta_whitelist; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.beta_whitelist (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    added_by character varying(255),
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: business_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.business_metrics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255) NOT NULL,
    metric_key character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    definition text,
    importance text,
    category character varying(50),
    value numeric(20,4),
    value_unit character varying(20),
    captured_at timestamp with time zone,
    source character varying(50) DEFAULT 'manual'::character varying NOT NULL,
    is_predefined boolean DEFAULT false NOT NULL,
    display_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT business_metrics_category_check CHECK (((category IS NULL) OR ((category)::text = ANY ((ARRAY['financial'::character varying, 'growth'::character varying, 'retention'::character varying, 'efficiency'::character varying, 'custom'::character varying])::text[])))),
    CONSTRAINT business_metrics_source_check CHECK (((source)::text = ANY ((ARRAY['manual'::character varying, 'clarification'::character varying, 'integration'::character varying])::text[])))
);


--
-- Name: COLUMN business_metrics.captured_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.business_metrics.captured_at IS 'When the value was captured/measured';


--
-- Name: COLUMN business_metrics.source; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.business_metrics.source IS 'manual, clarification, integration';


--
-- Name: COLUMN business_metrics.is_predefined; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.business_metrics.is_predefined IS 'True if based on a template';


--
-- Name: competitor_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competitor_profiles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255) NOT NULL,
    name character varying(200) NOT NULL,
    website character varying(500),
    tagline text,
    industry character varying(100),
    product_description text,
    pricing_model character varying(100),
    target_market text,
    business_model character varying(100),
    value_proposition text,
    tech_stack jsonb,
    recent_news jsonb,
    funding_info text,
    employee_count character varying(50),
    display_order integer DEFAULT 0 NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    data_depth character varying(20) DEFAULT 'basic'::character varying NOT NULL,
    source character varying(50) DEFAULT 'tavily'::character varying NOT NULL,
    last_enriched_at timestamp with time zone,
    previous_snapshot jsonb,
    changes_detected jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT competitor_profiles_depth_check CHECK (((data_depth)::text = ANY ((ARRAY['basic'::character varying, 'standard'::character varying, 'deep'::character varying])::text[])))
);


--
-- Name: COLUMN competitor_profiles.is_primary; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.competitor_profiles.is_primary IS 'User''s top competitors for focus';


--
-- Name: COLUMN competitor_profiles.data_depth; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.competitor_profiles.data_depth IS 'basic, standard, deep';


--
-- Name: COLUMN competitor_profiles.previous_snapshot; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.competitor_profiles.previous_snapshot IS 'Previous data for change detection';


--
-- Name: COLUMN competitor_profiles.changes_detected; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.competitor_profiles.changes_detected IS 'List of fields that changed in last refresh';


--
-- Name: contributions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions (
    id integer NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
)
PARTITION BY RANGE (created_at);


--
-- Name: contributions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contributions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contributions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contributions_id_seq OWNED BY public.contributions.id;


--
-- Name: contributions_2025_05; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2025_05 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2025_06; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2025_06 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2025_07; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2025_07 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2025_08; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2025_08 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2025_09; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2025_09 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2025_10; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2025_10 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2025_11; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2025_11 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2025_12; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2025_12 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2026_01; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2026_01 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2026_02; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2026_02 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2026_03; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2026_03 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2026_04; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2026_04 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contributions_2026_05; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contributions_2026_05 (
    id integer DEFAULT nextval('public.contributions_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    persona_code character varying(50) NOT NULL,
    content text NOT NULL,
    round_number integer NOT NULL,
    phase character varying(50) NOT NULL,
    cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    tokens integer DEFAULT 0 NOT NULL,
    model character varying(100) NOT NULL,
    embedding public.vector(1024),
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: facilitator_decisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.facilitator_decisions (
    id integer NOT NULL,
    session_id character varying(255) NOT NULL,
    round_number integer NOT NULL,
    sub_problem_index integer,
    action character varying(50) NOT NULL,
    reasoning text,
    next_speaker character varying(50),
    moderator_type character varying(50),
    research_query text,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: facilitator_decisions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.facilitator_decisions ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.facilitator_decisions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: industry_insights; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.industry_insights (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    industry character varying(100) NOT NULL,
    insight_type character varying(50) NOT NULL,
    content jsonb NOT NULL,
    source_count integer DEFAULT 1 NOT NULL,
    confidence numeric(3,2) DEFAULT 0.50 NOT NULL,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT industry_insights_type_check CHECK (((insight_type)::text = ANY ((ARRAY['trend'::character varying, 'benchmark'::character varying, 'competitor'::character varying, 'best_practice'::character varying])::text[])))
);


--
-- Name: COLUMN industry_insights.insight_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.industry_insights.insight_type IS 'trend, benchmark, competitor, best_practice';


--
-- Name: COLUMN industry_insights.content; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.industry_insights.content IS 'Structured insight data varies by type';


--
-- Name: COLUMN industry_insights.source_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.industry_insights.source_count IS 'Number of users contributing to this insight';


--
-- Name: COLUMN industry_insights.confidence; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.industry_insights.confidence IS 'Aggregated confidence score 0.00-1.00';


--
-- Name: COLUMN industry_insights.expires_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.industry_insights.expires_at IS 'When this insight expires (trends expire, benchmarks refresh quarterly)';


--
-- Name: metric_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.metric_templates (
    metric_key character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    definition text NOT NULL,
    importance text NOT NULL,
    category character varying(50) NOT NULL,
    value_unit character varying(20) NOT NULL,
    display_order integer DEFAULT 0 NOT NULL,
    applies_to jsonb DEFAULT '["all"]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: COLUMN metric_templates.category; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.metric_templates.category IS 'financial, growth, retention, efficiency';


--
-- Name: COLUMN metric_templates.value_unit; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.metric_templates.value_unit IS '$, %, months, ratio, days';


--
-- Name: COLUMN metric_templates.applies_to; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.metric_templates.applies_to IS 'Business models: saas, ecommerce, marketplace, all';


--
-- Name: personas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.personas (
    id integer NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    expertise character varying(500) NOT NULL,
    system_prompt text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: personas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.personas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: personas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.personas_id_seq OWNED BY public.personas.id;


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    target_start_date date,
    target_end_date date,
    estimated_start_date date,
    estimated_end_date date,
    actual_start_date timestamp with time zone,
    actual_end_date timestamp with time zone,
    progress_percent integer DEFAULT 0 NOT NULL,
    total_actions integer DEFAULT 0 NOT NULL,
    completed_actions integer DEFAULT 0 NOT NULL,
    color character varying(7),
    icon character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT check_project_completed_actions_valid CHECK (((completed_actions >= 0) AND (completed_actions <= total_actions))),
    CONSTRAINT check_project_progress_range CHECK (((progress_percent >= 0) AND (progress_percent <= 100))),
    CONSTRAINT check_project_target_dates_logical CHECK (((target_end_date IS NULL) OR (target_start_date IS NULL) OR (target_end_date >= target_start_date))),
    CONSTRAINT check_project_total_actions_non_negative CHECK ((total_actions >= 0)),
    CONSTRAINT check_project_valid_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'paused'::character varying, 'completed'::character varying, 'archived'::character varying])::text[])))
);


--
-- Name: TABLE projects; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.projects IS 'Projects are value-delivery containers that group related actions';


--
-- Name: COLUMN projects.id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.id IS 'UUID primary key';


--
-- Name: COLUMN projects.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.user_id IS 'Owner of the project (FK to users.id)';


--
-- Name: COLUMN projects.name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.name IS 'Project name';


--
-- Name: COLUMN projects.description; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.description IS 'Project description and goals';


--
-- Name: COLUMN projects.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.status IS 'Current status: active, paused, completed, archived';


--
-- Name: COLUMN projects.target_start_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.target_start_date IS 'User-set target start date';


--
-- Name: COLUMN projects.target_end_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.target_end_date IS 'User-set target end date';


--
-- Name: COLUMN projects.estimated_start_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.estimated_start_date IS 'Calculated: min(actions.estimated_start_date)';


--
-- Name: COLUMN projects.estimated_end_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.estimated_end_date IS 'Calculated: max(actions.estimated_end_date)';


--
-- Name: COLUMN projects.actual_start_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.actual_start_date IS 'When first action started';


--
-- Name: COLUMN projects.actual_end_date; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.actual_end_date IS 'When all actions completed';


--
-- Name: COLUMN projects.progress_percent; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.progress_percent IS 'Calculated from completed actions';


--
-- Name: COLUMN projects.total_actions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.total_actions IS 'Total number of actions in project';


--
-- Name: COLUMN projects.completed_actions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.completed_actions IS 'Number of completed actions';


--
-- Name: COLUMN projects.color; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.color IS 'Hex color for Gantt visualization';


--
-- Name: COLUMN projects.icon; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.projects.icon IS 'Emoji or icon name';


--
-- Name: recommendations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recommendations (
    id integer NOT NULL,
    session_id character varying(255),
    recommendation text,
    sub_problem_index integer,
    persona_code character varying(50) NOT NULL,
    persona_name character varying(255),
    reasoning text,
    confidence numeric(3,2),
    conditions json,
    weight numeric(3,2),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: recommendations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.recommendations ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.recommendations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: research_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.research_cache (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    question text NOT NULL,
    answer_summary text NOT NULL,
    confidence character varying(20),
    sources jsonb,
    source_count integer,
    category text,
    industry text,
    research_date timestamp with time zone DEFAULT now() NOT NULL,
    access_count integer DEFAULT 1 NOT NULL,
    last_accessed_at timestamp with time zone DEFAULT now() NOT NULL,
    freshness_days integer DEFAULT 90 NOT NULL,
    tokens_used integer,
    research_cost_usd numeric(10,6),
    question_embedding public.vector(1024),
    CONSTRAINT research_cache_confidence_check CHECK (((confidence)::text = ANY ((ARRAY['high'::character varying, 'medium'::character varying, 'low'::character varying])::text[])))
);


--
-- Name: research_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.research_metrics (
    id integer NOT NULL,
    query text NOT NULL,
    research_depth character varying(10) NOT NULL,
    keywords_matched text,
    success boolean NOT NULL,
    cached boolean DEFAULT false NOT NULL,
    sources_count integer DEFAULT 0 NOT NULL,
    confidence character varying(20),
    cost_usd numeric(10,6),
    response_time_ms numeric(10,2),
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: research_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.research_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: research_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.research_metrics_id_seq OWNED BY public.research_metrics.id;


--
-- Name: session_clarifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_clarifications (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id character varying(255) NOT NULL,
    question text NOT NULL,
    asked_by_persona text,
    priority character varying(20),
    reason text,
    answer text,
    answered_at timestamp with time zone,
    asked_at_round integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT session_clarifications_priority_check CHECK (((priority)::text = ANY ((ARRAY['CRITICAL'::character varying, 'NICE_TO_HAVE'::character varying])::text[])))
);


--
-- Name: session_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events (
    id bigint NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
)
PARTITION BY RANGE (created_at);


--
-- Name: session_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.session_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: session_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.session_events_id_seq OWNED BY public.session_events.id;


--
-- Name: session_events_2025_05; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2025_05 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2025_06; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2025_06 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2025_07; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2025_07 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2025_08; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2025_08 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2025_09; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2025_09 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2025_10; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2025_10 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2025_11; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2025_11 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2025_12; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2025_12 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2026_01; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2026_01 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2026_02; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2026_02 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2026_03; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2026_03 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2026_04; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2026_04 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_2026_05; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events_2026_05 (
    id bigint DEFAULT nextval('public.session_events_id_seq'::regclass) NOT NULL,
    session_id character varying(255) NOT NULL,
    event_type character varying(100) NOT NULL,
    sequence integer NOT NULL,
    data jsonb NOT NULL,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_projects (
    session_id character varying(255) NOT NULL,
    project_id uuid NOT NULL,
    relationship character varying(50) DEFAULT 'discusses'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT check_session_project_relationship CHECK (((relationship)::text = ANY ((ARRAY['discusses'::character varying, 'created_from'::character varying, 'replanning'::character varying])::text[])))
);


--
-- Name: TABLE session_projects; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.session_projects IS 'Links sessions to projects they discuss, created, or are replanning';


--
-- Name: COLUMN session_projects.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.session_projects.session_id IS 'FK to sessions.id';


--
-- Name: COLUMN session_projects.project_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.session_projects.project_id IS 'FK to projects.id';


--
-- Name: COLUMN session_projects.relationship; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.session_projects.relationship IS 'discusses: session mentions project, created_from: session created the project, replanning: session is replanning blocked project';


--
-- Name: session_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_tasks (
    id bigint NOT NULL,
    session_id character varying(255) NOT NULL,
    tasks jsonb NOT NULL,
    total_tasks integer DEFAULT 0 NOT NULL,
    extraction_confidence numeric(3,2) DEFAULT 0.0 NOT NULL,
    synthesis_sections_analyzed text[] DEFAULT ARRAY[]::text[],
    extracted_at timestamp with time zone DEFAULT now() NOT NULL,
    sub_problem_index integer,
    user_id character varying(255) NOT NULL,
    task_statuses jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT check_extraction_confidence CHECK (((extraction_confidence >= 0.0) AND (extraction_confidence <= 1.0))),
    CONSTRAINT check_total_tasks CHECK ((total_tasks >= 0))
);


--
-- Name: TABLE session_tasks; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.session_tasks IS 'Extracted actionable tasks from session synthesis (cached in Redis, persisted here)';


--
-- Name: COLUMN session_tasks.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.session_tasks.session_id IS 'Session identifier (matches sessions.id, unique - one extraction per session)';


--
-- Name: COLUMN session_tasks.tasks; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.session_tasks.tasks IS 'Array of ExtractedTask objects as JSONB';


--
-- Name: COLUMN session_tasks.total_tasks; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.session_tasks.total_tasks IS 'Total number of tasks extracted';


--
-- Name: COLUMN session_tasks.extraction_confidence; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.session_tasks.extraction_confidence IS 'AI confidence in task extraction (0.0-1.0)';


--
-- Name: COLUMN session_tasks.synthesis_sections_analyzed; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.session_tasks.synthesis_sections_analyzed IS 'Which synthesis sections were analyzed';


--
-- Name: COLUMN session_tasks.extracted_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.session_tasks.extracted_at IS 'When tasks were extracted';


--
-- Name: COLUMN session_tasks.task_statuses; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.session_tasks.task_statuses IS 'Per-task status tracking as JSONB object. Keys are task IDs (e.g., "task_1"), values are status strings ("todo", "doing", "done"). Default status for new tasks is "todo".';


--
-- Name: session_tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.session_tasks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: session_tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.session_tasks_id_seq OWNED BY public.session_tasks.id;


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sessions (
    id character varying(255) NOT NULL,
    user_id character varying(255) NOT NULL,
    problem_statement text NOT NULL,
    problem_context jsonb,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    phase character varying(50) DEFAULT 'problem_decomposition'::character varying NOT NULL,
    total_cost numeric(10,4) DEFAULT 0.0 NOT NULL,
    total_tokens integer DEFAULT 0 NOT NULL,
    round_number integer DEFAULT 0 NOT NULL,
    max_rounds integer DEFAULT 10 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    killed_at timestamp with time zone,
    killed_by character varying(255),
    kill_reason character varying(500),
    synthesis_text text,
    final_recommendation text
);


--
-- Name: TABLE sessions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.sessions IS 'Deliberation sessions - primary source of truth (Redis is cache only)';


--
-- Name: COLUMN sessions.id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.id IS 'Session identifier (e.g., bo1_uuid)';


--
-- Name: COLUMN sessions.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.user_id IS 'User who created the session (from SuperTokens)';


--
-- Name: COLUMN sessions.problem_statement; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.problem_statement IS 'Original problem statement';


--
-- Name: COLUMN sessions.problem_context; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.problem_context IS 'Additional context as JSONB';


--
-- Name: COLUMN sessions.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.status IS 'Session status: created, running, completed, failed, killed, deleted';


--
-- Name: COLUMN sessions.phase; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.phase IS 'Current deliberation phase';


--
-- Name: COLUMN sessions.total_cost; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.total_cost IS 'Total cost in USD';


--
-- Name: COLUMN sessions.round_number; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.round_number IS 'Current round number';


--
-- Name: COLUMN sessions.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.created_at IS 'When session was created';


--
-- Name: COLUMN sessions.updated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.updated_at IS 'When session was last updated';


--
-- Name: COLUMN sessions.synthesis_text; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.synthesis_text IS 'Final synthesis XML from synthesize or meta_synthesize node';


--
-- Name: COLUMN sessions.final_recommendation; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessions.final_recommendation IS 'Final recommendation from deliberation';


--
-- Name: sub_problem_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sub_problem_results (
    id integer NOT NULL,
    session_id character varying(255) NOT NULL,
    sub_problem_index integer NOT NULL,
    goal text NOT NULL,
    synthesis text,
    expert_summaries jsonb,
    cost numeric(10,4),
    duration_seconds integer,
    contribution_count integer,
    user_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: sub_problem_results_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.sub_problem_results ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.sub_problem_results_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tags (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255) NOT NULL,
    name character varying(100) NOT NULL,
    color character varying(7) DEFAULT '#6366F1'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_context; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_context (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255) NOT NULL,
    business_model text,
    target_market text,
    product_description text,
    revenue text,
    customers text,
    growth_rate text,
    competitors text,
    website text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    company_name character varying(255),
    business_stage character varying(50),
    primary_objective character varying(100),
    industry character varying(100),
    product_categories jsonb,
    pricing_model character varying(100),
    brand_positioning text,
    brand_tone character varying(100),
    brand_maturity character varying(50),
    tech_stack jsonb,
    seo_structure jsonb,
    detected_competitors jsonb,
    ideal_customer_profile text,
    keywords jsonb,
    target_geography character varying(255),
    traffic_range character varying(50),
    mau_bucket character varying(50),
    revenue_stage character varying(50),
    main_value_proposition text,
    team_size character varying(50),
    budget_constraints text,
    time_constraints text,
    regulatory_constraints text,
    enrichment_source character varying(50),
    enrichment_date timestamp with time zone,
    last_refresh_prompt timestamp with time zone,
    onboarding_completed boolean DEFAULT false NOT NULL,
    onboarding_completed_at timestamp with time zone,
    CONSTRAINT user_context_business_stage_check CHECK (((business_stage IS NULL) OR ((business_stage)::text = ANY ((ARRAY['idea'::character varying, 'early'::character varying, 'growing'::character varying, 'scaling'::character varying])::text[])))),
    CONSTRAINT user_context_enrichment_source_check CHECK (((enrichment_source IS NULL) OR ((enrichment_source)::text = ANY ((ARRAY['manual'::character varying, 'api'::character varying, 'scrape'::character varying])::text[])))),
    CONSTRAINT user_context_primary_objective_check CHECK (((primary_objective IS NULL) OR ((primary_objective)::text = ANY ((ARRAY['acquire_customers'::character varying, 'improve_retention'::character varying, 'raise_capital'::character varying, 'launch_product'::character varying, 'reduce_costs'::character varying])::text[]))))
);


--
-- Name: COLUMN user_context.business_stage; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.business_stage IS 'idea, early, growing, scaling';


--
-- Name: COLUMN user_context.primary_objective; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.primary_objective IS 'acquire_customers, improve_retention, raise_capital, launch_product, reduce_costs';


--
-- Name: COLUMN user_context.product_categories; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.product_categories IS 'Array of product/service categories';


--
-- Name: COLUMN user_context.brand_maturity; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.brand_maturity IS 'startup, emerging, established, mature';


--
-- Name: COLUMN user_context.tech_stack; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.tech_stack IS 'Detected technologies';


--
-- Name: COLUMN user_context.seo_structure; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.seo_structure IS 'SEO metadata from website';


--
-- Name: COLUMN user_context.detected_competitors; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.detected_competitors IS 'Auto-detected competitors';


--
-- Name: COLUMN user_context.keywords; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.keywords IS 'Market category keywords';


--
-- Name: COLUMN user_context.traffic_range; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.traffic_range IS 'e.g., <1k, 1k-10k, 10k-100k, 100k+';


--
-- Name: COLUMN user_context.mau_bucket; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.mau_bucket IS 'Monthly active users bucket';


--
-- Name: COLUMN user_context.revenue_stage; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.revenue_stage IS 'pre-revenue, early, growth, mature';


--
-- Name: COLUMN user_context.team_size; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.team_size IS 'solo, small (2-5), medium (6-20), large (20+)';


--
-- Name: COLUMN user_context.enrichment_source; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_context.enrichment_source IS 'manual, api, scrape';


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    auth_provider character varying(50) NOT NULL,
    subscription_tier character varying(50) DEFAULT 'free'::character varying NOT NULL,
    gdpr_consent_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    is_locked boolean DEFAULT false NOT NULL,
    locked_at timestamp with time zone,
    locked_by character varying(255),
    lock_reason character varying(500),
    deleted_at timestamp with time zone,
    deleted_by character varying(255)
);


--
-- Name: user_metrics; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.user_metrics AS
 SELECT u.id,
    u.email,
    u.subscription_tier,
    u.is_admin,
    u.created_at AS user_created_at,
    count(s.id) AS total_meetings,
    COALESCE(sum(s.total_cost), (0)::numeric) AS total_cost,
    max(s.created_at) AS last_meeting_at,
    ( SELECT sessions.id
           FROM public.sessions
          WHERE ((sessions.user_id)::text = (u.id)::text)
          ORDER BY sessions.created_at DESC
         LIMIT 1) AS last_meeting_id
   FROM (public.users u
     LEFT JOIN public.sessions s ON (((u.id)::text = (s.user_id)::text)))
  GROUP BY u.id, u.email, u.subscription_tier, u.is_admin, u.created_at;


--
-- Name: user_onboarding; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_onboarding (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255) NOT NULL,
    tour_completed boolean DEFAULT false NOT NULL,
    tour_completed_at timestamp with time zone,
    steps_completed jsonb DEFAULT '[]'::jsonb NOT NULL,
    first_meeting_id character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: COLUMN user_onboarding.steps_completed; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_onboarding.steps_completed IS 'Array of completed step names: business_context, first_meeting, expert_panel, results';


--
-- Name: waitlist; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.waitlist (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    source character varying(100),
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: COLUMN waitlist.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.waitlist.status IS 'Status: pending, invited, converted';


--
-- Name: COLUMN waitlist.source; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.waitlist.source IS 'Where they signed up: landing_page, footer, etc.';


--
-- Name: COLUMN waitlist.notes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.waitlist.notes IS 'Admin notes about this signup';


--
-- Name: api_costs_2025_05; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2025_05 FOR VALUES FROM ('2025-05-01 00:00:00+00') TO ('2025-06-01 00:00:00+00');


--
-- Name: api_costs_2025_06; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2025_06 FOR VALUES FROM ('2025-06-01 00:00:00+00') TO ('2025-07-01 00:00:00+00');


--
-- Name: api_costs_2025_07; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2025_07 FOR VALUES FROM ('2025-07-01 00:00:00+00') TO ('2025-08-01 00:00:00+00');


--
-- Name: api_costs_2025_08; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2025_08 FOR VALUES FROM ('2025-08-01 00:00:00+00') TO ('2025-09-01 00:00:00+00');


--
-- Name: api_costs_2025_09; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2025_09 FOR VALUES FROM ('2025-09-01 00:00:00+00') TO ('2025-10-01 00:00:00+00');


--
-- Name: api_costs_2025_10; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2025_10 FOR VALUES FROM ('2025-10-01 00:00:00+00') TO ('2025-11-01 00:00:00+00');


--
-- Name: api_costs_2025_11; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2025_11 FOR VALUES FROM ('2025-11-01 00:00:00+00') TO ('2025-12-01 00:00:00+00');


--
-- Name: api_costs_2025_12; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2025_12 FOR VALUES FROM ('2025-12-01 00:00:00+00') TO ('2026-01-01 00:00:00+00');


--
-- Name: api_costs_2026_01; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2026_01 FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-02-01 00:00:00+00');


--
-- Name: api_costs_2026_02; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2026_02 FOR VALUES FROM ('2026-02-01 00:00:00+00') TO ('2026-03-01 00:00:00+00');


--
-- Name: api_costs_2026_03; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2026_03 FOR VALUES FROM ('2026-03-01 00:00:00+00') TO ('2026-04-01 00:00:00+00');


--
-- Name: api_costs_2026_04; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2026_04 FOR VALUES FROM ('2026-04-01 00:00:00+00') TO ('2026-05-01 00:00:00+00');


--
-- Name: api_costs_2026_05; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ATTACH PARTITION public.api_costs_2026_05 FOR VALUES FROM ('2026-05-01 00:00:00+00') TO ('2026-06-01 00:00:00+00');


--
-- Name: contributions_2025_05; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2025_05 FOR VALUES FROM ('2025-05-01 00:00:00+00') TO ('2025-06-01 00:00:00+00');


--
-- Name: contributions_2025_06; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2025_06 FOR VALUES FROM ('2025-06-01 00:00:00+00') TO ('2025-07-01 00:00:00+00');


--
-- Name: contributions_2025_07; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2025_07 FOR VALUES FROM ('2025-07-01 00:00:00+00') TO ('2025-08-01 00:00:00+00');


--
-- Name: contributions_2025_08; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2025_08 FOR VALUES FROM ('2025-08-01 00:00:00+00') TO ('2025-09-01 00:00:00+00');


--
-- Name: contributions_2025_09; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2025_09 FOR VALUES FROM ('2025-09-01 00:00:00+00') TO ('2025-10-01 00:00:00+00');


--
-- Name: contributions_2025_10; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2025_10 FOR VALUES FROM ('2025-10-01 00:00:00+00') TO ('2025-11-01 00:00:00+00');


--
-- Name: contributions_2025_11; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2025_11 FOR VALUES FROM ('2025-11-01 00:00:00+00') TO ('2025-12-01 00:00:00+00');


--
-- Name: contributions_2025_12; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2025_12 FOR VALUES FROM ('2025-12-01 00:00:00+00') TO ('2026-01-01 00:00:00+00');


--
-- Name: contributions_2026_01; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2026_01 FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-02-01 00:00:00+00');


--
-- Name: contributions_2026_02; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2026_02 FOR VALUES FROM ('2026-02-01 00:00:00+00') TO ('2026-03-01 00:00:00+00');


--
-- Name: contributions_2026_03; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2026_03 FOR VALUES FROM ('2026-03-01 00:00:00+00') TO ('2026-04-01 00:00:00+00');


--
-- Name: contributions_2026_04; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2026_04 FOR VALUES FROM ('2026-04-01 00:00:00+00') TO ('2026-05-01 00:00:00+00');


--
-- Name: contributions_2026_05; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ATTACH PARTITION public.contributions_2026_05 FOR VALUES FROM ('2026-05-01 00:00:00+00') TO ('2026-06-01 00:00:00+00');


--
-- Name: session_events_2025_05; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2025_05 FOR VALUES FROM ('2025-05-01 00:00:00+00') TO ('2025-06-01 00:00:00+00');


--
-- Name: session_events_2025_06; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2025_06 FOR VALUES FROM ('2025-06-01 00:00:00+00') TO ('2025-07-01 00:00:00+00');


--
-- Name: session_events_2025_07; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2025_07 FOR VALUES FROM ('2025-07-01 00:00:00+00') TO ('2025-08-01 00:00:00+00');


--
-- Name: session_events_2025_08; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2025_08 FOR VALUES FROM ('2025-08-01 00:00:00+00') TO ('2025-09-01 00:00:00+00');


--
-- Name: session_events_2025_09; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2025_09 FOR VALUES FROM ('2025-09-01 00:00:00+00') TO ('2025-10-01 00:00:00+00');


--
-- Name: session_events_2025_10; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2025_10 FOR VALUES FROM ('2025-10-01 00:00:00+00') TO ('2025-11-01 00:00:00+00');


--
-- Name: session_events_2025_11; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2025_11 FOR VALUES FROM ('2025-11-01 00:00:00+00') TO ('2025-12-01 00:00:00+00');


--
-- Name: session_events_2025_12; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2025_12 FOR VALUES FROM ('2025-12-01 00:00:00+00') TO ('2026-01-01 00:00:00+00');


--
-- Name: session_events_2026_01; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2026_01 FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-02-01 00:00:00+00');


--
-- Name: session_events_2026_02; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2026_02 FOR VALUES FROM ('2026-02-01 00:00:00+00') TO ('2026-03-01 00:00:00+00');


--
-- Name: session_events_2026_03; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2026_03 FOR VALUES FROM ('2026-03-01 00:00:00+00') TO ('2026-04-01 00:00:00+00');


--
-- Name: session_events_2026_04; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2026_04 FOR VALUES FROM ('2026-04-01 00:00:00+00') TO ('2026-05-01 00:00:00+00');


--
-- Name: session_events_2026_05; Type: TABLE ATTACH; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ATTACH PARTITION public.session_events_2026_05 FOR VALUES FROM ('2026-05-01 00:00:00+00') TO ('2026-06-01 00:00:00+00');


--
-- Name: action_updates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_updates ALTER COLUMN id SET DEFAULT nextval('public.action_updates_id_seq'::regclass);


--
-- Name: api_costs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs ALTER COLUMN id SET DEFAULT nextval('public.api_costs_id_seq'::regclass);


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- Name: contributions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions ALTER COLUMN id SET DEFAULT nextval('public.contributions_id_seq'::regclass);


--
-- Name: personas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personas ALTER COLUMN id SET DEFAULT nextval('public.personas_id_seq'::regclass);


--
-- Name: research_metrics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.research_metrics ALTER COLUMN id SET DEFAULT nextval('public.research_metrics_id_seq'::regclass);


--
-- Name: session_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ALTER COLUMN id SET DEFAULT nextval('public.session_events_id_seq'::regclass);


--
-- Name: session_tasks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_tasks ALTER COLUMN id SET DEFAULT nextval('public.session_tasks_id_seq'::regclass);


--
-- Name: action_tags action_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_tags
    ADD CONSTRAINT action_tags_pkey PRIMARY KEY (action_id, tag_id);


--
-- Name: action_updates action_updates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_updates
    ADD CONSTRAINT action_updates_pkey PRIMARY KEY (id);


--
-- Name: actions actions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT actions_pkey PRIMARY KEY (id);


--
-- Name: api_costs api_costs_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs
    ADD CONSTRAINT api_costs_pkey1 PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2025_05 api_costs_2025_05_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2025_05
    ADD CONSTRAINT api_costs_2025_05_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2025_06 api_costs_2025_06_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2025_06
    ADD CONSTRAINT api_costs_2025_06_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2025_07 api_costs_2025_07_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2025_07
    ADD CONSTRAINT api_costs_2025_07_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2025_08 api_costs_2025_08_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2025_08
    ADD CONSTRAINT api_costs_2025_08_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2025_09 api_costs_2025_09_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2025_09
    ADD CONSTRAINT api_costs_2025_09_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2025_10 api_costs_2025_10_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2025_10
    ADD CONSTRAINT api_costs_2025_10_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2025_11 api_costs_2025_11_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2025_11
    ADD CONSTRAINT api_costs_2025_11_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2025_12 api_costs_2025_12_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2025_12
    ADD CONSTRAINT api_costs_2025_12_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2026_01 api_costs_2026_01_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2026_01
    ADD CONSTRAINT api_costs_2026_01_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2026_02 api_costs_2026_02_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2026_02
    ADD CONSTRAINT api_costs_2026_02_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2026_03 api_costs_2026_03_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2026_03
    ADD CONSTRAINT api_costs_2026_03_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2026_04 api_costs_2026_04_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2026_04
    ADD CONSTRAINT api_costs_2026_04_pkey PRIMARY KEY (id, created_at);


--
-- Name: api_costs_2026_05 api_costs_2026_05_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_costs_2026_05
    ADD CONSTRAINT api_costs_2026_05_pkey PRIMARY KEY (id, created_at);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: beta_whitelist beta_whitelist_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.beta_whitelist
    ADD CONSTRAINT beta_whitelist_email_key UNIQUE (email);


--
-- Name: beta_whitelist beta_whitelist_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.beta_whitelist
    ADD CONSTRAINT beta_whitelist_pkey PRIMARY KEY (id);


--
-- Name: business_metrics business_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.business_metrics
    ADD CONSTRAINT business_metrics_pkey PRIMARY KEY (id);


--
-- Name: competitor_profiles competitor_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitor_profiles
    ADD CONSTRAINT competitor_profiles_pkey PRIMARY KEY (id);


--
-- Name: contributions contributions_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions
    ADD CONSTRAINT contributions_pkey1 PRIMARY KEY (id, created_at);


--
-- Name: contributions_2025_05 contributions_2025_05_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2025_05
    ADD CONSTRAINT contributions_2025_05_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2025_06 contributions_2025_06_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2025_06
    ADD CONSTRAINT contributions_2025_06_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2025_07 contributions_2025_07_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2025_07
    ADD CONSTRAINT contributions_2025_07_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2025_08 contributions_2025_08_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2025_08
    ADD CONSTRAINT contributions_2025_08_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2025_09 contributions_2025_09_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2025_09
    ADD CONSTRAINT contributions_2025_09_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2025_10 contributions_2025_10_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2025_10
    ADD CONSTRAINT contributions_2025_10_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2025_11 contributions_2025_11_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2025_11
    ADD CONSTRAINT contributions_2025_11_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2025_12 contributions_2025_12_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2025_12
    ADD CONSTRAINT contributions_2025_12_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2026_01 contributions_2026_01_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2026_01
    ADD CONSTRAINT contributions_2026_01_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2026_02 contributions_2026_02_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2026_02
    ADD CONSTRAINT contributions_2026_02_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2026_03 contributions_2026_03_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2026_03
    ADD CONSTRAINT contributions_2026_03_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2026_04 contributions_2026_04_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2026_04
    ADD CONSTRAINT contributions_2026_04_pkey PRIMARY KEY (id, created_at);


--
-- Name: contributions_2026_05 contributions_2026_05_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contributions_2026_05
    ADD CONSTRAINT contributions_2026_05_pkey PRIMARY KEY (id, created_at);


--
-- Name: facilitator_decisions facilitator_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facilitator_decisions
    ADD CONSTRAINT facilitator_decisions_pkey PRIMARY KEY (id);


--
-- Name: industry_insights industry_insights_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.industry_insights
    ADD CONSTRAINT industry_insights_pkey PRIMARY KEY (id);


--
-- Name: metric_templates metric_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.metric_templates
    ADD CONSTRAINT metric_templates_pkey PRIMARY KEY (metric_key);


--
-- Name: personas personas_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_code_key UNIQUE (code);


--
-- Name: personas personas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.personas
    ADD CONSTRAINT personas_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: recommendations recommendations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recommendations
    ADD CONSTRAINT recommendations_pkey PRIMARY KEY (id);


--
-- Name: research_cache research_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.research_cache
    ADD CONSTRAINT research_cache_pkey PRIMARY KEY (id);


--
-- Name: research_metrics research_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.research_metrics
    ADD CONSTRAINT research_metrics_pkey PRIMARY KEY (id);


--
-- Name: session_clarifications session_clarifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_clarifications
    ADD CONSTRAINT session_clarifications_pkey PRIMARY KEY (id);


--
-- Name: session_events session_events_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events
    ADD CONSTRAINT session_events_pkey1 PRIMARY KEY (id, created_at);


--
-- Name: session_events_2025_05 session_events_2025_05_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2025_05
    ADD CONSTRAINT session_events_2025_05_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2025_06 session_events_2025_06_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2025_06
    ADD CONSTRAINT session_events_2025_06_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2025_07 session_events_2025_07_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2025_07
    ADD CONSTRAINT session_events_2025_07_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2025_08 session_events_2025_08_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2025_08
    ADD CONSTRAINT session_events_2025_08_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2025_09 session_events_2025_09_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2025_09
    ADD CONSTRAINT session_events_2025_09_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2025_10 session_events_2025_10_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2025_10
    ADD CONSTRAINT session_events_2025_10_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2025_11 session_events_2025_11_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2025_11
    ADD CONSTRAINT session_events_2025_11_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2025_12 session_events_2025_12_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2025_12
    ADD CONSTRAINT session_events_2025_12_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2026_01 session_events_2026_01_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2026_01
    ADD CONSTRAINT session_events_2026_01_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2026_02 session_events_2026_02_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2026_02
    ADD CONSTRAINT session_events_2026_02_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2026_03 session_events_2026_03_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2026_03
    ADD CONSTRAINT session_events_2026_03_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2026_04 session_events_2026_04_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2026_04
    ADD CONSTRAINT session_events_2026_04_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_events_2026_05 session_events_2026_05_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events_2026_05
    ADD CONSTRAINT session_events_2026_05_pkey PRIMARY KEY (id, created_at);


--
-- Name: session_projects session_projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_projects
    ADD CONSTRAINT session_projects_pkey PRIMARY KEY (session_id, project_id);


--
-- Name: session_tasks session_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_tasks
    ADD CONSTRAINT session_tasks_pkey PRIMARY KEY (id);


--
-- Name: session_tasks session_tasks_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_tasks
    ADD CONSTRAINT session_tasks_session_id_key UNIQUE (session_id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: sub_problem_results sub_problem_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sub_problem_results
    ADD CONSTRAINT sub_problem_results_pkey PRIMARY KEY (id);


--
-- Name: tags tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_pkey PRIMARY KEY (id);


--
-- Name: action_dependencies unique_action_dependency; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_dependencies
    ADD CONSTRAINT unique_action_dependency PRIMARY KEY (action_id, depends_on_action_id);


--
-- Name: business_metrics uq_business_metrics_user_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.business_metrics
    ADD CONSTRAINT uq_business_metrics_user_key UNIQUE (user_id, metric_key);


--
-- Name: competitor_profiles uq_competitor_profiles_user_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitor_profiles
    ADD CONSTRAINT uq_competitor_profiles_user_name UNIQUE (user_id, name);


--
-- Name: tags uq_tags_user_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT uq_tags_user_name UNIQUE (user_id, name);


--
-- Name: user_context user_context_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_context
    ADD CONSTRAINT user_context_pkey PRIMARY KEY (id);


--
-- Name: user_context user_context_unique_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_context
    ADD CONSTRAINT user_context_unique_user UNIQUE (user_id);


--
-- Name: user_onboarding user_onboarding_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_onboarding
    ADD CONSTRAINT user_onboarding_pkey PRIMARY KEY (id);


--
-- Name: user_onboarding user_onboarding_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_onboarding
    ADD CONSTRAINT user_onboarding_user_id_key UNIQUE (user_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: waitlist waitlist_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.waitlist
    ADD CONSTRAINT waitlist_email_key UNIQUE (email);


--
-- Name: waitlist waitlist_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.waitlist
    ADD CONSTRAINT waitlist_pkey PRIMARY KEY (id);


--
-- Name: idx_api_costs_contribution; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_contribution ON ONLY public.api_costs USING btree (contribution_id);


--
-- Name: api_costs_2025_05_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_contribution_id_idx ON public.api_costs_2025_05 USING btree (contribution_id);


--
-- Name: idx_api_costs_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_created ON ONLY public.api_costs USING btree (created_at DESC);


--
-- Name: api_costs_2025_05_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_created_at_idx ON public.api_costs_2025_05 USING btree (created_at DESC);


--
-- Name: idx_api_costs_analysis; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_analysis ON ONLY public.api_costs USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2025_05_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_created_at_session_id_provider_total_cost_idx ON public.api_costs_2025_05 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: idx_api_costs_metadata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_metadata ON ONLY public.api_costs USING gin (metadata);


--
-- Name: api_costs_2025_05_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_metadata_idx ON public.api_costs_2025_05 USING gin (metadata);


--
-- Name: idx_api_costs_node; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_node ON ONLY public.api_costs USING btree (node_name);


--
-- Name: api_costs_2025_05_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_node_name_idx ON public.api_costs_2025_05 USING btree (node_name);


--
-- Name: idx_api_costs_phase; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_phase ON ONLY public.api_costs USING btree (phase);


--
-- Name: api_costs_2025_05_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_phase_idx ON public.api_costs_2025_05 USING btree (phase);


--
-- Name: idx_api_costs_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_provider ON ONLY public.api_costs USING btree (provider, model_name);


--
-- Name: api_costs_2025_05_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_provider_model_name_idx ON public.api_costs_2025_05 USING btree (provider, model_name);


--
-- Name: idx_api_costs_recommendation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_recommendation ON ONLY public.api_costs USING btree (recommendation_id);


--
-- Name: api_costs_2025_05_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_recommendation_id_idx ON public.api_costs_2025_05 USING btree (recommendation_id);


--
-- Name: api_costs_request_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_request_id_key ON ONLY public.api_costs USING btree (request_id, created_at);


--
-- Name: api_costs_2025_05_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2025_05_request_id_created_at_idx ON public.api_costs_2025_05 USING btree (request_id, created_at);


--
-- Name: idx_api_costs_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_session ON ONLY public.api_costs USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2025_05_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_session_id_created_at_idx ON public.api_costs_2025_05 USING btree (session_id, created_at DESC);


--
-- Name: idx_api_costs_session_node; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_session_node ON ONLY public.api_costs USING btree (session_id, node_name);


--
-- Name: api_costs_2025_05_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_session_id_node_name_idx ON public.api_costs_2025_05 USING btree (session_id, node_name);


--
-- Name: idx_api_costs_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_user ON ONLY public.api_costs USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_05_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_user_id_created_at_idx ON public.api_costs_2025_05 USING btree (user_id, created_at DESC);


--
-- Name: idx_api_costs_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_api_costs_user_created ON ONLY public.api_costs USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_05_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_05_user_id_created_at_idx1 ON public.api_costs_2025_05 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_06_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_contribution_id_idx ON public.api_costs_2025_06 USING btree (contribution_id);


--
-- Name: api_costs_2025_06_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_created_at_idx ON public.api_costs_2025_06 USING btree (created_at DESC);


--
-- Name: api_costs_2025_06_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_created_at_session_id_provider_total_cost_idx ON public.api_costs_2025_06 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2025_06_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_metadata_idx ON public.api_costs_2025_06 USING gin (metadata);


--
-- Name: api_costs_2025_06_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_node_name_idx ON public.api_costs_2025_06 USING btree (node_name);


--
-- Name: api_costs_2025_06_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_phase_idx ON public.api_costs_2025_06 USING btree (phase);


--
-- Name: api_costs_2025_06_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_provider_model_name_idx ON public.api_costs_2025_06 USING btree (provider, model_name);


--
-- Name: api_costs_2025_06_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_recommendation_id_idx ON public.api_costs_2025_06 USING btree (recommendation_id);


--
-- Name: api_costs_2025_06_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2025_06_request_id_created_at_idx ON public.api_costs_2025_06 USING btree (request_id, created_at);


--
-- Name: api_costs_2025_06_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_session_id_created_at_idx ON public.api_costs_2025_06 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2025_06_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_session_id_node_name_idx ON public.api_costs_2025_06 USING btree (session_id, node_name);


--
-- Name: api_costs_2025_06_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_user_id_created_at_idx ON public.api_costs_2025_06 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_06_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_06_user_id_created_at_idx1 ON public.api_costs_2025_06 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_07_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_contribution_id_idx ON public.api_costs_2025_07 USING btree (contribution_id);


--
-- Name: api_costs_2025_07_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_created_at_idx ON public.api_costs_2025_07 USING btree (created_at DESC);


--
-- Name: api_costs_2025_07_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_created_at_session_id_provider_total_cost_idx ON public.api_costs_2025_07 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2025_07_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_metadata_idx ON public.api_costs_2025_07 USING gin (metadata);


--
-- Name: api_costs_2025_07_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_node_name_idx ON public.api_costs_2025_07 USING btree (node_name);


--
-- Name: api_costs_2025_07_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_phase_idx ON public.api_costs_2025_07 USING btree (phase);


--
-- Name: api_costs_2025_07_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_provider_model_name_idx ON public.api_costs_2025_07 USING btree (provider, model_name);


--
-- Name: api_costs_2025_07_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_recommendation_id_idx ON public.api_costs_2025_07 USING btree (recommendation_id);


--
-- Name: api_costs_2025_07_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2025_07_request_id_created_at_idx ON public.api_costs_2025_07 USING btree (request_id, created_at);


--
-- Name: api_costs_2025_07_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_session_id_created_at_idx ON public.api_costs_2025_07 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2025_07_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_session_id_node_name_idx ON public.api_costs_2025_07 USING btree (session_id, node_name);


--
-- Name: api_costs_2025_07_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_user_id_created_at_idx ON public.api_costs_2025_07 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_07_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_07_user_id_created_at_idx1 ON public.api_costs_2025_07 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_08_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_contribution_id_idx ON public.api_costs_2025_08 USING btree (contribution_id);


--
-- Name: api_costs_2025_08_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_created_at_idx ON public.api_costs_2025_08 USING btree (created_at DESC);


--
-- Name: api_costs_2025_08_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_created_at_session_id_provider_total_cost_idx ON public.api_costs_2025_08 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2025_08_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_metadata_idx ON public.api_costs_2025_08 USING gin (metadata);


--
-- Name: api_costs_2025_08_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_node_name_idx ON public.api_costs_2025_08 USING btree (node_name);


--
-- Name: api_costs_2025_08_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_phase_idx ON public.api_costs_2025_08 USING btree (phase);


--
-- Name: api_costs_2025_08_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_provider_model_name_idx ON public.api_costs_2025_08 USING btree (provider, model_name);


--
-- Name: api_costs_2025_08_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_recommendation_id_idx ON public.api_costs_2025_08 USING btree (recommendation_id);


--
-- Name: api_costs_2025_08_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2025_08_request_id_created_at_idx ON public.api_costs_2025_08 USING btree (request_id, created_at);


--
-- Name: api_costs_2025_08_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_session_id_created_at_idx ON public.api_costs_2025_08 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2025_08_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_session_id_node_name_idx ON public.api_costs_2025_08 USING btree (session_id, node_name);


--
-- Name: api_costs_2025_08_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_user_id_created_at_idx ON public.api_costs_2025_08 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_08_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_08_user_id_created_at_idx1 ON public.api_costs_2025_08 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_09_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_contribution_id_idx ON public.api_costs_2025_09 USING btree (contribution_id);


--
-- Name: api_costs_2025_09_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_created_at_idx ON public.api_costs_2025_09 USING btree (created_at DESC);


--
-- Name: api_costs_2025_09_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_created_at_session_id_provider_total_cost_idx ON public.api_costs_2025_09 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2025_09_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_metadata_idx ON public.api_costs_2025_09 USING gin (metadata);


--
-- Name: api_costs_2025_09_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_node_name_idx ON public.api_costs_2025_09 USING btree (node_name);


--
-- Name: api_costs_2025_09_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_phase_idx ON public.api_costs_2025_09 USING btree (phase);


--
-- Name: api_costs_2025_09_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_provider_model_name_idx ON public.api_costs_2025_09 USING btree (provider, model_name);


--
-- Name: api_costs_2025_09_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_recommendation_id_idx ON public.api_costs_2025_09 USING btree (recommendation_id);


--
-- Name: api_costs_2025_09_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2025_09_request_id_created_at_idx ON public.api_costs_2025_09 USING btree (request_id, created_at);


--
-- Name: api_costs_2025_09_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_session_id_created_at_idx ON public.api_costs_2025_09 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2025_09_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_session_id_node_name_idx ON public.api_costs_2025_09 USING btree (session_id, node_name);


--
-- Name: api_costs_2025_09_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_user_id_created_at_idx ON public.api_costs_2025_09 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_09_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_09_user_id_created_at_idx1 ON public.api_costs_2025_09 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_10_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_contribution_id_idx ON public.api_costs_2025_10 USING btree (contribution_id);


--
-- Name: api_costs_2025_10_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_created_at_idx ON public.api_costs_2025_10 USING btree (created_at DESC);


--
-- Name: api_costs_2025_10_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_created_at_session_id_provider_total_cost_idx ON public.api_costs_2025_10 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2025_10_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_metadata_idx ON public.api_costs_2025_10 USING gin (metadata);


--
-- Name: api_costs_2025_10_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_node_name_idx ON public.api_costs_2025_10 USING btree (node_name);


--
-- Name: api_costs_2025_10_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_phase_idx ON public.api_costs_2025_10 USING btree (phase);


--
-- Name: api_costs_2025_10_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_provider_model_name_idx ON public.api_costs_2025_10 USING btree (provider, model_name);


--
-- Name: api_costs_2025_10_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_recommendation_id_idx ON public.api_costs_2025_10 USING btree (recommendation_id);


--
-- Name: api_costs_2025_10_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2025_10_request_id_created_at_idx ON public.api_costs_2025_10 USING btree (request_id, created_at);


--
-- Name: api_costs_2025_10_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_session_id_created_at_idx ON public.api_costs_2025_10 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2025_10_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_session_id_node_name_idx ON public.api_costs_2025_10 USING btree (session_id, node_name);


--
-- Name: api_costs_2025_10_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_user_id_created_at_idx ON public.api_costs_2025_10 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_10_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_10_user_id_created_at_idx1 ON public.api_costs_2025_10 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_11_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_contribution_id_idx ON public.api_costs_2025_11 USING btree (contribution_id);


--
-- Name: api_costs_2025_11_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_created_at_idx ON public.api_costs_2025_11 USING btree (created_at DESC);


--
-- Name: api_costs_2025_11_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_created_at_session_id_provider_total_cost_idx ON public.api_costs_2025_11 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2025_11_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_metadata_idx ON public.api_costs_2025_11 USING gin (metadata);


--
-- Name: api_costs_2025_11_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_node_name_idx ON public.api_costs_2025_11 USING btree (node_name);


--
-- Name: api_costs_2025_11_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_phase_idx ON public.api_costs_2025_11 USING btree (phase);


--
-- Name: api_costs_2025_11_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_provider_model_name_idx ON public.api_costs_2025_11 USING btree (provider, model_name);


--
-- Name: api_costs_2025_11_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_recommendation_id_idx ON public.api_costs_2025_11 USING btree (recommendation_id);


--
-- Name: api_costs_2025_11_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2025_11_request_id_created_at_idx ON public.api_costs_2025_11 USING btree (request_id, created_at);


--
-- Name: api_costs_2025_11_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_session_id_created_at_idx ON public.api_costs_2025_11 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2025_11_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_session_id_node_name_idx ON public.api_costs_2025_11 USING btree (session_id, node_name);


--
-- Name: api_costs_2025_11_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_user_id_created_at_idx ON public.api_costs_2025_11 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_11_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_11_user_id_created_at_idx1 ON public.api_costs_2025_11 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_12_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_contribution_id_idx ON public.api_costs_2025_12 USING btree (contribution_id);


--
-- Name: api_costs_2025_12_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_created_at_idx ON public.api_costs_2025_12 USING btree (created_at DESC);


--
-- Name: api_costs_2025_12_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_created_at_session_id_provider_total_cost_idx ON public.api_costs_2025_12 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2025_12_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_metadata_idx ON public.api_costs_2025_12 USING gin (metadata);


--
-- Name: api_costs_2025_12_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_node_name_idx ON public.api_costs_2025_12 USING btree (node_name);


--
-- Name: api_costs_2025_12_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_phase_idx ON public.api_costs_2025_12 USING btree (phase);


--
-- Name: api_costs_2025_12_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_provider_model_name_idx ON public.api_costs_2025_12 USING btree (provider, model_name);


--
-- Name: api_costs_2025_12_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_recommendation_id_idx ON public.api_costs_2025_12 USING btree (recommendation_id);


--
-- Name: api_costs_2025_12_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2025_12_request_id_created_at_idx ON public.api_costs_2025_12 USING btree (request_id, created_at);


--
-- Name: api_costs_2025_12_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_session_id_created_at_idx ON public.api_costs_2025_12 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2025_12_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_session_id_node_name_idx ON public.api_costs_2025_12 USING btree (session_id, node_name);


--
-- Name: api_costs_2025_12_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_user_id_created_at_idx ON public.api_costs_2025_12 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2025_12_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2025_12_user_id_created_at_idx1 ON public.api_costs_2025_12 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2026_01_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_contribution_id_idx ON public.api_costs_2026_01 USING btree (contribution_id);


--
-- Name: api_costs_2026_01_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_created_at_idx ON public.api_costs_2026_01 USING btree (created_at DESC);


--
-- Name: api_costs_2026_01_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_created_at_session_id_provider_total_cost_idx ON public.api_costs_2026_01 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2026_01_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_metadata_idx ON public.api_costs_2026_01 USING gin (metadata);


--
-- Name: api_costs_2026_01_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_node_name_idx ON public.api_costs_2026_01 USING btree (node_name);


--
-- Name: api_costs_2026_01_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_phase_idx ON public.api_costs_2026_01 USING btree (phase);


--
-- Name: api_costs_2026_01_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_provider_model_name_idx ON public.api_costs_2026_01 USING btree (provider, model_name);


--
-- Name: api_costs_2026_01_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_recommendation_id_idx ON public.api_costs_2026_01 USING btree (recommendation_id);


--
-- Name: api_costs_2026_01_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2026_01_request_id_created_at_idx ON public.api_costs_2026_01 USING btree (request_id, created_at);


--
-- Name: api_costs_2026_01_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_session_id_created_at_idx ON public.api_costs_2026_01 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2026_01_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_session_id_node_name_idx ON public.api_costs_2026_01 USING btree (session_id, node_name);


--
-- Name: api_costs_2026_01_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_user_id_created_at_idx ON public.api_costs_2026_01 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2026_01_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_01_user_id_created_at_idx1 ON public.api_costs_2026_01 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2026_02_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_contribution_id_idx ON public.api_costs_2026_02 USING btree (contribution_id);


--
-- Name: api_costs_2026_02_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_created_at_idx ON public.api_costs_2026_02 USING btree (created_at DESC);


--
-- Name: api_costs_2026_02_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_created_at_session_id_provider_total_cost_idx ON public.api_costs_2026_02 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2026_02_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_metadata_idx ON public.api_costs_2026_02 USING gin (metadata);


--
-- Name: api_costs_2026_02_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_node_name_idx ON public.api_costs_2026_02 USING btree (node_name);


--
-- Name: api_costs_2026_02_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_phase_idx ON public.api_costs_2026_02 USING btree (phase);


--
-- Name: api_costs_2026_02_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_provider_model_name_idx ON public.api_costs_2026_02 USING btree (provider, model_name);


--
-- Name: api_costs_2026_02_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_recommendation_id_idx ON public.api_costs_2026_02 USING btree (recommendation_id);


--
-- Name: api_costs_2026_02_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2026_02_request_id_created_at_idx ON public.api_costs_2026_02 USING btree (request_id, created_at);


--
-- Name: api_costs_2026_02_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_session_id_created_at_idx ON public.api_costs_2026_02 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2026_02_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_session_id_node_name_idx ON public.api_costs_2026_02 USING btree (session_id, node_name);


--
-- Name: api_costs_2026_02_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_user_id_created_at_idx ON public.api_costs_2026_02 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2026_02_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_02_user_id_created_at_idx1 ON public.api_costs_2026_02 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2026_03_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_contribution_id_idx ON public.api_costs_2026_03 USING btree (contribution_id);


--
-- Name: api_costs_2026_03_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_created_at_idx ON public.api_costs_2026_03 USING btree (created_at DESC);


--
-- Name: api_costs_2026_03_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_created_at_session_id_provider_total_cost_idx ON public.api_costs_2026_03 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2026_03_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_metadata_idx ON public.api_costs_2026_03 USING gin (metadata);


--
-- Name: api_costs_2026_03_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_node_name_idx ON public.api_costs_2026_03 USING btree (node_name);


--
-- Name: api_costs_2026_03_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_phase_idx ON public.api_costs_2026_03 USING btree (phase);


--
-- Name: api_costs_2026_03_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_provider_model_name_idx ON public.api_costs_2026_03 USING btree (provider, model_name);


--
-- Name: api_costs_2026_03_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_recommendation_id_idx ON public.api_costs_2026_03 USING btree (recommendation_id);


--
-- Name: api_costs_2026_03_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2026_03_request_id_created_at_idx ON public.api_costs_2026_03 USING btree (request_id, created_at);


--
-- Name: api_costs_2026_03_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_session_id_created_at_idx ON public.api_costs_2026_03 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2026_03_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_session_id_node_name_idx ON public.api_costs_2026_03 USING btree (session_id, node_name);


--
-- Name: api_costs_2026_03_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_user_id_created_at_idx ON public.api_costs_2026_03 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2026_03_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_03_user_id_created_at_idx1 ON public.api_costs_2026_03 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2026_04_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_contribution_id_idx ON public.api_costs_2026_04 USING btree (contribution_id);


--
-- Name: api_costs_2026_04_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_created_at_idx ON public.api_costs_2026_04 USING btree (created_at DESC);


--
-- Name: api_costs_2026_04_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_created_at_session_id_provider_total_cost_idx ON public.api_costs_2026_04 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2026_04_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_metadata_idx ON public.api_costs_2026_04 USING gin (metadata);


--
-- Name: api_costs_2026_04_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_node_name_idx ON public.api_costs_2026_04 USING btree (node_name);


--
-- Name: api_costs_2026_04_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_phase_idx ON public.api_costs_2026_04 USING btree (phase);


--
-- Name: api_costs_2026_04_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_provider_model_name_idx ON public.api_costs_2026_04 USING btree (provider, model_name);


--
-- Name: api_costs_2026_04_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_recommendation_id_idx ON public.api_costs_2026_04 USING btree (recommendation_id);


--
-- Name: api_costs_2026_04_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2026_04_request_id_created_at_idx ON public.api_costs_2026_04 USING btree (request_id, created_at);


--
-- Name: api_costs_2026_04_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_session_id_created_at_idx ON public.api_costs_2026_04 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2026_04_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_session_id_node_name_idx ON public.api_costs_2026_04 USING btree (session_id, node_name);


--
-- Name: api_costs_2026_04_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_user_id_created_at_idx ON public.api_costs_2026_04 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2026_04_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_04_user_id_created_at_idx1 ON public.api_costs_2026_04 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2026_05_contribution_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_contribution_id_idx ON public.api_costs_2026_05 USING btree (contribution_id);


--
-- Name: api_costs_2026_05_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_created_at_idx ON public.api_costs_2026_05 USING btree (created_at DESC);


--
-- Name: api_costs_2026_05_created_at_session_id_provider_total_cost_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_created_at_session_id_provider_total_cost_idx ON public.api_costs_2026_05 USING btree (created_at DESC, session_id, provider, total_cost);


--
-- Name: api_costs_2026_05_metadata_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_metadata_idx ON public.api_costs_2026_05 USING gin (metadata);


--
-- Name: api_costs_2026_05_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_node_name_idx ON public.api_costs_2026_05 USING btree (node_name);


--
-- Name: api_costs_2026_05_phase_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_phase_idx ON public.api_costs_2026_05 USING btree (phase);


--
-- Name: api_costs_2026_05_provider_model_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_provider_model_name_idx ON public.api_costs_2026_05 USING btree (provider, model_name);


--
-- Name: api_costs_2026_05_recommendation_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_recommendation_id_idx ON public.api_costs_2026_05 USING btree (recommendation_id);


--
-- Name: api_costs_2026_05_request_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX api_costs_2026_05_request_id_created_at_idx ON public.api_costs_2026_05 USING btree (request_id, created_at);


--
-- Name: api_costs_2026_05_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_session_id_created_at_idx ON public.api_costs_2026_05 USING btree (session_id, created_at DESC);


--
-- Name: api_costs_2026_05_session_id_node_name_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_session_id_node_name_idx ON public.api_costs_2026_05 USING btree (session_id, node_name);


--
-- Name: api_costs_2026_05_user_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_user_id_created_at_idx ON public.api_costs_2026_05 USING btree (user_id, created_at DESC);


--
-- Name: api_costs_2026_05_user_id_created_at_idx1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_costs_2026_05_user_id_created_at_idx1 ON public.api_costs_2026_05 USING btree (user_id, created_at DESC);


--
-- Name: idx_contributions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contributions_created_at ON ONLY public.contributions USING btree (created_at DESC);


--
-- Name: contributions_2025_05_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_05_created_at_idx ON public.contributions_2025_05 USING btree (created_at DESC);


--
-- Name: idx_contributions_persona_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contributions_persona_session ON ONLY public.contributions USING btree (persona_code, session_id);


--
-- Name: contributions_2025_05_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_05_persona_code_session_id_idx ON public.contributions_2025_05 USING btree (persona_code, session_id);


--
-- Name: idx_contributions_round_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contributions_round_number ON ONLY public.contributions USING btree (round_number);


--
-- Name: contributions_2025_05_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_05_round_number_idx ON public.contributions_2025_05 USING btree (round_number);


--
-- Name: idx_contributions_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contributions_session_id ON ONLY public.contributions USING btree (session_id, created_at DESC);


--
-- Name: contributions_2025_05_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_05_session_id_created_at_idx ON public.contributions_2025_05 USING btree (session_id, created_at DESC);


--
-- Name: idx_contributions_session_round; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contributions_session_round ON ONLY public.contributions USING btree (session_id, round_number);


--
-- Name: contributions_2025_05_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_05_session_id_round_number_idx ON public.contributions_2025_05 USING btree (session_id, round_number);


--
-- Name: idx_contributions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contributions_user_id ON ONLY public.contributions USING btree (user_id);


--
-- Name: contributions_2025_05_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_05_user_id_idx ON public.contributions_2025_05 USING btree (user_id);


--
-- Name: contributions_2025_06_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_06_created_at_idx ON public.contributions_2025_06 USING btree (created_at DESC);


--
-- Name: contributions_2025_06_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_06_persona_code_session_id_idx ON public.contributions_2025_06 USING btree (persona_code, session_id);


--
-- Name: contributions_2025_06_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_06_round_number_idx ON public.contributions_2025_06 USING btree (round_number);


--
-- Name: contributions_2025_06_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_06_session_id_created_at_idx ON public.contributions_2025_06 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2025_06_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_06_session_id_round_number_idx ON public.contributions_2025_06 USING btree (session_id, round_number);


--
-- Name: contributions_2025_06_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_06_user_id_idx ON public.contributions_2025_06 USING btree (user_id);


--
-- Name: contributions_2025_07_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_07_created_at_idx ON public.contributions_2025_07 USING btree (created_at DESC);


--
-- Name: contributions_2025_07_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_07_persona_code_session_id_idx ON public.contributions_2025_07 USING btree (persona_code, session_id);


--
-- Name: contributions_2025_07_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_07_round_number_idx ON public.contributions_2025_07 USING btree (round_number);


--
-- Name: contributions_2025_07_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_07_session_id_created_at_idx ON public.contributions_2025_07 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2025_07_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_07_session_id_round_number_idx ON public.contributions_2025_07 USING btree (session_id, round_number);


--
-- Name: contributions_2025_07_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_07_user_id_idx ON public.contributions_2025_07 USING btree (user_id);


--
-- Name: contributions_2025_08_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_08_created_at_idx ON public.contributions_2025_08 USING btree (created_at DESC);


--
-- Name: contributions_2025_08_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_08_persona_code_session_id_idx ON public.contributions_2025_08 USING btree (persona_code, session_id);


--
-- Name: contributions_2025_08_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_08_round_number_idx ON public.contributions_2025_08 USING btree (round_number);


--
-- Name: contributions_2025_08_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_08_session_id_created_at_idx ON public.contributions_2025_08 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2025_08_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_08_session_id_round_number_idx ON public.contributions_2025_08 USING btree (session_id, round_number);


--
-- Name: contributions_2025_08_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_08_user_id_idx ON public.contributions_2025_08 USING btree (user_id);


--
-- Name: contributions_2025_09_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_09_created_at_idx ON public.contributions_2025_09 USING btree (created_at DESC);


--
-- Name: contributions_2025_09_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_09_persona_code_session_id_idx ON public.contributions_2025_09 USING btree (persona_code, session_id);


--
-- Name: contributions_2025_09_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_09_round_number_idx ON public.contributions_2025_09 USING btree (round_number);


--
-- Name: contributions_2025_09_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_09_session_id_created_at_idx ON public.contributions_2025_09 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2025_09_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_09_session_id_round_number_idx ON public.contributions_2025_09 USING btree (session_id, round_number);


--
-- Name: contributions_2025_09_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_09_user_id_idx ON public.contributions_2025_09 USING btree (user_id);


--
-- Name: contributions_2025_10_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_10_created_at_idx ON public.contributions_2025_10 USING btree (created_at DESC);


--
-- Name: contributions_2025_10_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_10_persona_code_session_id_idx ON public.contributions_2025_10 USING btree (persona_code, session_id);


--
-- Name: contributions_2025_10_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_10_round_number_idx ON public.contributions_2025_10 USING btree (round_number);


--
-- Name: contributions_2025_10_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_10_session_id_created_at_idx ON public.contributions_2025_10 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2025_10_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_10_session_id_round_number_idx ON public.contributions_2025_10 USING btree (session_id, round_number);


--
-- Name: contributions_2025_10_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_10_user_id_idx ON public.contributions_2025_10 USING btree (user_id);


--
-- Name: contributions_2025_11_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_11_created_at_idx ON public.contributions_2025_11 USING btree (created_at DESC);


--
-- Name: contributions_2025_11_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_11_persona_code_session_id_idx ON public.contributions_2025_11 USING btree (persona_code, session_id);


--
-- Name: contributions_2025_11_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_11_round_number_idx ON public.contributions_2025_11 USING btree (round_number);


--
-- Name: contributions_2025_11_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_11_session_id_created_at_idx ON public.contributions_2025_11 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2025_11_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_11_session_id_round_number_idx ON public.contributions_2025_11 USING btree (session_id, round_number);


--
-- Name: contributions_2025_11_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_11_user_id_idx ON public.contributions_2025_11 USING btree (user_id);


--
-- Name: contributions_2025_12_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_12_created_at_idx ON public.contributions_2025_12 USING btree (created_at DESC);


--
-- Name: contributions_2025_12_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_12_persona_code_session_id_idx ON public.contributions_2025_12 USING btree (persona_code, session_id);


--
-- Name: contributions_2025_12_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_12_round_number_idx ON public.contributions_2025_12 USING btree (round_number);


--
-- Name: contributions_2025_12_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_12_session_id_created_at_idx ON public.contributions_2025_12 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2025_12_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_12_session_id_round_number_idx ON public.contributions_2025_12 USING btree (session_id, round_number);


--
-- Name: contributions_2025_12_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2025_12_user_id_idx ON public.contributions_2025_12 USING btree (user_id);


--
-- Name: contributions_2026_01_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_01_created_at_idx ON public.contributions_2026_01 USING btree (created_at DESC);


--
-- Name: contributions_2026_01_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_01_persona_code_session_id_idx ON public.contributions_2026_01 USING btree (persona_code, session_id);


--
-- Name: contributions_2026_01_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_01_round_number_idx ON public.contributions_2026_01 USING btree (round_number);


--
-- Name: contributions_2026_01_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_01_session_id_created_at_idx ON public.contributions_2026_01 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2026_01_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_01_session_id_round_number_idx ON public.contributions_2026_01 USING btree (session_id, round_number);


--
-- Name: contributions_2026_01_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_01_user_id_idx ON public.contributions_2026_01 USING btree (user_id);


--
-- Name: contributions_2026_02_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_02_created_at_idx ON public.contributions_2026_02 USING btree (created_at DESC);


--
-- Name: contributions_2026_02_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_02_persona_code_session_id_idx ON public.contributions_2026_02 USING btree (persona_code, session_id);


--
-- Name: contributions_2026_02_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_02_round_number_idx ON public.contributions_2026_02 USING btree (round_number);


--
-- Name: contributions_2026_02_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_02_session_id_created_at_idx ON public.contributions_2026_02 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2026_02_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_02_session_id_round_number_idx ON public.contributions_2026_02 USING btree (session_id, round_number);


--
-- Name: contributions_2026_02_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_02_user_id_idx ON public.contributions_2026_02 USING btree (user_id);


--
-- Name: contributions_2026_03_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_03_created_at_idx ON public.contributions_2026_03 USING btree (created_at DESC);


--
-- Name: contributions_2026_03_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_03_persona_code_session_id_idx ON public.contributions_2026_03 USING btree (persona_code, session_id);


--
-- Name: contributions_2026_03_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_03_round_number_idx ON public.contributions_2026_03 USING btree (round_number);


--
-- Name: contributions_2026_03_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_03_session_id_created_at_idx ON public.contributions_2026_03 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2026_03_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_03_session_id_round_number_idx ON public.contributions_2026_03 USING btree (session_id, round_number);


--
-- Name: contributions_2026_03_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_03_user_id_idx ON public.contributions_2026_03 USING btree (user_id);


--
-- Name: contributions_2026_04_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_04_created_at_idx ON public.contributions_2026_04 USING btree (created_at DESC);


--
-- Name: contributions_2026_04_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_04_persona_code_session_id_idx ON public.contributions_2026_04 USING btree (persona_code, session_id);


--
-- Name: contributions_2026_04_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_04_round_number_idx ON public.contributions_2026_04 USING btree (round_number);


--
-- Name: contributions_2026_04_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_04_session_id_created_at_idx ON public.contributions_2026_04 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2026_04_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_04_session_id_round_number_idx ON public.contributions_2026_04 USING btree (session_id, round_number);


--
-- Name: contributions_2026_04_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_04_user_id_idx ON public.contributions_2026_04 USING btree (user_id);


--
-- Name: contributions_2026_05_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_05_created_at_idx ON public.contributions_2026_05 USING btree (created_at DESC);


--
-- Name: contributions_2026_05_persona_code_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_05_persona_code_session_id_idx ON public.contributions_2026_05 USING btree (persona_code, session_id);


--
-- Name: contributions_2026_05_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_05_round_number_idx ON public.contributions_2026_05 USING btree (round_number);


--
-- Name: contributions_2026_05_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_05_session_id_created_at_idx ON public.contributions_2026_05 USING btree (session_id, created_at DESC);


--
-- Name: contributions_2026_05_session_id_round_number_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_05_session_id_round_number_idx ON public.contributions_2026_05 USING btree (session_id, round_number);


--
-- Name: contributions_2026_05_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX contributions_2026_05_user_id_idx ON public.contributions_2026_05 USING btree (user_id);


--
-- Name: idx_action_deps_action_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_deps_action_id ON public.action_dependencies USING btree (action_id);


--
-- Name: idx_action_deps_depends_on; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_deps_depends_on ON public.action_dependencies USING btree (depends_on_action_id);


--
-- Name: idx_action_tags_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_tags_action ON public.action_tags USING btree (action_id);


--
-- Name: idx_action_tags_tag; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_tags_tag ON public.action_tags USING btree (tag_id);


--
-- Name: idx_action_updates_action_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_updates_action_created ON public.action_updates USING btree (action_id, created_at);


--
-- Name: idx_action_updates_action_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_updates_action_id ON public.action_updates USING btree (action_id);


--
-- Name: idx_action_updates_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_updates_created_at ON public.action_updates USING btree (created_at);


--
-- Name: idx_action_updates_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_updates_type ON public.action_updates USING btree (update_type);


--
-- Name: idx_action_updates_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_action_updates_user_id ON public.action_updates USING btree (user_id);


--
-- Name: idx_actions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_created_at ON public.actions USING btree (created_at);


--
-- Name: idx_actions_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_deleted_at ON public.actions USING btree (deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: idx_actions_estimated_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_estimated_start ON public.actions USING btree (estimated_start_date);


--
-- Name: idx_actions_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_priority ON public.actions USING btree (priority);


--
-- Name: idx_actions_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_project_id ON public.actions USING btree (project_id);


--
-- Name: idx_actions_project_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_project_status ON public.actions USING btree (project_id, status) WHERE (project_id IS NOT NULL);


--
-- Name: idx_actions_replan_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_replan_session ON public.actions USING btree (replan_session_id);


--
-- Name: idx_actions_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_session_id ON public.actions USING btree (source_session_id);


--
-- Name: idx_actions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_status ON public.actions USING btree (status);


--
-- Name: idx_actions_target_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_target_start ON public.actions USING btree (target_start_date);


--
-- Name: idx_actions_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_updated_at ON public.actions USING btree (updated_at);


--
-- Name: idx_actions_user_dates; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_user_dates ON public.actions USING btree (user_id, estimated_start_date, estimated_end_date);


--
-- Name: idx_actions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_user_id ON public.actions USING btree (user_id);


--
-- Name: idx_actions_user_not_deleted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_user_not_deleted ON public.actions USING btree (user_id, deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: idx_actions_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_user_status ON public.actions USING btree (user_id, status);


--
-- Name: idx_actions_user_status_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_actions_user_status_priority ON public.actions USING btree (user_id, status, priority);


--
-- Name: idx_audit_log_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_resource ON public.audit_log USING btree (resource_type, resource_id);


--
-- Name: idx_audit_log_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_timestamp ON public.audit_log USING btree ("timestamp");


--
-- Name: idx_audit_log_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_user_id ON public.audit_log USING btree (user_id);


--
-- Name: idx_beta_whitelist_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_beta_whitelist_email ON public.beta_whitelist USING btree (email);


--
-- Name: idx_business_metrics_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_business_metrics_category ON public.business_metrics USING btree (category);


--
-- Name: idx_business_metrics_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_business_metrics_user_id ON public.business_metrics USING btree (user_id);


--
-- Name: idx_clarifications_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_clarifications_session ON public.session_clarifications USING btree (session_id);


--
-- Name: idx_competitor_profiles_last_enriched; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_competitor_profiles_last_enriched ON public.competitor_profiles USING btree (last_enriched_at);


--
-- Name: idx_competitor_profiles_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_competitor_profiles_user_id ON public.competitor_profiles USING btree (user_id);


--
-- Name: idx_facilitator_decisions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_facilitator_decisions_user_id ON public.facilitator_decisions USING btree (user_id);


--
-- Name: idx_industry_insights_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_industry_insights_active ON public.industry_insights USING btree (industry, insight_type, expires_at);


--
-- Name: idx_industry_insights_type_industry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_industry_insights_type_industry ON public.industry_insights USING btree (insight_type, industry);


--
-- Name: idx_projects_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_created_at ON public.projects USING btree (created_at);


--
-- Name: idx_projects_estimated_end; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_estimated_end ON public.projects USING btree (estimated_end_date);


--
-- Name: idx_projects_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_status ON public.projects USING btree (status);


--
-- Name: idx_projects_target_end; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_target_end ON public.projects USING btree (target_end_date);


--
-- Name: idx_projects_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_updated_at ON public.projects USING btree (updated_at);


--
-- Name: idx_projects_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_user_id ON public.projects USING btree (user_id);


--
-- Name: idx_projects_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_user_status ON public.projects USING btree (user_id, status);


--
-- Name: idx_research_cache_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_research_cache_category ON public.research_cache USING btree (category);


--
-- Name: idx_research_cache_category_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_research_cache_category_date ON public.research_cache USING btree (category, research_date DESC);


--
-- Name: idx_research_cache_embedding_hnsw; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_research_cache_embedding_hnsw ON public.research_cache USING hnsw (question_embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: idx_research_cache_industry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_research_cache_industry ON public.research_cache USING btree (industry);


--
-- Name: idx_research_cache_research_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_research_cache_research_date ON public.research_cache USING btree (research_date DESC);


--
-- Name: idx_research_metrics_depth; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_research_metrics_depth ON public.research_metrics USING btree (research_depth);


--
-- Name: idx_research_metrics_depth_success; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_research_metrics_depth_success ON public.research_metrics USING btree (research_depth, success);


--
-- Name: idx_research_metrics_success; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_research_metrics_success ON public.research_metrics USING btree (success);


--
-- Name: idx_research_metrics_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_research_metrics_timestamp ON public.research_metrics USING btree ("timestamp");


--
-- Name: idx_session_events_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_events_created_at ON ONLY public.session_events USING btree (created_at DESC);


--
-- Name: idx_session_events_data; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_events_data ON ONLY public.session_events USING gin (data);


--
-- Name: idx_session_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_events_event_type ON ONLY public.session_events USING btree (event_type);


--
-- Name: idx_session_events_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_events_session_id ON ONLY public.session_events USING btree (session_id, created_at DESC);


--
-- Name: idx_session_events_session_sequence; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_events_session_sequence ON ONLY public.session_events USING btree (session_id, sequence);


--
-- Name: idx_session_events_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_events_user_id ON ONLY public.session_events USING btree (user_id);


--
-- Name: idx_session_projects_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_projects_project ON public.session_projects USING btree (project_id);


--
-- Name: idx_session_projects_relationship; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_projects_relationship ON public.session_projects USING btree (relationship);


--
-- Name: idx_session_projects_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_projects_session ON public.session_projects USING btree (session_id);


--
-- Name: idx_session_tasks_extracted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_tasks_extracted_at ON public.session_tasks USING btree (extracted_at DESC);


--
-- Name: idx_session_tasks_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_tasks_session_id ON public.session_tasks USING btree (session_id);


--
-- Name: idx_session_tasks_statuses; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_tasks_statuses ON public.session_tasks USING gin (task_statuses);


--
-- Name: idx_session_tasks_tasks; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_tasks_tasks ON public.session_tasks USING gin (tasks);


--
-- Name: idx_session_tasks_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_tasks_user_id ON public.session_tasks USING btree (user_id);


--
-- Name: idx_sessions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_created_at ON public.sessions USING btree (created_at);


--
-- Name: idx_sessions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_status ON public.sessions USING btree (status);


--
-- Name: idx_sessions_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_user_created ON public.sessions USING btree (user_id, created_at DESC);


--
-- Name: idx_sessions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_user_id ON public.sessions USING btree (user_id);


--
-- Name: idx_sessions_user_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_user_status ON public.sessions USING btree (user_id, status);


--
-- Name: idx_sub_problem_results_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sub_problem_results_session_id ON public.sub_problem_results USING btree (session_id);


--
-- Name: idx_sub_problem_results_session_subproblem; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_sub_problem_results_session_subproblem ON public.sub_problem_results USING btree (session_id, sub_problem_index);


--
-- Name: idx_sub_problem_results_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sub_problem_results_user_id ON public.sub_problem_results USING btree (user_id);


--
-- Name: idx_tags_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tags_name ON public.tags USING btree (name);


--
-- Name: idx_tags_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tags_user ON public.tags USING btree (user_id);


--
-- Name: idx_user_context_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_context_user_id ON public.user_context USING btree (user_id);


--
-- Name: idx_user_onboarding_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_onboarding_user_id ON public.user_onboarding USING btree (user_id);


--
-- Name: idx_users_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_deleted_at ON public.users USING btree (deleted_at);


--
-- Name: idx_users_is_locked; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_is_locked ON public.users USING btree (is_locked);


--
-- Name: idx_waitlist_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_waitlist_email ON public.waitlist USING btree (email);


--
-- Name: idx_waitlist_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_waitlist_status ON public.waitlist USING btree (status);


--
-- Name: ix_industry_insights_industry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_industry_insights_industry ON public.industry_insights USING btree (industry);


--
-- Name: ix_session_tasks_sub_problem_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_tasks_sub_problem_index ON public.session_tasks USING btree (sub_problem_index);


--
-- Name: session_events_2025_05_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_05_created_at_idx ON public.session_events_2025_05 USING btree (created_at DESC);


--
-- Name: session_events_2025_05_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_05_data_idx ON public.session_events_2025_05 USING gin (data);


--
-- Name: session_events_2025_05_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_05_event_type_idx ON public.session_events_2025_05 USING btree (event_type);


--
-- Name: session_events_2025_05_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_05_session_id_created_at_idx ON public.session_events_2025_05 USING btree (session_id, created_at DESC);


--
-- Name: unique_session_sequence; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX unique_session_sequence ON ONLY public.session_events USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2025_05_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2025_05_session_id_sequence_created_at_idx ON public.session_events_2025_05 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2025_05_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_05_session_id_sequence_idx ON public.session_events_2025_05 USING btree (session_id, sequence);


--
-- Name: session_events_2025_05_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_05_user_id_idx ON public.session_events_2025_05 USING btree (user_id);


--
-- Name: session_events_2025_06_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_06_created_at_idx ON public.session_events_2025_06 USING btree (created_at DESC);


--
-- Name: session_events_2025_06_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_06_data_idx ON public.session_events_2025_06 USING gin (data);


--
-- Name: session_events_2025_06_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_06_event_type_idx ON public.session_events_2025_06 USING btree (event_type);


--
-- Name: session_events_2025_06_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_06_session_id_created_at_idx ON public.session_events_2025_06 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2025_06_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2025_06_session_id_sequence_created_at_idx ON public.session_events_2025_06 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2025_06_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_06_session_id_sequence_idx ON public.session_events_2025_06 USING btree (session_id, sequence);


--
-- Name: session_events_2025_06_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_06_user_id_idx ON public.session_events_2025_06 USING btree (user_id);


--
-- Name: session_events_2025_07_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_07_created_at_idx ON public.session_events_2025_07 USING btree (created_at DESC);


--
-- Name: session_events_2025_07_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_07_data_idx ON public.session_events_2025_07 USING gin (data);


--
-- Name: session_events_2025_07_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_07_event_type_idx ON public.session_events_2025_07 USING btree (event_type);


--
-- Name: session_events_2025_07_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_07_session_id_created_at_idx ON public.session_events_2025_07 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2025_07_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2025_07_session_id_sequence_created_at_idx ON public.session_events_2025_07 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2025_07_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_07_session_id_sequence_idx ON public.session_events_2025_07 USING btree (session_id, sequence);


--
-- Name: session_events_2025_07_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_07_user_id_idx ON public.session_events_2025_07 USING btree (user_id);


--
-- Name: session_events_2025_08_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_08_created_at_idx ON public.session_events_2025_08 USING btree (created_at DESC);


--
-- Name: session_events_2025_08_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_08_data_idx ON public.session_events_2025_08 USING gin (data);


--
-- Name: session_events_2025_08_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_08_event_type_idx ON public.session_events_2025_08 USING btree (event_type);


--
-- Name: session_events_2025_08_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_08_session_id_created_at_idx ON public.session_events_2025_08 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2025_08_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2025_08_session_id_sequence_created_at_idx ON public.session_events_2025_08 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2025_08_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_08_session_id_sequence_idx ON public.session_events_2025_08 USING btree (session_id, sequence);


--
-- Name: session_events_2025_08_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_08_user_id_idx ON public.session_events_2025_08 USING btree (user_id);


--
-- Name: session_events_2025_09_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_09_created_at_idx ON public.session_events_2025_09 USING btree (created_at DESC);


--
-- Name: session_events_2025_09_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_09_data_idx ON public.session_events_2025_09 USING gin (data);


--
-- Name: session_events_2025_09_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_09_event_type_idx ON public.session_events_2025_09 USING btree (event_type);


--
-- Name: session_events_2025_09_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_09_session_id_created_at_idx ON public.session_events_2025_09 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2025_09_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2025_09_session_id_sequence_created_at_idx ON public.session_events_2025_09 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2025_09_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_09_session_id_sequence_idx ON public.session_events_2025_09 USING btree (session_id, sequence);


--
-- Name: session_events_2025_09_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_09_user_id_idx ON public.session_events_2025_09 USING btree (user_id);


--
-- Name: session_events_2025_10_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_10_created_at_idx ON public.session_events_2025_10 USING btree (created_at DESC);


--
-- Name: session_events_2025_10_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_10_data_idx ON public.session_events_2025_10 USING gin (data);


--
-- Name: session_events_2025_10_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_10_event_type_idx ON public.session_events_2025_10 USING btree (event_type);


--
-- Name: session_events_2025_10_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_10_session_id_created_at_idx ON public.session_events_2025_10 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2025_10_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2025_10_session_id_sequence_created_at_idx ON public.session_events_2025_10 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2025_10_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_10_session_id_sequence_idx ON public.session_events_2025_10 USING btree (session_id, sequence);


--
-- Name: session_events_2025_10_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_10_user_id_idx ON public.session_events_2025_10 USING btree (user_id);


--
-- Name: session_events_2025_11_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_11_created_at_idx ON public.session_events_2025_11 USING btree (created_at DESC);


--
-- Name: session_events_2025_11_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_11_data_idx ON public.session_events_2025_11 USING gin (data);


--
-- Name: session_events_2025_11_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_11_event_type_idx ON public.session_events_2025_11 USING btree (event_type);


--
-- Name: session_events_2025_11_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_11_session_id_created_at_idx ON public.session_events_2025_11 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2025_11_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2025_11_session_id_sequence_created_at_idx ON public.session_events_2025_11 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2025_11_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_11_session_id_sequence_idx ON public.session_events_2025_11 USING btree (session_id, sequence);


--
-- Name: session_events_2025_11_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_11_user_id_idx ON public.session_events_2025_11 USING btree (user_id);


--
-- Name: session_events_2025_12_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_12_created_at_idx ON public.session_events_2025_12 USING btree (created_at DESC);


--
-- Name: session_events_2025_12_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_12_data_idx ON public.session_events_2025_12 USING gin (data);


--
-- Name: session_events_2025_12_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_12_event_type_idx ON public.session_events_2025_12 USING btree (event_type);


--
-- Name: session_events_2025_12_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_12_session_id_created_at_idx ON public.session_events_2025_12 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2025_12_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2025_12_session_id_sequence_created_at_idx ON public.session_events_2025_12 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2025_12_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_12_session_id_sequence_idx ON public.session_events_2025_12 USING btree (session_id, sequence);


--
-- Name: session_events_2025_12_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2025_12_user_id_idx ON public.session_events_2025_12 USING btree (user_id);


--
-- Name: session_events_2026_01_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_01_created_at_idx ON public.session_events_2026_01 USING btree (created_at DESC);


--
-- Name: session_events_2026_01_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_01_data_idx ON public.session_events_2026_01 USING gin (data);


--
-- Name: session_events_2026_01_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_01_event_type_idx ON public.session_events_2026_01 USING btree (event_type);


--
-- Name: session_events_2026_01_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_01_session_id_created_at_idx ON public.session_events_2026_01 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2026_01_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2026_01_session_id_sequence_created_at_idx ON public.session_events_2026_01 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2026_01_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_01_session_id_sequence_idx ON public.session_events_2026_01 USING btree (session_id, sequence);


--
-- Name: session_events_2026_01_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_01_user_id_idx ON public.session_events_2026_01 USING btree (user_id);


--
-- Name: session_events_2026_02_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_02_created_at_idx ON public.session_events_2026_02 USING btree (created_at DESC);


--
-- Name: session_events_2026_02_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_02_data_idx ON public.session_events_2026_02 USING gin (data);


--
-- Name: session_events_2026_02_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_02_event_type_idx ON public.session_events_2026_02 USING btree (event_type);


--
-- Name: session_events_2026_02_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_02_session_id_created_at_idx ON public.session_events_2026_02 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2026_02_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2026_02_session_id_sequence_created_at_idx ON public.session_events_2026_02 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2026_02_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_02_session_id_sequence_idx ON public.session_events_2026_02 USING btree (session_id, sequence);


--
-- Name: session_events_2026_02_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_02_user_id_idx ON public.session_events_2026_02 USING btree (user_id);


--
-- Name: session_events_2026_03_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_03_created_at_idx ON public.session_events_2026_03 USING btree (created_at DESC);


--
-- Name: session_events_2026_03_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_03_data_idx ON public.session_events_2026_03 USING gin (data);


--
-- Name: session_events_2026_03_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_03_event_type_idx ON public.session_events_2026_03 USING btree (event_type);


--
-- Name: session_events_2026_03_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_03_session_id_created_at_idx ON public.session_events_2026_03 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2026_03_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2026_03_session_id_sequence_created_at_idx ON public.session_events_2026_03 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2026_03_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_03_session_id_sequence_idx ON public.session_events_2026_03 USING btree (session_id, sequence);


--
-- Name: session_events_2026_03_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_03_user_id_idx ON public.session_events_2026_03 USING btree (user_id);


--
-- Name: session_events_2026_04_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_04_created_at_idx ON public.session_events_2026_04 USING btree (created_at DESC);


--
-- Name: session_events_2026_04_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_04_data_idx ON public.session_events_2026_04 USING gin (data);


--
-- Name: session_events_2026_04_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_04_event_type_idx ON public.session_events_2026_04 USING btree (event_type);


--
-- Name: session_events_2026_04_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_04_session_id_created_at_idx ON public.session_events_2026_04 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2026_04_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2026_04_session_id_sequence_created_at_idx ON public.session_events_2026_04 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2026_04_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_04_session_id_sequence_idx ON public.session_events_2026_04 USING btree (session_id, sequence);


--
-- Name: session_events_2026_04_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_04_user_id_idx ON public.session_events_2026_04 USING btree (user_id);


--
-- Name: session_events_2026_05_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_05_created_at_idx ON public.session_events_2026_05 USING btree (created_at DESC);


--
-- Name: session_events_2026_05_data_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_05_data_idx ON public.session_events_2026_05 USING gin (data);


--
-- Name: session_events_2026_05_event_type_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_05_event_type_idx ON public.session_events_2026_05 USING btree (event_type);


--
-- Name: session_events_2026_05_session_id_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_05_session_id_created_at_idx ON public.session_events_2026_05 USING btree (session_id, created_at DESC);


--
-- Name: session_events_2026_05_session_id_sequence_created_at_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_events_2026_05_session_id_sequence_created_at_idx ON public.session_events_2026_05 USING btree (session_id, sequence, created_at);


--
-- Name: session_events_2026_05_session_id_sequence_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_05_session_id_sequence_idx ON public.session_events_2026_05 USING btree (session_id, sequence);


--
-- Name: session_events_2026_05_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX session_events_2026_05_user_id_idx ON public.session_events_2026_05 USING btree (user_id);


--
-- Name: api_costs_2025_05_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2025_05_contribution_id_idx;


--
-- Name: api_costs_2025_05_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2025_05_created_at_idx;


--
-- Name: api_costs_2025_05_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2025_05_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2025_05_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2025_05_metadata_idx;


--
-- Name: api_costs_2025_05_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2025_05_node_name_idx;


--
-- Name: api_costs_2025_05_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2025_05_phase_idx;


--
-- Name: api_costs_2025_05_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2025_05_pkey;


--
-- Name: api_costs_2025_05_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2025_05_provider_model_name_idx;


--
-- Name: api_costs_2025_05_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2025_05_recommendation_id_idx;


--
-- Name: api_costs_2025_05_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2025_05_request_id_created_at_idx;


--
-- Name: api_costs_2025_05_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2025_05_session_id_created_at_idx;


--
-- Name: api_costs_2025_05_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2025_05_session_id_node_name_idx;


--
-- Name: api_costs_2025_05_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2025_05_user_id_created_at_idx;


--
-- Name: api_costs_2025_05_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2025_05_user_id_created_at_idx1;


--
-- Name: api_costs_2025_06_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2025_06_contribution_id_idx;


--
-- Name: api_costs_2025_06_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2025_06_created_at_idx;


--
-- Name: api_costs_2025_06_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2025_06_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2025_06_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2025_06_metadata_idx;


--
-- Name: api_costs_2025_06_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2025_06_node_name_idx;


--
-- Name: api_costs_2025_06_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2025_06_phase_idx;


--
-- Name: api_costs_2025_06_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2025_06_pkey;


--
-- Name: api_costs_2025_06_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2025_06_provider_model_name_idx;


--
-- Name: api_costs_2025_06_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2025_06_recommendation_id_idx;


--
-- Name: api_costs_2025_06_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2025_06_request_id_created_at_idx;


--
-- Name: api_costs_2025_06_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2025_06_session_id_created_at_idx;


--
-- Name: api_costs_2025_06_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2025_06_session_id_node_name_idx;


--
-- Name: api_costs_2025_06_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2025_06_user_id_created_at_idx;


--
-- Name: api_costs_2025_06_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2025_06_user_id_created_at_idx1;


--
-- Name: api_costs_2025_07_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2025_07_contribution_id_idx;


--
-- Name: api_costs_2025_07_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2025_07_created_at_idx;


--
-- Name: api_costs_2025_07_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2025_07_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2025_07_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2025_07_metadata_idx;


--
-- Name: api_costs_2025_07_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2025_07_node_name_idx;


--
-- Name: api_costs_2025_07_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2025_07_phase_idx;


--
-- Name: api_costs_2025_07_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2025_07_pkey;


--
-- Name: api_costs_2025_07_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2025_07_provider_model_name_idx;


--
-- Name: api_costs_2025_07_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2025_07_recommendation_id_idx;


--
-- Name: api_costs_2025_07_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2025_07_request_id_created_at_idx;


--
-- Name: api_costs_2025_07_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2025_07_session_id_created_at_idx;


--
-- Name: api_costs_2025_07_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2025_07_session_id_node_name_idx;


--
-- Name: api_costs_2025_07_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2025_07_user_id_created_at_idx;


--
-- Name: api_costs_2025_07_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2025_07_user_id_created_at_idx1;


--
-- Name: api_costs_2025_08_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2025_08_contribution_id_idx;


--
-- Name: api_costs_2025_08_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2025_08_created_at_idx;


--
-- Name: api_costs_2025_08_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2025_08_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2025_08_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2025_08_metadata_idx;


--
-- Name: api_costs_2025_08_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2025_08_node_name_idx;


--
-- Name: api_costs_2025_08_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2025_08_phase_idx;


--
-- Name: api_costs_2025_08_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2025_08_pkey;


--
-- Name: api_costs_2025_08_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2025_08_provider_model_name_idx;


--
-- Name: api_costs_2025_08_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2025_08_recommendation_id_idx;


--
-- Name: api_costs_2025_08_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2025_08_request_id_created_at_idx;


--
-- Name: api_costs_2025_08_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2025_08_session_id_created_at_idx;


--
-- Name: api_costs_2025_08_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2025_08_session_id_node_name_idx;


--
-- Name: api_costs_2025_08_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2025_08_user_id_created_at_idx;


--
-- Name: api_costs_2025_08_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2025_08_user_id_created_at_idx1;


--
-- Name: api_costs_2025_09_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2025_09_contribution_id_idx;


--
-- Name: api_costs_2025_09_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2025_09_created_at_idx;


--
-- Name: api_costs_2025_09_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2025_09_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2025_09_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2025_09_metadata_idx;


--
-- Name: api_costs_2025_09_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2025_09_node_name_idx;


--
-- Name: api_costs_2025_09_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2025_09_phase_idx;


--
-- Name: api_costs_2025_09_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2025_09_pkey;


--
-- Name: api_costs_2025_09_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2025_09_provider_model_name_idx;


--
-- Name: api_costs_2025_09_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2025_09_recommendation_id_idx;


--
-- Name: api_costs_2025_09_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2025_09_request_id_created_at_idx;


--
-- Name: api_costs_2025_09_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2025_09_session_id_created_at_idx;


--
-- Name: api_costs_2025_09_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2025_09_session_id_node_name_idx;


--
-- Name: api_costs_2025_09_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2025_09_user_id_created_at_idx;


--
-- Name: api_costs_2025_09_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2025_09_user_id_created_at_idx1;


--
-- Name: api_costs_2025_10_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2025_10_contribution_id_idx;


--
-- Name: api_costs_2025_10_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2025_10_created_at_idx;


--
-- Name: api_costs_2025_10_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2025_10_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2025_10_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2025_10_metadata_idx;


--
-- Name: api_costs_2025_10_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2025_10_node_name_idx;


--
-- Name: api_costs_2025_10_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2025_10_phase_idx;


--
-- Name: api_costs_2025_10_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2025_10_pkey;


--
-- Name: api_costs_2025_10_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2025_10_provider_model_name_idx;


--
-- Name: api_costs_2025_10_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2025_10_recommendation_id_idx;


--
-- Name: api_costs_2025_10_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2025_10_request_id_created_at_idx;


--
-- Name: api_costs_2025_10_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2025_10_session_id_created_at_idx;


--
-- Name: api_costs_2025_10_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2025_10_session_id_node_name_idx;


--
-- Name: api_costs_2025_10_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2025_10_user_id_created_at_idx;


--
-- Name: api_costs_2025_10_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2025_10_user_id_created_at_idx1;


--
-- Name: api_costs_2025_11_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2025_11_contribution_id_idx;


--
-- Name: api_costs_2025_11_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2025_11_created_at_idx;


--
-- Name: api_costs_2025_11_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2025_11_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2025_11_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2025_11_metadata_idx;


--
-- Name: api_costs_2025_11_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2025_11_node_name_idx;


--
-- Name: api_costs_2025_11_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2025_11_phase_idx;


--
-- Name: api_costs_2025_11_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2025_11_pkey;


--
-- Name: api_costs_2025_11_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2025_11_provider_model_name_idx;


--
-- Name: api_costs_2025_11_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2025_11_recommendation_id_idx;


--
-- Name: api_costs_2025_11_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2025_11_request_id_created_at_idx;


--
-- Name: api_costs_2025_11_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2025_11_session_id_created_at_idx;


--
-- Name: api_costs_2025_11_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2025_11_session_id_node_name_idx;


--
-- Name: api_costs_2025_11_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2025_11_user_id_created_at_idx;


--
-- Name: api_costs_2025_11_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2025_11_user_id_created_at_idx1;


--
-- Name: api_costs_2025_12_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2025_12_contribution_id_idx;


--
-- Name: api_costs_2025_12_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2025_12_created_at_idx;


--
-- Name: api_costs_2025_12_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2025_12_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2025_12_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2025_12_metadata_idx;


--
-- Name: api_costs_2025_12_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2025_12_node_name_idx;


--
-- Name: api_costs_2025_12_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2025_12_phase_idx;


--
-- Name: api_costs_2025_12_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2025_12_pkey;


--
-- Name: api_costs_2025_12_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2025_12_provider_model_name_idx;


--
-- Name: api_costs_2025_12_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2025_12_recommendation_id_idx;


--
-- Name: api_costs_2025_12_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2025_12_request_id_created_at_idx;


--
-- Name: api_costs_2025_12_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2025_12_session_id_created_at_idx;


--
-- Name: api_costs_2025_12_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2025_12_session_id_node_name_idx;


--
-- Name: api_costs_2025_12_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2025_12_user_id_created_at_idx;


--
-- Name: api_costs_2025_12_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2025_12_user_id_created_at_idx1;


--
-- Name: api_costs_2026_01_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2026_01_contribution_id_idx;


--
-- Name: api_costs_2026_01_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2026_01_created_at_idx;


--
-- Name: api_costs_2026_01_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2026_01_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2026_01_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2026_01_metadata_idx;


--
-- Name: api_costs_2026_01_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2026_01_node_name_idx;


--
-- Name: api_costs_2026_01_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2026_01_phase_idx;


--
-- Name: api_costs_2026_01_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2026_01_pkey;


--
-- Name: api_costs_2026_01_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2026_01_provider_model_name_idx;


--
-- Name: api_costs_2026_01_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2026_01_recommendation_id_idx;


--
-- Name: api_costs_2026_01_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2026_01_request_id_created_at_idx;


--
-- Name: api_costs_2026_01_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2026_01_session_id_created_at_idx;


--
-- Name: api_costs_2026_01_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2026_01_session_id_node_name_idx;


--
-- Name: api_costs_2026_01_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2026_01_user_id_created_at_idx;


--
-- Name: api_costs_2026_01_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2026_01_user_id_created_at_idx1;


--
-- Name: api_costs_2026_02_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2026_02_contribution_id_idx;


--
-- Name: api_costs_2026_02_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2026_02_created_at_idx;


--
-- Name: api_costs_2026_02_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2026_02_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2026_02_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2026_02_metadata_idx;


--
-- Name: api_costs_2026_02_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2026_02_node_name_idx;


--
-- Name: api_costs_2026_02_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2026_02_phase_idx;


--
-- Name: api_costs_2026_02_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2026_02_pkey;


--
-- Name: api_costs_2026_02_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2026_02_provider_model_name_idx;


--
-- Name: api_costs_2026_02_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2026_02_recommendation_id_idx;


--
-- Name: api_costs_2026_02_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2026_02_request_id_created_at_idx;


--
-- Name: api_costs_2026_02_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2026_02_session_id_created_at_idx;


--
-- Name: api_costs_2026_02_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2026_02_session_id_node_name_idx;


--
-- Name: api_costs_2026_02_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2026_02_user_id_created_at_idx;


--
-- Name: api_costs_2026_02_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2026_02_user_id_created_at_idx1;


--
-- Name: api_costs_2026_03_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2026_03_contribution_id_idx;


--
-- Name: api_costs_2026_03_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2026_03_created_at_idx;


--
-- Name: api_costs_2026_03_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2026_03_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2026_03_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2026_03_metadata_idx;


--
-- Name: api_costs_2026_03_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2026_03_node_name_idx;


--
-- Name: api_costs_2026_03_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2026_03_phase_idx;


--
-- Name: api_costs_2026_03_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2026_03_pkey;


--
-- Name: api_costs_2026_03_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2026_03_provider_model_name_idx;


--
-- Name: api_costs_2026_03_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2026_03_recommendation_id_idx;


--
-- Name: api_costs_2026_03_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2026_03_request_id_created_at_idx;


--
-- Name: api_costs_2026_03_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2026_03_session_id_created_at_idx;


--
-- Name: api_costs_2026_03_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2026_03_session_id_node_name_idx;


--
-- Name: api_costs_2026_03_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2026_03_user_id_created_at_idx;


--
-- Name: api_costs_2026_03_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2026_03_user_id_created_at_idx1;


--
-- Name: api_costs_2026_04_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2026_04_contribution_id_idx;


--
-- Name: api_costs_2026_04_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2026_04_created_at_idx;


--
-- Name: api_costs_2026_04_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2026_04_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2026_04_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2026_04_metadata_idx;


--
-- Name: api_costs_2026_04_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2026_04_node_name_idx;


--
-- Name: api_costs_2026_04_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2026_04_phase_idx;


--
-- Name: api_costs_2026_04_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2026_04_pkey;


--
-- Name: api_costs_2026_04_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2026_04_provider_model_name_idx;


--
-- Name: api_costs_2026_04_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2026_04_recommendation_id_idx;


--
-- Name: api_costs_2026_04_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2026_04_request_id_created_at_idx;


--
-- Name: api_costs_2026_04_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2026_04_session_id_created_at_idx;


--
-- Name: api_costs_2026_04_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2026_04_session_id_node_name_idx;


--
-- Name: api_costs_2026_04_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2026_04_user_id_created_at_idx;


--
-- Name: api_costs_2026_04_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2026_04_user_id_created_at_idx1;


--
-- Name: api_costs_2026_05_contribution_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_contribution ATTACH PARTITION public.api_costs_2026_05_contribution_id_idx;


--
-- Name: api_costs_2026_05_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_created ATTACH PARTITION public.api_costs_2026_05_created_at_idx;


--
-- Name: api_costs_2026_05_created_at_session_id_provider_total_cost_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_analysis ATTACH PARTITION public.api_costs_2026_05_created_at_session_id_provider_total_cost_idx;


--
-- Name: api_costs_2026_05_metadata_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_metadata ATTACH PARTITION public.api_costs_2026_05_metadata_idx;


--
-- Name: api_costs_2026_05_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_node ATTACH PARTITION public.api_costs_2026_05_node_name_idx;


--
-- Name: api_costs_2026_05_phase_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_phase ATTACH PARTITION public.api_costs_2026_05_phase_idx;


--
-- Name: api_costs_2026_05_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_pkey1 ATTACH PARTITION public.api_costs_2026_05_pkey;


--
-- Name: api_costs_2026_05_provider_model_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_provider ATTACH PARTITION public.api_costs_2026_05_provider_model_name_idx;


--
-- Name: api_costs_2026_05_recommendation_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_recommendation ATTACH PARTITION public.api_costs_2026_05_recommendation_id_idx;


--
-- Name: api_costs_2026_05_request_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.api_costs_request_id_key ATTACH PARTITION public.api_costs_2026_05_request_id_created_at_idx;


--
-- Name: api_costs_2026_05_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session ATTACH PARTITION public.api_costs_2026_05_session_id_created_at_idx;


--
-- Name: api_costs_2026_05_session_id_node_name_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_session_node ATTACH PARTITION public.api_costs_2026_05_session_id_node_name_idx;


--
-- Name: api_costs_2026_05_user_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user ATTACH PARTITION public.api_costs_2026_05_user_id_created_at_idx;


--
-- Name: api_costs_2026_05_user_id_created_at_idx1; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_api_costs_user_created ATTACH PARTITION public.api_costs_2026_05_user_id_created_at_idx1;


--
-- Name: contributions_2025_05_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2025_05_created_at_idx;


--
-- Name: contributions_2025_05_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2025_05_persona_code_session_id_idx;


--
-- Name: contributions_2025_05_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2025_05_pkey;


--
-- Name: contributions_2025_05_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2025_05_round_number_idx;


--
-- Name: contributions_2025_05_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2025_05_session_id_created_at_idx;


--
-- Name: contributions_2025_05_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2025_05_session_id_round_number_idx;


--
-- Name: contributions_2025_05_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2025_05_user_id_idx;


--
-- Name: contributions_2025_06_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2025_06_created_at_idx;


--
-- Name: contributions_2025_06_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2025_06_persona_code_session_id_idx;


--
-- Name: contributions_2025_06_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2025_06_pkey;


--
-- Name: contributions_2025_06_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2025_06_round_number_idx;


--
-- Name: contributions_2025_06_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2025_06_session_id_created_at_idx;


--
-- Name: contributions_2025_06_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2025_06_session_id_round_number_idx;


--
-- Name: contributions_2025_06_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2025_06_user_id_idx;


--
-- Name: contributions_2025_07_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2025_07_created_at_idx;


--
-- Name: contributions_2025_07_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2025_07_persona_code_session_id_idx;


--
-- Name: contributions_2025_07_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2025_07_pkey;


--
-- Name: contributions_2025_07_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2025_07_round_number_idx;


--
-- Name: contributions_2025_07_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2025_07_session_id_created_at_idx;


--
-- Name: contributions_2025_07_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2025_07_session_id_round_number_idx;


--
-- Name: contributions_2025_07_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2025_07_user_id_idx;


--
-- Name: contributions_2025_08_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2025_08_created_at_idx;


--
-- Name: contributions_2025_08_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2025_08_persona_code_session_id_idx;


--
-- Name: contributions_2025_08_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2025_08_pkey;


--
-- Name: contributions_2025_08_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2025_08_round_number_idx;


--
-- Name: contributions_2025_08_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2025_08_session_id_created_at_idx;


--
-- Name: contributions_2025_08_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2025_08_session_id_round_number_idx;


--
-- Name: contributions_2025_08_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2025_08_user_id_idx;


--
-- Name: contributions_2025_09_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2025_09_created_at_idx;


--
-- Name: contributions_2025_09_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2025_09_persona_code_session_id_idx;


--
-- Name: contributions_2025_09_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2025_09_pkey;


--
-- Name: contributions_2025_09_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2025_09_round_number_idx;


--
-- Name: contributions_2025_09_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2025_09_session_id_created_at_idx;


--
-- Name: contributions_2025_09_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2025_09_session_id_round_number_idx;


--
-- Name: contributions_2025_09_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2025_09_user_id_idx;


--
-- Name: contributions_2025_10_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2025_10_created_at_idx;


--
-- Name: contributions_2025_10_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2025_10_persona_code_session_id_idx;


--
-- Name: contributions_2025_10_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2025_10_pkey;


--
-- Name: contributions_2025_10_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2025_10_round_number_idx;


--
-- Name: contributions_2025_10_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2025_10_session_id_created_at_idx;


--
-- Name: contributions_2025_10_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2025_10_session_id_round_number_idx;


--
-- Name: contributions_2025_10_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2025_10_user_id_idx;


--
-- Name: contributions_2025_11_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2025_11_created_at_idx;


--
-- Name: contributions_2025_11_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2025_11_persona_code_session_id_idx;


--
-- Name: contributions_2025_11_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2025_11_pkey;


--
-- Name: contributions_2025_11_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2025_11_round_number_idx;


--
-- Name: contributions_2025_11_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2025_11_session_id_created_at_idx;


--
-- Name: contributions_2025_11_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2025_11_session_id_round_number_idx;


--
-- Name: contributions_2025_11_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2025_11_user_id_idx;


--
-- Name: contributions_2025_12_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2025_12_created_at_idx;


--
-- Name: contributions_2025_12_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2025_12_persona_code_session_id_idx;


--
-- Name: contributions_2025_12_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2025_12_pkey;


--
-- Name: contributions_2025_12_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2025_12_round_number_idx;


--
-- Name: contributions_2025_12_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2025_12_session_id_created_at_idx;


--
-- Name: contributions_2025_12_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2025_12_session_id_round_number_idx;


--
-- Name: contributions_2025_12_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2025_12_user_id_idx;


--
-- Name: contributions_2026_01_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2026_01_created_at_idx;


--
-- Name: contributions_2026_01_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2026_01_persona_code_session_id_idx;


--
-- Name: contributions_2026_01_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2026_01_pkey;


--
-- Name: contributions_2026_01_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2026_01_round_number_idx;


--
-- Name: contributions_2026_01_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2026_01_session_id_created_at_idx;


--
-- Name: contributions_2026_01_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2026_01_session_id_round_number_idx;


--
-- Name: contributions_2026_01_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2026_01_user_id_idx;


--
-- Name: contributions_2026_02_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2026_02_created_at_idx;


--
-- Name: contributions_2026_02_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2026_02_persona_code_session_id_idx;


--
-- Name: contributions_2026_02_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2026_02_pkey;


--
-- Name: contributions_2026_02_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2026_02_round_number_idx;


--
-- Name: contributions_2026_02_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2026_02_session_id_created_at_idx;


--
-- Name: contributions_2026_02_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2026_02_session_id_round_number_idx;


--
-- Name: contributions_2026_02_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2026_02_user_id_idx;


--
-- Name: contributions_2026_03_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2026_03_created_at_idx;


--
-- Name: contributions_2026_03_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2026_03_persona_code_session_id_idx;


--
-- Name: contributions_2026_03_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2026_03_pkey;


--
-- Name: contributions_2026_03_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2026_03_round_number_idx;


--
-- Name: contributions_2026_03_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2026_03_session_id_created_at_idx;


--
-- Name: contributions_2026_03_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2026_03_session_id_round_number_idx;


--
-- Name: contributions_2026_03_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2026_03_user_id_idx;


--
-- Name: contributions_2026_04_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2026_04_created_at_idx;


--
-- Name: contributions_2026_04_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2026_04_persona_code_session_id_idx;


--
-- Name: contributions_2026_04_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2026_04_pkey;


--
-- Name: contributions_2026_04_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2026_04_round_number_idx;


--
-- Name: contributions_2026_04_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2026_04_session_id_created_at_idx;


--
-- Name: contributions_2026_04_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2026_04_session_id_round_number_idx;


--
-- Name: contributions_2026_04_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2026_04_user_id_idx;


--
-- Name: contributions_2026_05_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_created_at ATTACH PARTITION public.contributions_2026_05_created_at_idx;


--
-- Name: contributions_2026_05_persona_code_session_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_persona_session ATTACH PARTITION public.contributions_2026_05_persona_code_session_id_idx;


--
-- Name: contributions_2026_05_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.contributions_pkey1 ATTACH PARTITION public.contributions_2026_05_pkey;


--
-- Name: contributions_2026_05_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_round_number ATTACH PARTITION public.contributions_2026_05_round_number_idx;


--
-- Name: contributions_2026_05_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_id ATTACH PARTITION public.contributions_2026_05_session_id_created_at_idx;


--
-- Name: contributions_2026_05_session_id_round_number_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_session_round ATTACH PARTITION public.contributions_2026_05_session_id_round_number_idx;


--
-- Name: contributions_2026_05_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_contributions_user_id ATTACH PARTITION public.contributions_2026_05_user_id_idx;


--
-- Name: session_events_2025_05_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2025_05_created_at_idx;


--
-- Name: session_events_2025_05_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2025_05_data_idx;


--
-- Name: session_events_2025_05_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2025_05_event_type_idx;


--
-- Name: session_events_2025_05_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2025_05_pkey;


--
-- Name: session_events_2025_05_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2025_05_session_id_created_at_idx;


--
-- Name: session_events_2025_05_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2025_05_session_id_sequence_created_at_idx;


--
-- Name: session_events_2025_05_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2025_05_session_id_sequence_idx;


--
-- Name: session_events_2025_05_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2025_05_user_id_idx;


--
-- Name: session_events_2025_06_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2025_06_created_at_idx;


--
-- Name: session_events_2025_06_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2025_06_data_idx;


--
-- Name: session_events_2025_06_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2025_06_event_type_idx;


--
-- Name: session_events_2025_06_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2025_06_pkey;


--
-- Name: session_events_2025_06_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2025_06_session_id_created_at_idx;


--
-- Name: session_events_2025_06_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2025_06_session_id_sequence_created_at_idx;


--
-- Name: session_events_2025_06_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2025_06_session_id_sequence_idx;


--
-- Name: session_events_2025_06_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2025_06_user_id_idx;


--
-- Name: session_events_2025_07_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2025_07_created_at_idx;


--
-- Name: session_events_2025_07_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2025_07_data_idx;


--
-- Name: session_events_2025_07_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2025_07_event_type_idx;


--
-- Name: session_events_2025_07_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2025_07_pkey;


--
-- Name: session_events_2025_07_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2025_07_session_id_created_at_idx;


--
-- Name: session_events_2025_07_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2025_07_session_id_sequence_created_at_idx;


--
-- Name: session_events_2025_07_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2025_07_session_id_sequence_idx;


--
-- Name: session_events_2025_07_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2025_07_user_id_idx;


--
-- Name: session_events_2025_08_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2025_08_created_at_idx;


--
-- Name: session_events_2025_08_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2025_08_data_idx;


--
-- Name: session_events_2025_08_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2025_08_event_type_idx;


--
-- Name: session_events_2025_08_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2025_08_pkey;


--
-- Name: session_events_2025_08_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2025_08_session_id_created_at_idx;


--
-- Name: session_events_2025_08_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2025_08_session_id_sequence_created_at_idx;


--
-- Name: session_events_2025_08_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2025_08_session_id_sequence_idx;


--
-- Name: session_events_2025_08_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2025_08_user_id_idx;


--
-- Name: session_events_2025_09_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2025_09_created_at_idx;


--
-- Name: session_events_2025_09_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2025_09_data_idx;


--
-- Name: session_events_2025_09_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2025_09_event_type_idx;


--
-- Name: session_events_2025_09_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2025_09_pkey;


--
-- Name: session_events_2025_09_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2025_09_session_id_created_at_idx;


--
-- Name: session_events_2025_09_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2025_09_session_id_sequence_created_at_idx;


--
-- Name: session_events_2025_09_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2025_09_session_id_sequence_idx;


--
-- Name: session_events_2025_09_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2025_09_user_id_idx;


--
-- Name: session_events_2025_10_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2025_10_created_at_idx;


--
-- Name: session_events_2025_10_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2025_10_data_idx;


--
-- Name: session_events_2025_10_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2025_10_event_type_idx;


--
-- Name: session_events_2025_10_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2025_10_pkey;


--
-- Name: session_events_2025_10_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2025_10_session_id_created_at_idx;


--
-- Name: session_events_2025_10_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2025_10_session_id_sequence_created_at_idx;


--
-- Name: session_events_2025_10_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2025_10_session_id_sequence_idx;


--
-- Name: session_events_2025_10_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2025_10_user_id_idx;


--
-- Name: session_events_2025_11_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2025_11_created_at_idx;


--
-- Name: session_events_2025_11_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2025_11_data_idx;


--
-- Name: session_events_2025_11_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2025_11_event_type_idx;


--
-- Name: session_events_2025_11_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2025_11_pkey;


--
-- Name: session_events_2025_11_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2025_11_session_id_created_at_idx;


--
-- Name: session_events_2025_11_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2025_11_session_id_sequence_created_at_idx;


--
-- Name: session_events_2025_11_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2025_11_session_id_sequence_idx;


--
-- Name: session_events_2025_11_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2025_11_user_id_idx;


--
-- Name: session_events_2025_12_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2025_12_created_at_idx;


--
-- Name: session_events_2025_12_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2025_12_data_idx;


--
-- Name: session_events_2025_12_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2025_12_event_type_idx;


--
-- Name: session_events_2025_12_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2025_12_pkey;


--
-- Name: session_events_2025_12_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2025_12_session_id_created_at_idx;


--
-- Name: session_events_2025_12_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2025_12_session_id_sequence_created_at_idx;


--
-- Name: session_events_2025_12_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2025_12_session_id_sequence_idx;


--
-- Name: session_events_2025_12_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2025_12_user_id_idx;


--
-- Name: session_events_2026_01_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2026_01_created_at_idx;


--
-- Name: session_events_2026_01_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2026_01_data_idx;


--
-- Name: session_events_2026_01_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2026_01_event_type_idx;


--
-- Name: session_events_2026_01_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2026_01_pkey;


--
-- Name: session_events_2026_01_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2026_01_session_id_created_at_idx;


--
-- Name: session_events_2026_01_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2026_01_session_id_sequence_created_at_idx;


--
-- Name: session_events_2026_01_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2026_01_session_id_sequence_idx;


--
-- Name: session_events_2026_01_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2026_01_user_id_idx;


--
-- Name: session_events_2026_02_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2026_02_created_at_idx;


--
-- Name: session_events_2026_02_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2026_02_data_idx;


--
-- Name: session_events_2026_02_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2026_02_event_type_idx;


--
-- Name: session_events_2026_02_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2026_02_pkey;


--
-- Name: session_events_2026_02_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2026_02_session_id_created_at_idx;


--
-- Name: session_events_2026_02_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2026_02_session_id_sequence_created_at_idx;


--
-- Name: session_events_2026_02_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2026_02_session_id_sequence_idx;


--
-- Name: session_events_2026_02_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2026_02_user_id_idx;


--
-- Name: session_events_2026_03_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2026_03_created_at_idx;


--
-- Name: session_events_2026_03_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2026_03_data_idx;


--
-- Name: session_events_2026_03_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2026_03_event_type_idx;


--
-- Name: session_events_2026_03_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2026_03_pkey;


--
-- Name: session_events_2026_03_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2026_03_session_id_created_at_idx;


--
-- Name: session_events_2026_03_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2026_03_session_id_sequence_created_at_idx;


--
-- Name: session_events_2026_03_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2026_03_session_id_sequence_idx;


--
-- Name: session_events_2026_03_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2026_03_user_id_idx;


--
-- Name: session_events_2026_04_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2026_04_created_at_idx;


--
-- Name: session_events_2026_04_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2026_04_data_idx;


--
-- Name: session_events_2026_04_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2026_04_event_type_idx;


--
-- Name: session_events_2026_04_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2026_04_pkey;


--
-- Name: session_events_2026_04_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2026_04_session_id_created_at_idx;


--
-- Name: session_events_2026_04_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2026_04_session_id_sequence_created_at_idx;


--
-- Name: session_events_2026_04_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2026_04_session_id_sequence_idx;


--
-- Name: session_events_2026_04_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2026_04_user_id_idx;


--
-- Name: session_events_2026_05_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_created_at ATTACH PARTITION public.session_events_2026_05_created_at_idx;


--
-- Name: session_events_2026_05_data_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_data ATTACH PARTITION public.session_events_2026_05_data_idx;


--
-- Name: session_events_2026_05_event_type_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_event_type ATTACH PARTITION public.session_events_2026_05_event_type_idx;


--
-- Name: session_events_2026_05_pkey; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.session_events_pkey1 ATTACH PARTITION public.session_events_2026_05_pkey;


--
-- Name: session_events_2026_05_session_id_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_id ATTACH PARTITION public.session_events_2026_05_session_id_created_at_idx;


--
-- Name: session_events_2026_05_session_id_sequence_created_at_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.unique_session_sequence ATTACH PARTITION public.session_events_2026_05_session_id_sequence_created_at_idx;


--
-- Name: session_events_2026_05_session_id_sequence_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_session_sequence ATTACH PARTITION public.session_events_2026_05_session_id_sequence_idx;


--
-- Name: session_events_2026_05_user_id_idx; Type: INDEX ATTACH; Schema: public; Owner: -
--

ALTER INDEX public.idx_session_events_user_id ATTACH PARTITION public.session_events_2026_05_user_id_idx;


--
-- Name: beta_whitelist update_beta_whitelist_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_beta_whitelist_updated_at BEFORE UPDATE ON public.beta_whitelist FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: waitlist update_waitlist_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_waitlist_updated_at BEFORE UPDATE ON public.waitlist FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: action_dependencies action_dependencies_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_dependencies
    ADD CONSTRAINT action_dependencies_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id) ON DELETE CASCADE;


--
-- Name: action_dependencies action_dependencies_depends_on_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_dependencies
    ADD CONSTRAINT action_dependencies_depends_on_action_id_fkey FOREIGN KEY (depends_on_action_id) REFERENCES public.actions(id) ON DELETE CASCADE;


--
-- Name: action_tags action_tags_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_tags
    ADD CONSTRAINT action_tags_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id) ON DELETE CASCADE;


--
-- Name: action_tags action_tags_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_tags
    ADD CONSTRAINT action_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.tags(id) ON DELETE CASCADE;


--
-- Name: action_updates action_updates_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_updates
    ADD CONSTRAINT action_updates_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id) ON DELETE CASCADE;


--
-- Name: action_updates action_updates_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.action_updates
    ADD CONSTRAINT action_updates_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: actions actions_source_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT actions_source_session_id_fkey FOREIGN KEY (source_session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: actions actions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT actions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: api_costs api_costs_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE public.api_costs
    ADD CONSTRAINT api_costs_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: api_costs api_costs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE public.api_costs
    ADD CONSTRAINT api_costs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: audit_log audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: business_metrics business_metrics_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.business_metrics
    ADD CONSTRAINT business_metrics_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: competitor_profiles competitor_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitor_profiles
    ADD CONSTRAINT competitor_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: contributions contributions_persona_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE public.contributions
    ADD CONSTRAINT contributions_persona_code_fkey FOREIGN KEY (persona_code) REFERENCES public.personas(code);


--
-- Name: contributions contributions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE public.contributions
    ADD CONSTRAINT contributions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: facilitator_decisions facilitator_decisions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facilitator_decisions
    ADD CONSTRAINT facilitator_decisions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: facilitator_decisions facilitator_decisions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facilitator_decisions
    ADD CONSTRAINT facilitator_decisions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: actions fk_actions_project_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT fk_actions_project_id FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE SET NULL;


--
-- Name: actions fk_actions_replan_session; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT fk_actions_replan_session FOREIGN KEY (replan_session_id) REFERENCES public.sessions(id) ON DELETE SET NULL;


--
-- Name: api_costs fk_api_costs_recommendation_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE public.api_costs
    ADD CONSTRAINT fk_api_costs_recommendation_id FOREIGN KEY (recommendation_id) REFERENCES public.recommendations(id) ON DELETE SET NULL;


--
-- Name: contributions fk_contributions_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE public.contributions
    ADD CONSTRAINT fk_contributions_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: facilitator_decisions fk_facilitator_decisions_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facilitator_decisions
    ADD CONSTRAINT fk_facilitator_decisions_user_id FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: session_events fk_session_events_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE public.session_events
    ADD CONSTRAINT fk_session_events_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: session_tasks fk_session_tasks_session; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_tasks
    ADD CONSTRAINT fk_session_tasks_session FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: session_tasks fk_session_tasks_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_tasks
    ADD CONSTRAINT fk_session_tasks_user_id FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: projects projects_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: session_clarifications session_clarifications_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_clarifications
    ADD CONSTRAINT session_clarifications_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: session_events session_events_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE public.session_events
    ADD CONSTRAINT session_events_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: session_projects session_projects_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_projects
    ADD CONSTRAINT session_projects_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: session_projects session_projects_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_projects
    ADD CONSTRAINT session_projects_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: sub_problem_results sub_problem_results_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sub_problem_results
    ADD CONSTRAINT sub_problem_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.sessions(id) ON DELETE CASCADE;


--
-- Name: sub_problem_results sub_problem_results_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sub_problem_results
    ADD CONSTRAINT sub_problem_results_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tags tags_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_context user_context_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_context
    ADD CONSTRAINT user_context_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_onboarding user_onboarding_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_onboarding
    ADD CONSTRAINT user_onboarding_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: api_costs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.api_costs ENABLE ROW LEVEL SECURITY;

--
-- Name: api_costs api_costs_admin_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY api_costs_admin_access ON public.api_costs FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.users
  WHERE (((users.id)::text = current_setting('app.current_user_id'::text, true)) AND (users.is_admin = true)))));


--
-- Name: api_costs api_costs_user_isolation; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY api_costs_user_isolation ON public.api_costs USING (((user_id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: audit_log; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

--
-- Name: audit_log audit_log_user_isolation; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY audit_log_user_isolation ON public.audit_log USING (((user_id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: business_metrics; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.business_metrics ENABLE ROW LEVEL SECURITY;

--
-- Name: business_metrics business_metrics_own_data; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY business_metrics_own_data ON public.business_metrics USING (((user_id)::text = current_setting('app.current_user_id'::text, true))) WITH CHECK (((user_id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: competitor_profiles; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.competitor_profiles ENABLE ROW LEVEL SECURITY;

--
-- Name: competitor_profiles competitor_profiles_own_data; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY competitor_profiles_own_data ON public.competitor_profiles USING (((user_id)::text = current_setting('app.current_user_id'::text, true))) WITH CHECK (((user_id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: contributions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.contributions ENABLE ROW LEVEL SECURITY;

--
-- Name: contributions contributions_admin_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY contributions_admin_access ON public.contributions FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.users
  WHERE (((users.id)::text = current_setting('app.current_user_id'::text, true)) AND (users.is_admin = true)))));


--
-- Name: contributions contributions_user_isolation; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY contributions_user_isolation ON public.contributions USING (((user_id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: facilitator_decisions facilitator_decisions_admin_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY facilitator_decisions_admin_access ON public.facilitator_decisions FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.users
  WHERE (((users.id)::text = current_setting('app.current_user_id'::text, true)) AND (users.is_admin = true)))));


--
-- Name: facilitator_decisions facilitator_decisions_user_isolation; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY facilitator_decisions_user_isolation ON public.facilitator_decisions USING (((user_id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: industry_insights; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.industry_insights ENABLE ROW LEVEL SECURITY;

--
-- Name: industry_insights industry_insights_read_all; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY industry_insights_read_all ON public.industry_insights FOR SELECT USING (true);


--
-- Name: industry_insights industry_insights_write_system; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY industry_insights_write_system ON public.industry_insights USING ((current_setting('app.current_user_role'::text, true) = 'admin'::text)) WITH CHECK ((current_setting('app.current_user_role'::text, true) = 'admin'::text));


--
-- Name: session_clarifications; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.session_clarifications ENABLE ROW LEVEL SECURITY;

--
-- Name: session_events; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.session_events ENABLE ROW LEVEL SECURITY;

--
-- Name: session_events session_events_admin_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY session_events_admin_access ON public.session_events FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.users
  WHERE (((users.id)::text = current_setting('app.current_user_id'::text, true)) AND (users.is_admin = true)))));


--
-- Name: session_events session_events_user_isolation; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY session_events_user_isolation ON public.session_events USING (((user_id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: session_tasks; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.session_tasks ENABLE ROW LEVEL SECURITY;

--
-- Name: session_tasks session_tasks_admin_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY session_tasks_admin_access ON public.session_tasks FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.users
  WHERE (((users.id)::text = current_setting('app.current_user_id'::text, true)) AND (users.is_admin = true)))));


--
-- Name: session_tasks session_tasks_user_isolation; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY session_tasks_user_isolation ON public.session_tasks USING (((user_id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: sessions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;

--
-- Name: sessions sessions_user_isolation; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY sessions_user_isolation ON public.sessions USING (((user_id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: sub_problem_results; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.sub_problem_results ENABLE ROW LEVEL SECURITY;

--
-- Name: user_context; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.user_context ENABLE ROW LEVEL SECURITY;

--
-- Name: user_onboarding; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.user_onboarding ENABLE ROW LEVEL SECURITY;

--
-- Name: user_onboarding user_onboarding_own_data; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY user_onboarding_own_data ON public.user_onboarding USING (((user_id)::text = current_setting('app.current_user_id'::text, true))) WITH CHECK (((user_id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: users; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

--
-- Name: users users_self_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY users_self_access ON public.users FOR SELECT USING (((id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: users users_self_update; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY users_self_update ON public.users FOR UPDATE USING (((id)::text = current_setting('app.current_user_id'::text, true))) WITH CHECK (((id)::text = current_setting('app.current_user_id'::text, true)));


--
-- Name: users users_system_insert; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY users_system_insert ON public.users FOR INSERT WITH CHECK (true);


--
-- Name: waitlist; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.waitlist ENABLE ROW LEVEL SECURITY;

--
-- Name: waitlist waitlist_admin_only; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY waitlist_admin_only ON public.waitlist USING ((EXISTS ( SELECT 1
   FROM public.users
  WHERE (((users.id)::text = current_setting('app.current_user_id'::text, true)) AND (users.is_admin = true)))));


--
-- PostgreSQL database dump complete
--

\unrestrict LPxdoymx77tGXOzyfacRs4Dtg7Ps6ufLPgY0Nbxau1OBMPFeJc4ufVo3nWkQ2Xb

