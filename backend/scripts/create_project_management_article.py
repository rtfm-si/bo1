#!/usr/bin/env python3
"""Create the Bo1 project management blog post.

Run with: docker-compose exec bo1 python -m backend.scripts.create_project_management_article
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bo1.state.database import db_session

# Blog post content
ARTICLE = {
    "title": "Bo1 for Light-Touch Project Management: Ditch the Complexity",
    "excerpt": "Skip the enterprise PM tools. Bo1 offers simple project planning with AI-assisted scoping, Kanban boards, and Gantt views - without the learning curve.",
    "meta_title": "Bo1 for Project Management: Simple Planning Without the Complexity",
    "meta_description": "Discover how Bo1 replaces heavyweight project management tools with AI-powered planning, Kanban boards, and Gantt charts. Perfect for solo founders and small teams.",
    "content": """# Bo1 for Light-Touch Project Management: Ditch the Complexity

You don't need Jira. You don't need Asana. You don't need a 47-field project template with mandatory status updates and gantt chart dependencies that take longer to maintain than the actual work.

What you need is a way to plan, track, and adapt - without the overhead eating into your building time. That's where Bo1 comes in.

## The Problem with "Real" PM Tools

Enterprise project management tools are built for enterprises. They assume you have:
- A dedicated project manager
- Sprint ceremonies with teams of 10+
- Stakeholders who need weekly status reports
- Time to configure workflows, automations, and integrations

If you're a solo founder or small team, that's not your reality. You need to ship fast, pivot often, and spend zero time on PM overhead.

## Meeting Mode for Project Scoping

Every project starts with ambiguity. What exactly are we building? What's the scope? What are the risks?

Instead of a 2-hour planning meeting with yourself, use Bo1's Meeting Mode:

*"What should be the scope and key milestones for our Q1 product launch?"*

Bo1's AI personas - Product Strategist, Technical Lead, User Advocate, Business Analyst - debate the scope from multiple angles. They challenge assumptions, flag risks, and converge on a realistic plan.

The output? A structured recommendation with clear scope boundaries, prioritized features, and identified dependencies. Not a 50-page project charter - just what you need to start executing.

## Actions System: Your Kanban Board

Once you've scoped the project, Bo1 extracts actionable tasks from your meeting. These flow directly into the Actions system - your built-in Kanban board.

No need to manually create tickets. No context-switching between apps. The AI identifies action items, assigns owners, and sets due dates based on the meeting discussion.

The Kanban view gives you:
- **To Do**: Tasks waiting to be started
- **In Progress**: Active work with visible owners
- **Done**: Completed tasks for that satisfying sense of progress

Drag and drop to update status. Add blockers when you hit obstacles. The AI tracks everything without requiring you to fill out forms.

## Gantt View for Timeline Visibility

Sometimes you need to see the bigger picture. Bo1's Gantt view shows your project timeline at a glance:

- Task durations and dependencies
- Critical path visualization
- Deadline tracking with calendar integration

This isn't a full-featured Microsoft Project replacement. It's the 20% of Gantt functionality that covers 80% of use cases - seeing what depends on what and whether you're on track.

## Mentor Mode for Risk Assessment

Midway through a project, doubts creep in. Are we behind? Should we cut scope? Is this dependency going to block everything?

Mentor Mode is your on-demand project advisor. Ask:

*"We're 3 weeks into a 6-week project and only 30% done. What should we do?"*

The mentor persona analyzes your situation, considers trade-offs, and offers concrete recommendations. Cut this feature. Extend the timeline by X weeks. Bring in this resource.

It's not about generating a risk matrix. It's about getting actionable advice when you need it most.

## Calendar Sync for Deadline Management

Bo1's calendar integration means your action items and project milestones sync directly to Google Calendar. No manual entry. No forgotten deadlines.

When a meeting generates actions with due dates, they appear on your calendar automatically. When you update a deadline in Bo1, your calendar updates too.

Simple, bidirectional, zero friction.

## Real Example: Building a Feature

Here's how a solo founder might use Bo1for a 4-week feature build:

1. **Week 0 - Scoping Meeting**: "What should be the MVP scope for our new analytics dashboard?"
   - Bo1 generates prioritized feature list, flags complexity risks
   - Actions extracted: 12 tasks across design, backend, frontend, testing

2. **Week 1-3 - Execution**: Kanban board tracks daily progress
   - Blockers flagged in real-time
   - Mentor consulted when stuck on architecture decisions

3. **Week 4 - Review Meeting**: "Did we achieve our analytics MVP goals? What's next?"
   - Bo1 assesses delivered vs. planned
   - Generates follow-up actions for post-launch iteration

Total PM overhead: 3 meetings, zero status reports, no Jira configuration.

## Who This Is For

Bo1's light-touch PM works best if you're:

- **A solo founder** who needs structure without bureaucracy
- **A small team (2-5)** coordinating without a dedicated PM
- **An agency** managing client projects with simple timelines
- **A side-project builder** who wants just enough organization

If you need resource leveling across 50 projects, role-based permissions, and audit trails - you need enterprise software. If you need to ship things without PM overhead, you need Bo1.

## Get Started

1. Create a project scoping meeting
2. Let Bo1 extract actions to your Kanban board
3. Use Gantt view for timeline visibility
4. Consult Mentor when you need guidance

That's it. No onboarding calls. No configuration guides. Just planning that gets out of your way.

---

*Bo1 helps founders and small teams make better decisions and track execution without enterprise complexity. [Start free](https://app.boardof.one)*
""",
}


def create_article(admin_user_id: str = "system") -> int | None:
    """Create the project management article.

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
