"""Test data fixtures for load testing.

Contains sample data for:
- Problem statements
- Dataset content (small CSV)
- User context
"""

import io

# Sample problem statements (varied complexity)
PROBLEM_STATEMENTS = [
    # Quick decisions
    "Should we adopt a 4-day work week for the engineering team?",
    "What meeting cadence should we use for the product team?",
    "Should we switch from Slack to Teams?",
    # Strategic decisions
    "Should we expand into the European market this quarter?",
    "What pricing strategy should we adopt for our new SaaS product?",
    "Should we pursue Series A funding or bootstrap longer?",
    # Technical decisions
    "Should we migrate from PostgreSQL to a NoSQL database?",
    "What cloud provider should we use for our infrastructure?",
    "Should we build or buy a CRM solution?",
    # Marketing decisions
    "What marketing channels should we prioritize for Q1?",
    "Should we rebrand our product line?",
    "What content strategy should we adopt for thought leadership?",
]

# Sample business contexts
BUSINESS_CONTEXTS = [
    "We are a B2B SaaS startup with 50 employees. ARR is $2M.",
    "Enterprise software company, 200 employees, profitable.",
    "Early-stage startup, pre-seed, 5 person team.",
    "Mid-size agency with 30 employees, $5M revenue.",
    "Tech consultancy, 15 employees, hybrid remote.",
]

# Sample CSV data for dataset upload tests
SAMPLE_CSV_DATA = """product_id,name,category,price,quantity_sold,date
P001,Widget A,Electronics,29.99,150,2024-01-15
P002,Widget B,Electronics,49.99,75,2024-01-15
P003,Gadget X,Accessories,19.99,200,2024-01-15
P004,Gadget Y,Accessories,24.99,180,2024-01-16
P005,Tool Alpha,Tools,99.99,50,2024-01-16
P006,Tool Beta,Tools,79.99,65,2024-01-17
P007,Widget C,Electronics,39.99,120,2024-01-17
P008,Accessory Z,Accessories,14.99,300,2024-01-18
P009,Tool Gamma,Tools,149.99,30,2024-01-18
P010,Widget D,Electronics,59.99,90,2024-01-19
"""


def get_sample_csv_bytes() -> bytes:
    """Get sample CSV as bytes for upload."""
    return SAMPLE_CSV_DATA.strip().encode("utf-8")


def get_sample_csv_file() -> io.BytesIO:
    """Get sample CSV as file-like object for multipart upload."""
    return io.BytesIO(get_sample_csv_bytes())


# Sample questions for dataset Q&A
DATASET_QUESTIONS = [
    "What is the total revenue?",
    "Which category has the most sales?",
    "What is the average price per category?",
    "Show me the top 5 products by quantity sold.",
    "What was the best selling day?",
]
