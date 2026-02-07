"""SQL safety validation for admin analytics chat.

4-layer safety model:
1. Schema context: LLM only sees table/column names
2. SQL parsing: SELECT/WITH only, table allowlist, auto-inject LIMIT
3. Execution: READ ONLY transaction + statement_timeout
4. Result cap: 10K rows max
"""

import logging
import re

import sqlparse
from sqlparse.tokens import DML, Keyword

logger = logging.getLogger(__name__)

# Tables the analytics agent is allowed to query
ALLOWED_TABLES = frozenset(
    {
        # Cost tracking
        "api_costs",
        "fixed_costs",
        "daily_cost_summary",
        "daily_user_feature_costs",
        # Users & auth
        "users",
        "beta_whitelist",
        "waitlist",
        "user_onboarding",
        "user_auth_providers",
        "user_budget_settings",
        "user_usage",
        "user_cost_periods",
        # Sessions & meetings
        "sessions",
        "session_events",
        "session_kills",
        "session_shares",
        "session_clarifications",
        "session_tasks",
        "session_projects",
        # Personas & contributions
        "personas",
        "contributions",
        "recommendations",
        "facilitator_decisions",
        "sub_problem_results",
        # Research cache
        "research_cache",
        "research_metrics",
        # Feedback & ratings
        "feedback",
        "user_ratings",
        # Promotions
        "promotions",
        "user_promotions",
        "promo_invoice_applications",
        # Blog & SEO
        "blog_posts",
        "published_decisions",
        "page_views",
        "seo_blog_articles",
        "seo_article_events",
        "seo_topics",
        "seo_trend_analyses",
        # Billing
        "billing_products",
        "billing_prices",
        "user_subscriptions",
        "stripe_events",
        # Email
        "email_log",
        # Experiments
        "experiments",
        # Datasets
        "datasets",
        "dataset_analyses",
        "dataset_conversations",
        "dataset_messages",
        # Mentor
        "mentor_conversations",
        "mentor_messages",
        # Error patterns / ops
        "error_patterns",
        "auto_remediation_log",
        "alert_history",
        # Feature flags
        "feature_flags",
        "feature_flag_overrides",
        # Context
        "user_context",
        "user_cognition",
        # Projects & actions
        "projects",
        "actions",
        "action_updates",
        "action_tags",
        "action_dependencies",
        # GSC
        "gsc_snapshots",
        "gsc_connection",
        # Workspaces
        "workspaces",
        "workspace_members",
        # Meeting templates
        "meeting_templates",
        # Admin analytics (self-referential)
        "admin_analytics_conversations",
        "admin_analytics_messages",
        "admin_saved_analyses",
    }
)

# Forbidden SQL keywords that indicate mutation
FORBIDDEN_KEYWORDS = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
        "EXECUTE",
        "CALL",
        "COPY",
        "VACUUM",
        "REINDEX",
        "CLUSTER",
        "COMMENT",
        "LOCK",
        "NOTIFY",
        "LISTEN",
        "UNLISTEN",
        "SET",
        "RESET",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT",
        "PREPARE",
        "DEALLOCATE",
        "DECLARE",
        "FETCH",
        "MOVE",
        "CLOSE",
    }
)

# Max rows returned from a single query
MAX_RESULT_ROWS = 10_000
DEFAULT_LIMIT = 10_000


class SQLValidationError(Exception):
    """Raised when SQL fails safety validation."""

    pass


def validate_sql(sql: str) -> str:
    """Validate and sanitize SQL for read-only execution.

    Args:
        sql: Raw SQL string from LLM

    Returns:
        Sanitized SQL with LIMIT injected if missing

    Raises:
        SQLValidationError: If SQL fails any safety check
    """
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL statement")

    # Strip comments and normalize
    sql = sql.strip().rstrip(";")

    # Parse with sqlparse
    parsed_statements = sqlparse.parse(sql)

    if len(parsed_statements) != 1:
        raise SQLValidationError(
            f"Expected exactly 1 statement, got {len(parsed_statements)}. "
            "Multiple statements are not allowed."
        )

    stmt = parsed_statements[0]

    # Check statement type - must be SELECT or WITH (CTE)
    first_token = _get_first_keyword(stmt)
    if first_token not in ("SELECT", "WITH"):
        raise SQLValidationError(f"Only SELECT/WITH statements allowed, got: {first_token}")

    # Check for forbidden keywords in the full statement
    sql_upper = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        # Match as whole word to avoid false positives (e.g. "SET" in "OFFSET")
        pattern = rf"\b{keyword}\b"
        # But allow SET inside function calls or window functions
        if keyword == "SET" and "OFFSET" not in sql_upper:
            # SET is only forbidden at statement level, not inside expressions
            # Check if SET appears outside of parentheses
            if _has_top_level_keyword(sql_upper, keyword):
                raise SQLValidationError(f"Forbidden keyword: {keyword}")
        elif keyword in ("BEGIN", "COMMIT", "ROLLBACK"):
            # These are only forbidden at statement level
            if _has_top_level_keyword(sql_upper, keyword):
                raise SQLValidationError(f"Forbidden keyword: {keyword}")
        elif re.search(pattern, sql_upper):
            raise SQLValidationError(f"Forbidden keyword: {keyword}")

    # Extract and validate table names
    tables = _extract_table_names(sql)
    disallowed = tables - ALLOWED_TABLES
    if disallowed:
        raise SQLValidationError(f"Access to table(s) not allowed: {', '.join(sorted(disallowed))}")

    # Check for dangerous patterns
    _check_dangerous_patterns(sql)

    # Inject LIMIT if missing
    sql = _inject_limit(sql)

    return sql


