"""Static DB schema description for LLM context window.

Provides table/column descriptions so the LLM can generate correct SQL
without ever seeing credentials or raw data.
"""

# Concise schema for analytics LLM context — only tables useful for admin queries.
# Format: table(col1 TYPE, col2 TYPE, ...) -- description
SCHEMA_CONTEXT = """
-- Core user & auth tables
users(id TEXT PK, email TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, is_admin BOOL, tier TEXT, stripe_customer_id TEXT) -- all registered users
user_onboarding(user_id TEXT FK→users, completed_at TIMESTAMPTZ, steps_completed JSONB) -- onboarding progress
user_context(id UUID PK, user_id TEXT FK→users, context_type TEXT, content TEXT, created_at TIMESTAMPTZ) -- business context entries
waitlist(id SERIAL PK, email TEXT, status TEXT['pending','approved','rejected'], created_at TIMESTAMPTZ, approved_at TIMESTAMPTZ)
beta_whitelist(id SERIAL PK, email TEXT, created_at TIMESTAMPTZ)
user_auth_providers(user_id TEXT, provider TEXT, provider_user_id TEXT)
user_budget_settings(user_id TEXT PK, monthly_budget NUMERIC, alert_threshold NUMERIC)

-- Session (meeting) tables
sessions(id TEXT PK, user_id TEXT FK→users, status TEXT, problem_statement TEXT, phase TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, total_cost NUMERIC, persona_count INT, round_count INT, model_tier TEXT) -- deliberation sessions/meetings
session_events(id BIGSERIAL PK, session_id TEXT FK→sessions, event_type TEXT, sequence INT, data JSONB, created_at TIMESTAMPTZ) -- event log
session_kills(id SERIAL PK, session_id TEXT, killed_by TEXT, reason TEXT, cost_at_kill NUMERIC, created_at TIMESTAMPTZ)
session_shares(id UUID PK, session_id TEXT FK→sessions, share_token TEXT, created_at TIMESTAMPTZ)
session_clarifications(id UUID PK, session_id TEXT FK→sessions, question TEXT, answer TEXT, created_at TIMESTAMPTZ)

-- Personas & contributions
personas(id UUID PK, session_id TEXT FK→sessions, name TEXT, role TEXT, expertise TEXT, archetype TEXT) -- generated expert personas
contributions(id UUID PK, session_id TEXT FK→sessions, persona_id UUID FK→personas, round INT, content TEXT, phase TEXT, token_count INT, created_at TIMESTAMPTZ)
recommendations(id UUID PK, session_id TEXT FK→sessions, persona_id UUID, recommendation TEXT, confidence NUMERIC, created_at TIMESTAMPTZ)
facilitator_decisions(id UUID PK, session_id TEXT FK→sessions, round INT, decision TEXT, reasoning TEXT, created_at TIMESTAMPTZ)
sub_problem_results(id UUID PK, session_id TEXT FK→sessions, sub_problem_index INT, title TEXT, synthesis TEXT, created_at TIMESTAMPTZ)

-- Cost tracking (partitioned by created_at)
api_costs(id BIGSERIAL PK, session_id TEXT, user_id TEXT, provider TEXT['anthropic','voyage','brave','tavily'], model TEXT, prompt_type TEXT, feature TEXT, cost_category TEXT['user_session','internal_system','seo_content'], total_cost NUMERIC, input_tokens INT, output_tokens INT, cache_read_tokens INT, cache_creation_tokens INT, cache_hit BOOL, total_tokens INT, phase TEXT, sub_problem_index INT, metadata JSONB, created_at TIMESTAMPTZ)
fixed_costs(id SERIAL PK, provider TEXT, description TEXT, monthly_amount_usd NUMERIC, category TEXT, active BOOL, notes TEXT)
daily_cost_summary(date DATE PK, total_cost NUMERIC, by_provider JSONB, request_count INT)

-- Billing & subscriptions
billing_products(id UUID PK, slug TEXT, name TEXT, type TEXT, meetings_monthly INT, active BOOL, display_order INT)
billing_prices(id UUID PK, product_id UUID FK→billing_products, amount_cents INT, currency TEXT, interval TEXT, active BOOL)
user_subscriptions(user_id TEXT, product_slug TEXT, status TEXT, created_at TIMESTAMPTZ)
stripe_events(id TEXT PK, type TEXT, data JSONB, created_at TIMESTAMPTZ)
promotions(id UUID PK, code TEXT, type TEXT, value NUMERIC, max_uses INT, uses_count INT, expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ)
user_promotions(id UUID PK, user_id TEXT, promotion_id UUID FK→promotions, status TEXT, applied_at TIMESTAMPTZ)

-- Feedback & engagement
feedback(id UUID PK, user_id TEXT, type TEXT['feature_request','problem_report'], title TEXT, description TEXT, status TEXT['new','reviewing','resolved','closed'], context JSONB, analysis JSONB, created_at TIMESTAMPTZ)
user_ratings(id UUID PK, session_id TEXT, user_id TEXT, rating INT, comment TEXT, created_at TIMESTAMPTZ)

-- Datasets & analysis
datasets(id UUID PK, user_id TEXT FK→users, name TEXT, status TEXT, row_count INT, column_count INT, created_at TIMESTAMPTZ)
dataset_analyses(id UUID PK, dataset_id UUID FK→datasets, analysis_type TEXT, result JSONB, created_at TIMESTAMPTZ)
dataset_conversations(id UUID PK, dataset_id UUID FK→datasets, user_id TEXT, created_at TIMESTAMPTZ)
dataset_messages(id UUID PK, conversation_id UUID FK→dataset_conversations, role TEXT, content TEXT, created_at TIMESTAMPTZ)

-- Mentor chat
mentor_conversations(id UUID PK, user_id TEXT, persona TEXT, created_at TIMESTAMPTZ)
mentor_messages(id UUID PK, conversation_id UUID FK→mentor_conversations, role TEXT, content TEXT, created_at TIMESTAMPTZ)

-- Blog & SEO
blog_posts(id UUID PK, title TEXT, slug TEXT, content TEXT, status TEXT['draft','scheduled','published'], published_at TIMESTAMPTZ, seo_keywords TEXT[], created_at TIMESTAMPTZ)
published_decisions(id UUID PK, session_id TEXT, category TEXT, slug TEXT, title TEXT, status TEXT['draft','published'], published_at TIMESTAMPTZ, view_count INT, click_through_count INT, homepage_featured BOOL)
seo_blog_articles(id SERIAL PK, title TEXT, slug TEXT, user_id TEXT, view_count INT, click_count INT, signup_count INT, created_at TIMESTAMPTZ)
seo_article_events(id SERIAL PK, article_id INT FK→seo_blog_articles, event_type TEXT, created_at TIMESTAMPTZ)
page_views(id BIGSERIAL PK, path TEXT, visitor_id TEXT, country TEXT, duration_ms INT, scroll_depth NUMERIC, created_at TIMESTAMPTZ)

-- Email
email_log(id SERIAL PK, user_id TEXT, email_type TEXT, subject TEXT, sent_at TIMESTAMPTZ, status TEXT)

-- Experiments
experiments(id UUID PK, name TEXT, status TEXT['draft','running','paused','concluded'], variants JSONB, created_at TIMESTAMPTZ)

-- Research cache
research_cache(id UUID PK, query_hash TEXT, question TEXT, result JSONB, hit_count INT, similarity NUMERIC, created_at TIMESTAMPTZ)

-- Ops & monitoring
error_patterns(id SERIAL PK, pattern_name TEXT, pattern_regex TEXT, error_type TEXT, severity TEXT, enabled BOOL, threshold_count INT, match_count INT)
auto_remediation_log(id SERIAL PK, pattern_name TEXT, fix_type TEXT, triggered_at TIMESTAMPTZ, outcome TEXT, duration_ms INT)
alert_history(id SERIAL PK, alert_type TEXT, severity TEXT, title TEXT, message TEXT, delivered BOOL, created_at TIMESTAMPTZ)

-- Feature flags
feature_flags(id SERIAL PK, key TEXT, default_value BOOL, description TEXT)

-- Projects & actions
projects(id UUID PK, user_id TEXT, name TEXT, status TEXT, created_at TIMESTAMPTZ)
actions(id UUID PK, user_id TEXT, session_id TEXT, title TEXT, status TEXT['todo','in_progress','done','cancelled'], priority TEXT, due_date DATE, created_at TIMESTAMPTZ, completed_at TIMESTAMPTZ)

-- GSC (Google Search Console)
gsc_snapshots(id UUID PK, decision_id UUID, impressions INT, clicks INT, ctr NUMERIC, position NUMERIC, data_date DATE)

-- Workspaces
workspaces(id UUID PK, name TEXT, slug TEXT, owner_id TEXT FK→users, created_at TIMESTAMPTZ)
workspace_members(id UUID PK, workspace_id UUID FK→workspaces, user_id TEXT FK→users, role TEXT, joined_at TIMESTAMPTZ)

-- Admin analytics (self-referential)
admin_analytics_conversations(id UUID PK, admin_user_id TEXT, title TEXT, model_preference TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)
admin_analytics_messages(id UUID PK, conversation_id UUID FK→admin_analytics_conversations, role TEXT['user','assistant'], content TEXT, steps JSONB, suggestions TEXT[], llm_cost NUMERIC(10,6), created_at TIMESTAMPTZ)
admin_saved_analyses(id UUID PK, admin_user_id TEXT, title TEXT, description TEXT, original_question TEXT, steps JSONB, last_run_at TIMESTAMPTZ, last_run_result JSONB, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)
"""


def get_schema_context() -> str:
    """Return the schema context string for LLM prompts."""
    return SCHEMA_CONTEXT.strip()


def get_allowed_table_names() -> list[str]:
    """Extract table names from schema context for validation."""
    import re

    tables = []
    for line in SCHEMA_CONTEXT.strip().split("\n"):
        line = line.strip()
        if line.startswith("--") or not line:
            continue
        match = re.match(r"^(\w+)\(", line)
        if match:
            tables.append(match.group(1))
    return tables
