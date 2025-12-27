#!/usr/bin/env python3
"""Create the Bo1 analytics use cases blog post.

Run with: docker-compose exec bo1 python -m backend.scripts.create_analytics_article
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bo1.state.database import db_session

# Blog post content
ARTICLE = {
    "title": "Bo1 for Analytics: Make Sense of Your Data with AI Deliberation",
    "excerpt": "Turn spreadsheets and metrics into strategic insights. Bo1 helps you interpret analytics, identify trends, and make data-driven decisions without being a data scientist.",
    "meta_title": "Bo1 for Analytics: AI-Powered Data Insights for Founders",
    "meta_description": "Import your data, ask questions, and get multi-perspective analysis. Bo1 turns your spreadsheets and KPIs into actionable business insights.",
    "content": """# Bo1 for Analytics: Make Sense of Your Data with AI Deliberation

Most founders aren't data scientists. But you're still expected to make data-driven decisions. You have spreadsheets, dashboards, and metrics - but turning those numbers into strategic clarity often feels like guesswork.

Bo1 changes that. By combining data import with multi-agent deliberation, you get AI personas who can analyze your metrics, debate interpretations, and surface insights you might miss on your own.

## Import Your Data, Start Asking Questions

Bo1 supports multiple ways to get your data in:

**CSV/Spreadsheet Upload**: Drop your exported reports directly into Bo1. Sales figures, user metrics, marketing spend - any tabular data becomes queryable.

**Google Sheets Integration**: Connect your live spreadsheets for always-current analysis. Great for ongoing tracking of KPIs you update regularly.

**Digital Ocean Spaces**: For larger datasets or automated pipelines, connect to cloud storage.

Once your data is in, you can ask questions naturally: "What's driving the MRR growth this quarter?" or "Why did churn spike in October?"

## Dataset Q&A: Your Data Analyst on Demand

Bo1's Dataset Q&A mode lets you interrogate your data without writing SQL or building dashboards. Ask questions in plain English and get structured answers.

**Example queries:**

- "Show me the top 10 customers by revenue and their retention rates"
- "What's the correlation between support tickets and churn?"
- "Compare Q3 to Q4 performance across all key metrics"

The AI understands context. If you've set up your business profile in Bo1, it knows your industry benchmarks and can flag when your numbers are outliers.

## Meeting Mode for Analytics Interpretation

Numbers tell part of the story. Interpretation tells the rest.

When you run a Bo1 meeting about your analytics, multiple AI personas examine the same data from different angles:

**The Data Analyst** focuses on statistical significance and data quality. "This trend is based on a sample of 50 users - we need more data before acting."

**The Business Strategist** connects metrics to business outcomes. "The 15% increase in activation rate directly impacts LTV projections."

**The Skeptic** challenges assumptions. "Are we sure this improvement isn't just seasonal? Let's check year-over-year."

**The Operator** thinks about action. "If this trend holds, we should reallocate marketing spend to channel X within two weeks."

This multi-perspective analysis catches blind spots that single-viewpoint analysis misses.

## Real-World Analytics Use Cases

### Churn Analysis

**The question**: "Why are customers leaving and what should we prioritize to improve retention?"

Bo1 analyzes your cohort data, identifies patterns in churned vs. retained customers, and debates which factors are causal vs. correlated. The personas might discover that customers who skip onboarding churn 3x more - but argue about whether to fix onboarding or target different customers.

### Revenue Trend Investigation

**The question**: "Our revenue growth slowed last month. Is this concerning?"

Import your financial data and let Bo1 decompose the growth into components: new vs. expansion vs. churn. The deliberation surfaces whether slowdown is seasonal, market-driven, or execution-related - and recommends investigation priorities.

### Marketing Channel Attribution

**The question**: "Which marketing channels are actually driving conversions?"

Bo1 examines your attribution data with healthy skepticism about last-touch models. The personas debate multi-touch contribution, discuss the difference between lead quality and quantity, and recommend budget reallocation with confidence intervals.

### User Behavior Patterns

**The question**: "What do our most successful users have in common?"

Upload product analytics and let Bo1 identify behavioral clusters. The AI finds patterns like "users who complete feature X in week 1 have 80% higher retention" and debates whether correlation implies actionable causation.

## Mentor Mode for KPI Setup

Not sure which metrics to track? Use Mentor Mode to design your analytics framework.

Ask questions like:
- "What KPIs should a B2B SaaS at our stage track?"
- "How do I set up cohort analysis for a marketplace?"
- "What's a reasonable benchmark for our activation rate?"

The mentor persona walks you through metrics selection, helps you set targets based on industry data, and explains how to instrument tracking.

## From Data to Decisions

The goal isn't just analysis - it's action. After every Bo1 analytics session, you get:

**Summary insights**: Key findings in plain language
**Recommended actions**: Specific next steps with priorities
**Confidence levels**: How certain the conclusions are
**Data gaps**: What additional information would strengthen the analysis

These outputs feed directly into Bo1's Actions system, so analytics insights become tracked tasks.

## Start Analyzing Today

If you've ever felt overwhelmed by your own data, or wondered whether your metrics are telling you the truth, Bo1's analytics capabilities are designed for you.

1. Import your key datasets
2. Ask your burning questions in Dataset Q&A
3. Run a meeting when you need deeper interpretation
4. Use Mentor Mode to level up your analytics practice

Your data has stories to tell. Bo1 helps you hear them.

---

*Bo1 helps founders and small teams make better decisions through AI-assisted multi-agent deliberation. [Start free](https://app.boardof.one)*
""",
}


def create_article(admin_user_id: str = "system") -> int | None:
    """Create the analytics article.

    Args:
        admin_user_id: User ID to assign the article to

    Returns:
        Article ID if created, None if already exists
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Check if article already exists
            cur.execute(
                "SELECT id FROM seo_blog_articles WHERE title = %s",
                (ARTICLE["title"],),
            )
            if cur.fetchone():
                print(f"Article already exists: {ARTICLE['title']}")
                return None

            # Insert article
            cur.execute(
                """
                INSERT INTO seo_blog_articles
                (user_id, title, excerpt, content, meta_title, meta_description, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'draft')
                RETURNING id
                """,
                (
                    admin_user_id,
                    ARTICLE["title"],
                    ARTICLE["excerpt"],
                    ARTICLE["content"],
                    ARTICLE["meta_title"],
                    ARTICLE["meta_description"],
                ),
            )
            row = cur.fetchone()
            article_id = row["id"] if isinstance(row, dict) else row[0]
            conn.commit()
            print(f"Created article id={article_id}: {ARTICLE['title']}")
            return article_id


if __name__ == "__main__":
    create_article()
