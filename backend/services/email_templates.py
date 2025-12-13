"""Email templates for transactional emails.

All templates use simple inline CSS for maximum email client compatibility.
"""

from datetime import date

from backend.services.email import get_unsubscribe_url

# =============================================================================
# Shared Styles
# =============================================================================

BASE_STYLES = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
.container { max-width: 600px; margin: 0 auto; padding: 20px; }
.header { background: #1a1a2e; padding: 30px 20px; text-align: center; }
.header h1 { color: #ffffff; margin: 0; font-size: 24px; font-weight: 600; }
.content { background: #ffffff; padding: 30px 20px; }
.footer { background: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; color: #666; }
.button { display: inline-block; background: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500; margin: 10px 0; }
.button:hover { background: #1d4ed8; }
.action-item { background: #f9fafb; border-left: 4px solid #2563eb; padding: 12px 16px; margin: 10px 0; }
.action-title { font-weight: 600; margin: 0 0 4px 0; }
.action-due { font-size: 14px; color: #666; }
.overdue { border-left-color: #dc2626; }
.due-soon { border-left-color: #f59e0b; }
.summary-box { background: #eff6ff; border-radius: 8px; padding: 20px; margin: 20px 0; }
.summary-title { font-weight: 600; color: #1e40af; margin: 0 0 10px 0; }
ul { margin: 10px 0; padding-left: 20px; }
li { margin: 5px 0; }
"""


def _wrap_email(content: str, user_id: str | None = None, email_type: str = "all") -> str:
    """Wrap content in base email template with header/footer.

    Args:
        content: Main email content HTML
        user_id: User ID for unsubscribe link (optional)
        email_type: Email type for unsubscribe preferences

    Returns:
        Complete HTML email
    """
    unsubscribe_html = ""
    if user_id:
        unsubscribe_url = get_unsubscribe_url(user_id, email_type)
        unsubscribe_html = f'<br><a href="{unsubscribe_url}" style="color: #666;">Unsubscribe</a>'

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{BASE_STYLES}</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>Board of One</h1>
</div>
<div class="content">
{content}
</div>
<div class="footer">
Board of One - AI-powered decision making
{unsubscribe_html}
</div>
</div>
</body>
</html>"""


# =============================================================================
# Welcome Email
# =============================================================================


def render_welcome_email(
    user_name: str | None = None, user_id: str | None = None
) -> tuple[str, str]:
    """Render welcome email for new users.

    Args:
        user_name: User's name (optional)
        user_id: User ID for unsubscribe link

    Returns:
        Tuple of (html_content, plain_text)
    """
    greeting = f"Hi {user_name}," if user_name else "Welcome,"

    content = f"""
<h2>{greeting}</h2>
<p>Welcome to Board of One! You now have access to AI-powered decision making with expert personas that debate and analyze your business challenges.</p>

<div class="summary-box">
<p class="summary-title">Getting Started</p>
<ul>
<li><strong>Ask a question</strong> - Start a new meeting to get expert recommendations on any business decision</li>
<li><strong>Upload data</strong> - Connect spreadsheets or CSVs for data-driven insights</li>
<li><strong>Track actions</strong> - Turn recommendations into actionable tasks with due dates</li>
</ul>
</div>

<p>
<a href="https://boardof.one/dashboard" class="button">Go to Dashboard</a>
</p>

<p>Need help? Reply to this email and we'll get back to you.</p>

<p>Best,<br>The Board of One Team</p>
"""

    html = _wrap_email(content, user_id, "all")

    plain_text = f"""{greeting}

Welcome to Board of One! You now have access to AI-powered decision making with expert personas that debate and analyze your business challenges.

Getting Started:
- Ask a question - Start a new meeting to get expert recommendations
- Upload data - Connect spreadsheets or CSVs for data-driven insights
- Track actions - Turn recommendations into actionable tasks

Go to Dashboard: https://boardof.one/dashboard

Need help? Reply to this email and we'll get back to you.

Best,
The Board of One Team
"""

    return html, plain_text


# =============================================================================
# Meeting Completed Email
# =============================================================================


def render_meeting_completed_email(
    user_id: str,
    problem_statement: str,
    summary: str,
    recommendations: list[str],
    actions: list[dict],
    meeting_url: str,
) -> tuple[str, str]:
    """Render meeting completed email with summary and actions.

    Args:
        user_id: User ID for unsubscribe link
        problem_statement: The original question/problem
        summary: Executive summary of the meeting
        recommendations: List of key recommendations
        actions: List of action dicts with 'title', 'due_date', 'priority'
        meeting_url: URL to view full meeting

    Returns:
        Tuple of (html_content, plain_text)
    """
    # Build recommendations HTML
    recs_html = "".join(f"<li>{rec}</li>" for rec in recommendations[:5])

    # Build actions HTML
    actions_html = ""
    for action in actions[:5]:
        due = action.get("due_date")
        due_str = f"Due: {due}" if due else "No due date"
        priority = action.get("priority", "medium")
        priority_class = "overdue" if priority == "high" else ""
        actions_html += f"""
<div class="action-item {priority_class}">
<p class="action-title">{action.get("title", "Action")}</p>
<p class="action-due">{due_str} | Priority: {priority}</p>
</div>
"""

    content = f"""
<h2>Meeting Complete</h2>
<p><strong>Question:</strong> {problem_statement[:200]}{"..." if len(problem_statement) > 200 else ""}</p>

<div class="summary-box">
<p class="summary-title">Executive Summary</p>
<p>{summary}</p>
</div>

<h3>Key Recommendations</h3>
<ul>
{recs_html}
</ul>

<h3>Action Items</h3>
{actions_html if actions_html else "<p>No action items generated for this meeting.</p>"}

<p>
<a href="{meeting_url}" class="button">View Full Meeting</a>
</p>
"""

    html = _wrap_email(content, user_id, "all")

    # Plain text version
    recs_text = "\n".join(f"  - {rec}" for rec in recommendations[:5])
    actions_text = "\n".join(
        f"  - {a.get('title', 'Action')} (Due: {a.get('due_date', 'TBD')}, Priority: {a.get('priority', 'medium')})"
        for a in actions[:5]
    )

    plain_text = f"""Meeting Complete

Question: {problem_statement[:200]}{"..." if len(problem_statement) > 200 else ""}

Executive Summary:
{summary}

Key Recommendations:
{recs_text}

Action Items:
{actions_text if actions_text else "  No action items generated."}

View Full Meeting: {meeting_url}
"""

    return html, plain_text


# =============================================================================
# Action Reminder Email
# =============================================================================


def render_action_reminder_email(
    user_id: str,
    action_title: str,
    action_description: str,
    due_date: date | str,
    action_url: str,
    is_overdue: bool = False,
) -> tuple[str, str]:
    """Render action due reminder email.

    Args:
        user_id: User ID for unsubscribe link
        action_title: Title of the action
        action_description: Description of what needs to be done
        due_date: When the action is due
        action_url: URL to view/edit the action
        is_overdue: Whether the action is past due

    Returns:
        Tuple of (html_content, plain_text)
    """
    if is_overdue:
        status_text = "is overdue"
        urgency_class = "overdue"
        subject_prefix = "[Overdue]"
    else:
        status_text = "is due tomorrow"
        urgency_class = "due-soon"
        subject_prefix = "[Reminder]"

    due_str = due_date.isoformat() if hasattr(due_date, "isoformat") else str(due_date)

    content = f"""
<h2>Action {status_text}</h2>

<div class="action-item {urgency_class}">
<p class="action-title">{action_title}</p>
<p class="action-due">Due: {due_str}</p>
</div>

<p>{action_description[:500]}{"..." if len(action_description) > 500 else ""}</p>

<p>
<a href="{action_url}" class="button">View Action</a>
</p>
"""

    html = _wrap_email(content, user_id, "reminders")

    plain_text = f"""{subject_prefix} Action {status_text}

{action_title}
Due: {due_str}

{action_description[:500]}{"..." if len(action_description) > 500 else ""}

View Action: {action_url}
"""

    return html, plain_text


# =============================================================================
# Weekly Digest Email
# =============================================================================


def render_weekly_digest_email(
    user_id: str,
    overdue_actions: list[dict],
    upcoming_actions: list[dict],
    completed_count: int,
    meetings_count: int,
) -> tuple[str, str]:
    """Render weekly digest email summarizing activity.

    Args:
        user_id: User ID for unsubscribe link
        overdue_actions: List of overdue action dicts
        upcoming_actions: List of actions due in next 7 days
        completed_count: Number of actions completed this week
        meetings_count: Number of meetings run this week

    Returns:
        Tuple of (html_content, plain_text)
    """
    # Overdue section
    overdue_html = ""
    if overdue_actions:
        items = "".join(
            f'<div class="action-item overdue"><p class="action-title">{a.get("title", "Action")}</p>'
            f'<p class="action-due">Due: {a.get("due_date", "N/A")}</p></div>'
            for a in overdue_actions[:5]
        )
        overdue_html = f"<h3>Overdue Actions ({len(overdue_actions)})</h3>{items}"

    # Upcoming section
    upcoming_html = ""
    if upcoming_actions:
        items = "".join(
            f'<div class="action-item"><p class="action-title">{a.get("title", "Action")}</p>'
            f'<p class="action-due">Due: {a.get("due_date", "N/A")}</p></div>'
            for a in upcoming_actions[:5]
        )
        upcoming_html = f"<h3>Coming Up This Week ({len(upcoming_actions)})</h3>{items}"

    content = f"""
<h2>Your Weekly Summary</h2>

<div class="summary-box">
<p><strong>{completed_count}</strong> actions completed</p>
<p><strong>{meetings_count}</strong> meetings run</p>
<p><strong>{len(overdue_actions)}</strong> actions overdue</p>
</div>

{overdue_html}
{upcoming_html}

<p>
<a href="https://boardof.one/actions" class="button">View All Actions</a>
</p>
"""

    html = _wrap_email(content, user_id, "digest")

    plain_text = f"""Your Weekly Summary

{completed_count} actions completed
{meetings_count} meetings run
{len(overdue_actions)} actions overdue

View All Actions: https://boardof.one/actions
"""

    return html, plain_text


# =============================================================================
# Workspace Invitation Email
# =============================================================================


def render_workspace_invitation_email(
    workspace_name: str,
    inviter_name: str,
    role: str,
    accept_url: str,
    expires_at: date | str | None = None,
) -> tuple[str, str]:
    """Render workspace invitation email.

    Args:
        workspace_name: Name of the workspace
        inviter_name: Name/email of the person who sent the invite
        role: Role being offered (member, admin)
        accept_url: URL to accept the invitation
        expires_at: When the invitation expires

    Returns:
        Tuple of (html_content, plain_text)
    """
    expires_str = ""
    if expires_at:
        if hasattr(expires_at, "strftime"):
            expires_str = expires_at.strftime("%B %d, %Y")
        else:
            expires_str = str(expires_at)[:10]

    role_display = role.replace("_", " ").title()

    content = f"""
<h2>You've been invited to join a workspace</h2>

<p><strong>{inviter_name}</strong> has invited you to join <strong>{workspace_name}</strong> on Board of One.</p>

<div class="summary-box">
<p><strong>Workspace:</strong> {workspace_name}</p>
<p><strong>Role:</strong> {role_display}</p>
{f"<p><strong>Expires:</strong> {expires_str}</p>" if expires_str else ""}
</div>

<p>As a {role_display.lower()}, you'll be able to collaborate on meetings, share data, and track actions together with your team.</p>

<p>
<a href="{accept_url}" class="button">Accept Invitation</a>
</p>

<p style="font-size: 14px; color: #666;">
If you don't want to join this workspace, you can simply ignore this email.
The invitation will expire automatically.
</p>
"""

    html = _wrap_email(content)

    plain_text = f"""You've been invited to join a workspace

{inviter_name} has invited you to join {workspace_name} on Board of One.

Workspace: {workspace_name}
Role: {role_display}
{f"Expires: {expires_str}" if expires_str else ""}

As a {role_display.lower()}, you'll be able to collaborate on meetings, share data, and track actions together with your team.

Accept Invitation: {accept_url}

If you don't want to join this workspace, you can simply ignore this email.
"""

    return html, plain_text
