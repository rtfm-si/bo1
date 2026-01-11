"""Metric calculation question bank.

Maps metric keys to guided Q&A for deriving metric values.
Each metric has 2-4 inputs that combine via formula.
"""

from enum import Enum
from typing import TypedDict


class InputType(str, Enum):
    """Input field type for metric calculation questions."""

    CURRENCY = "currency"  # Dollar amount
    NUMBER = "number"  # Plain number (count)
    PERCENT = "percent"  # Percentage (0-100)


class QuestionDef(TypedDict):
    """Definition of a metric calculation question."""

    id: str
    question: str
    input_type: InputType
    placeholder: str
    help_text: str | None


class MetricFormula(TypedDict):
    """Formula definition for calculating a metric."""

    questions: list[QuestionDef]
    formula: str  # Python expression using question IDs as variables
    result_unit: str  # $, %, months, ratio, count


# =============================================================================
# Metric Question Bank
# =============================================================================

METRIC_QUESTIONS: dict[str, MetricFormula] = {
    # -------------------------------------------------------------------------
    # Financial Metrics
    # -------------------------------------------------------------------------
    "mrr": {
        "questions": [
            {
                "id": "monthly_subscription_revenue",
                "question": "What is your total monthly subscription revenue?",
                "input_type": InputType.CURRENCY,
                "placeholder": "5000",
                "help_text": "Sum of all recurring subscription payments per month",
            },
        ],
        "formula": "monthly_subscription_revenue",
        "result_unit": "$",
    },
    "arr": {
        "questions": [
            {
                "id": "monthly_recurring_revenue",
                "question": "What is your monthly recurring revenue (MRR)?",
                "input_type": InputType.CURRENCY,
                "placeholder": "5000",
                "help_text": "If you know your MRR, we'll multiply by 12",
            },
        ],
        "formula": "monthly_recurring_revenue * 12",
        "result_unit": "$",
    },
    "burn_rate": {
        "questions": [
            {
                "id": "monthly_expenses",
                "question": "What are your total monthly expenses?",
                "input_type": InputType.CURRENCY,
                "placeholder": "25000",
                "help_text": "Include salaries, rent, software, marketing, etc.",
            },
            {
                "id": "monthly_revenue",
                "question": "What is your monthly revenue?",
                "input_type": InputType.CURRENCY,
                "placeholder": "15000",
                "help_text": "Total monthly income from all sources",
            },
        ],
        "formula": "monthly_expenses - monthly_revenue",
        "result_unit": "$",
    },
    "runway": {
        "questions": [
            {
                "id": "cash_balance",
                "question": "What is your current cash balance?",
                "input_type": InputType.CURRENCY,
                "placeholder": "150000",
                "help_text": "Total available cash in bank accounts",
            },
            {
                "id": "monthly_burn",
                "question": "What is your monthly burn rate?",
                "input_type": InputType.CURRENCY,
                "placeholder": "10000",
                "help_text": "Net cash spent per month (expenses minus revenue)",
            },
        ],
        "formula": "cash_balance / monthly_burn if monthly_burn > 0 else 0",
        "result_unit": "months",
    },
    "gross_margin": {
        "questions": [
            {
                "id": "revenue",
                "question": "What is your total revenue?",
                "input_type": InputType.CURRENCY,
                "placeholder": "50000",
                "help_text": "Total income from sales",
            },
            {
                "id": "cogs",
                "question": "What is your cost of goods sold (COGS)?",
                "input_type": InputType.CURRENCY,
                "placeholder": "15000",
                "help_text": "Direct costs to deliver your product/service",
            },
        ],
        "formula": "((revenue - cogs) / revenue * 100) if revenue > 0 else 0",
        "result_unit": "%",
    },
    # -------------------------------------------------------------------------
    # Customer Metrics
    # -------------------------------------------------------------------------
    "churn": {
        "questions": [
            {
                "id": "customers_lost",
                "question": "How many customers did you lose this month?",
                "input_type": InputType.NUMBER,
                "placeholder": "5",
                "help_text": "Customers who canceled or didn't renew",
            },
            {
                "id": "customers_start",
                "question": "How many customers did you have at the start of the month?",
                "input_type": InputType.NUMBER,
                "placeholder": "100",
                "help_text": "Total active customers at month start",
            },
        ],
        "formula": "(customers_lost / customers_start * 100) if customers_start > 0 else 0",
        "result_unit": "%",
    },
    "nps": {
        "questions": [
            {
                "id": "promoters",
                "question": "How many promoters (9-10 rating)?",
                "input_type": InputType.NUMBER,
                "placeholder": "50",
                "help_text": "Customers who rated 9 or 10 out of 10",
            },
            {
                "id": "passives",
                "question": "How many passives (7-8 rating)?",
                "input_type": InputType.NUMBER,
                "placeholder": "30",
                "help_text": "Customers who rated 7 or 8 out of 10",
            },
            {
                "id": "detractors",
                "question": "How many detractors (0-6 rating)?",
                "input_type": InputType.NUMBER,
                "placeholder": "20",
                "help_text": "Customers who rated 0 to 6 out of 10",
            },
        ],
        "formula": "(promoters - detractors) / (promoters + passives + detractors) * 100 if (promoters + passives + detractors) > 0 else 0",
        "result_unit": "score",
    },
    "cac": {
        "questions": [
            {
                "id": "marketing_spend",
                "question": "What was your total marketing/sales spend this month?",
                "input_type": InputType.CURRENCY,
                "placeholder": "10000",
                "help_text": "Include ads, sales salaries, tools, etc.",
            },
            {
                "id": "new_customers",
                "question": "How many new customers did you acquire?",
                "input_type": InputType.NUMBER,
                "placeholder": "25",
                "help_text": "New paying customers this month",
            },
        ],
        "formula": "marketing_spend / new_customers if new_customers > 0 else 0",
        "result_unit": "$",
    },
    "ltv": {
        "questions": [
            {
                "id": "arpu",
                "question": "What is your average revenue per user (ARPU) per month?",
                "input_type": InputType.CURRENCY,
                "placeholder": "50",
                "help_text": "Monthly revenue divided by number of customers",
            },
            {
                "id": "avg_customer_lifetime",
                "question": "What is the average customer lifetime in months?",
                "input_type": InputType.NUMBER,
                "placeholder": "24",
                "help_text": "How long a customer stays on average",
            },
        ],
        "formula": "arpu * avg_customer_lifetime",
        "result_unit": "$",
    },
    "ltv_cac_ratio": {
        "questions": [
            {
                "id": "ltv",
                "question": "What is your customer lifetime value (LTV)?",
                "input_type": InputType.CURRENCY,
                "placeholder": "1200",
                "help_text": "Total revenue from an average customer",
            },
            {
                "id": "cac",
                "question": "What is your customer acquisition cost (CAC)?",
                "input_type": InputType.CURRENCY,
                "placeholder": "400",
                "help_text": "Cost to acquire one new customer",
            },
        ],
        "formula": "ltv / cac if cac > 0 else 0",
        "result_unit": "ratio",
    },
    # -------------------------------------------------------------------------
    # D2C / E-commerce Metrics
    # -------------------------------------------------------------------------
    "aov": {
        "questions": [
            {
                "id": "total_revenue",
                "question": "What was your total revenue this month?",
                "input_type": InputType.CURRENCY,
                "placeholder": "50000",
                "help_text": "Total sales revenue",
            },
            {
                "id": "total_orders",
                "question": "How many orders did you receive?",
                "input_type": InputType.NUMBER,
                "placeholder": "500",
                "help_text": "Total number of orders",
            },
        ],
        "formula": "total_revenue / total_orders if total_orders > 0 else 0",
        "result_unit": "$",
    },
    "conversion_rate": {
        "questions": [
            {
                "id": "conversions",
                "question": "How many conversions (purchases) did you have?",
                "input_type": InputType.NUMBER,
                "placeholder": "100",
                "help_text": "Number of completed purchases",
            },
            {
                "id": "visitors",
                "question": "How many visitors came to your site?",
                "input_type": InputType.NUMBER,
                "placeholder": "5000",
                "help_text": "Total unique visitors",
            },
        ],
        "formula": "(conversions / visitors * 100) if visitors > 0 else 0",
        "result_unit": "%",
    },
    "return_rate": {
        "questions": [
            {
                "id": "returns",
                "question": "How many items were returned?",
                "input_type": InputType.NUMBER,
                "placeholder": "25",
                "help_text": "Number of returned items/orders",
            },
            {
                "id": "total_orders",
                "question": "How many total orders were placed?",
                "input_type": InputType.NUMBER,
                "placeholder": "500",
                "help_text": "Total orders in the same period",
            },
        ],
        "formula": "(returns / total_orders * 100) if total_orders > 0 else 0",
        "result_unit": "%",
    },
}