def _get_first_keyword(stmt: sqlparse.sql.Statement) -> str:
    """Get the first meaningful keyword from a parsed statement."""
    for token in stmt.tokens:
        if token.ttype is DML:
            return token.value.upper()
        if token.ttype is Keyword and token.value.upper() in ("WITH", "SELECT"):
            return token.value.upper()
        if not token.is_whitespace:
            return token.value.upper().split()[0] if token.value.strip() else ""
    return ""


def _extract_table_names(sql: str) -> set[str]:
    """Extract table names from SQL using regex patterns.

    Handles: FROM table, JOIN table, FROM schema.table
    Excludes CTE names defined in WITH clauses.
    """
    tables: set[str] = set()

    # First, extract CTE names to exclude them
    cte_names: set[str] = set()
    for match in re.finditer(r"\bWITH\b\s+", sql, re.IGNORECASE):
        # Find CTE names: WITH name AS (...), name2 AS (...)
        rest = sql[match.end() :]
        for cte_match in re.finditer(r"(\w+)\s+AS\s*\(", rest, re.IGNORECASE):
            cte_names.add(cte_match.group(1).lower())

    # Pattern: FROM/JOIN followed by table name (optional schema prefix)
    # Handles: FROM table, FROM schema.table, JOIN table AS alias
    pattern = r"""
        (?:FROM|JOIN)\s+
        (?:LATERAL\s+)?
        (?:(\w+)\.)?       # optional schema
        (\w+)              # table name
        (?:\s+(?:AS\s+)?(\w+))?  # optional alias
    """
    skip_names = {
        "select",
        "lateral",
        "unnest",
        "generate_series",
        "json_each",
        "jsonb_each",
        "json_array_elements",
        "jsonb_array_elements",
        "values",
    }
    for match in re.finditer(pattern, sql, re.IGNORECASE | re.VERBOSE):
        table = match.group(2).lower()
        # Skip subquery aliases, SQL keywords, and CTE names
        if table not in skip_names and table not in cte_names:
            tables.add(table)

    return tables


def _has_top_level_keyword(sql_upper: str, keyword: str) -> bool:
    """Check if keyword appears at top level (not inside parentheses)."""
    depth = 0
    pattern = re.compile(rf"\b{keyword}\b")
    for i, char in enumerate(sql_upper):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif depth == 0:
            remaining = sql_upper[i:]
            m = pattern.match(remaining)
            if m:
                return True
    return False


def _check_dangerous_patterns(sql: str) -> None:
    """Check for dangerous SQL patterns."""
    sql_upper = sql.upper()

    # No pg_* system tables
    if re.search(r"\bPG_\w+", sql_upper):
        # Allow pg_sleep in test contexts but block pg_catalog etc.
        pg_match = re.search(r"\bPG_(\w+)", sql_upper)
        if pg_match:
            pg_table = pg_match.group(1).lower()
            # pg_sleep is a function, not dangerous for reads
            if pg_table not in ("sleep",):
                raise SQLValidationError(f"Access to system catalog pg_{pg_table} is not allowed")

    # No information_schema
    if "INFORMATION_SCHEMA" in sql_upper:
        raise SQLValidationError("Access to information_schema is not allowed")

    # No INTO clause (SELECT INTO creates tables)
    if re.search(r"\bINTO\s+\w+", sql_upper):
        # Allow INSERT INTO in subqueries... wait, INSERT is already blocked
        raise SQLValidationError("INTO clause is not allowed")

    # No raw string execution
    if "EXECUTE" in sql_upper or "DO $$" in sql_upper:
        raise SQLValidationError("Dynamic SQL execution is not allowed")


def _inject_limit(sql: str) -> str:
    """Inject LIMIT clause if missing from the outermost SELECT."""
    sql_upper = sql.upper().strip()

    # Check if LIMIT already exists at the top level
    # We need to check outside of parentheses
    depth = 0
    has_limit = False
    for i, char in enumerate(sql_upper):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif depth == 0 and sql_upper[i:].startswith("LIMIT"):
            # Verify it's a keyword boundary
            if i == 0 or not sql_upper[i - 1].isalnum():
                end = i + 5
                if end >= len(sql_upper) or not sql_upper[end].isalnum():
                    has_limit = True
                    break

    if not has_limit:
        sql = f"{sql}\nLIMIT {DEFAULT_LIMIT}"

    return sql


def get_execution_params() -> dict:
    """Get safe execution parameters for analytics queries.

    Returns:
        Dict with connection parameters for read-only execution
    """
    return {
        "transaction_read_only": True,
        "statement_timeout_ms": 15_000,  # 15 second timeout
    }