def get_metric_questions(metric_key: str) -> MetricFormula | None:
    """Get calculation questions for a metric.

    Args:
        metric_key: The metric identifier (e.g., 'mrr', 'churn')

    Returns:
        MetricFormula with questions and formula, or None if not found
    """
    return METRIC_QUESTIONS.get(metric_key)


def get_available_metrics() -> list[str]:
    """Get list of metrics with calculation support."""
    return list(METRIC_QUESTIONS.keys())


def calculate_metric(metric_key: str, answers: dict[str, float]) -> tuple[float, str]:
    """Calculate a metric value from user answers.

    Args:
        metric_key: The metric identifier
        answers: Dict mapping question IDs to numeric values

    Returns:
        Tuple of (calculated_value, formula_used)

    Raises:
        ValueError: If metric not found or calculation fails
    """
    formula_def = METRIC_QUESTIONS.get(metric_key)
    if not formula_def:
        raise ValueError(f"Unknown metric: {metric_key}")

    # Validate all required answers are present
    required_ids = {q["id"] for q in formula_def["questions"]}
    provided_ids = set(answers.keys())
    missing = required_ids - provided_ids
    if missing:
        raise ValueError(f"Missing answers for: {', '.join(missing)}")

    # Safely evaluate the formula
    try:
        # Create a safe namespace with only the answers
        namespace = {k: float(v) for k, v in answers.items()}
        result = eval(formula_def["formula"], {"__builtins__": {}}, namespace)  # noqa: S307
        return round(float(result), 2), formula_def["formula"]
    except ZeroDivisionError:
        return 0.0, formula_def["formula"]
    except Exception as e:
        raise ValueError(f"Calculation failed: {e}") from e
