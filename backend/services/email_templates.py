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


# =============================================================================
# Workspace Join Request Email
# =============================================================================


def render_join_request_email(
    workspace_name: str,
    requester_email: str,
    message: str | None = None,
) -> tuple[str, str]:
    """Render email notifying admins of a new join request.

    Args:
        workspace_name: Name of the workspace
        requester_email: Email of the user requesting to join
        message: Optional message from the requester

    Returns:
        Tuple of (subject, html_content)
    """
    message_html = ""
    if message:
        message_html = f"""
<div class="summary-box">
<p class="summary-title">Message from {requester_email}</p>
<p>{message}</p>
</div>
"""

    content = f"""
<h2>New Join Request</h2>

<p><strong>{requester_email}</strong> has requested to join <strong>{workspace_name}</strong>.</p>

{message_html}

<p>You can review and respond to this request from the workspace settings.</p>

<p>
<a href="https://boardof.one/settings/workspace" class="button">Review Request</a>
</p>
"""

    html = _wrap_email(content)

    subject = f"[Board of One] Join request for {workspace_name}"

    return subject, html


def render_join_approved_email(
    workspace_name: str,
) -> tuple[str, str]:
    """Render email notifying user their join request was approved.

    Args:
        workspace_name: Name of the workspace

    Returns:
        Tuple of (subject, html_content)
    """
    content = f"""
<h2>Join Request Approved</h2>

<p>Great news! Your request to join <strong>{workspace_name}</strong> has been approved.</p>

<p>You can now access the workspace and collaborate with your team.</p>

<p>
<a href="https://boardof.one/dashboard" class="button">Go to Dashboard</a>
</p>
"""

    html = _wrap_email(content)

    subject = f"[Board of One] You've been added to {workspace_name}"

    return subject, html


def render_join_rejected_email(
    workspace_name: str,
    reason: str | None = None,
) -> tuple[str, str]:
    """Render email notifying user their join request was rejected.

    Args:
        workspace_name: Name of the workspace
        reason: Optional reason for rejection

    Returns:
        Tuple of (subject, html_content)
    """
    reason_html = ""
    if reason:
        reason_html = f"""
<div class="summary-box">
<p class="summary-title">Reason</p>
<p>{reason}</p>
</div>
"""

    content = f"""
<h2>Join Request Not Approved</h2>

<p>Your request to join <strong>{workspace_name}</strong> was not approved.</p>

{reason_html}

<p>If you believe this was a mistake, please contact the workspace administrator directly.</p>
"""

    html = _wrap_email(content)

    subject = f"[Board of One] Update on your request to join {workspace_name}"

    return subject, html


# =============================================================================
# Workspace Role Change Emails
# =============================================================================


def render_ownership_transferred_email(
    workspace_name: str,
    is_new_owner: bool,
) -> tuple[str, str]:
    """Render email notifying about ownership transfer.

    Args:
        workspace_name: Name of the workspace
        is_new_owner: True if recipient is the new owner, False if old owner

    Returns:
        Tuple of (subject, html_content)
    """
    if is_new_owner:
        content = f"""
<h2>You are now the owner of {workspace_name}</h2>

<p>Ownership of <strong>{workspace_name}</strong> has been transferred to you.</p>

<div class="summary-box">
<p class="summary-title">What this means</p>
<ul>
<li>You have full control over the workspace settings</li>
<li>You can manage all members and their roles</li>
<li>You can transfer ownership to another member</li>
<li>You manage the workspace billing</li>
</ul>
</div>

<p>
<a href="https://boardof.one/settings/workspace" class="button">Manage Workspace</a>
</p>
"""
        subject = f"[Board of One] You are now owner of {workspace_name}"
    else:
        content = f"""
<h2>Ownership of {workspace_name} has been transferred</h2>

<p>You have transferred ownership of <strong>{workspace_name}</strong>.</p>

<p>Your role has been changed to <strong>Admin</strong>. You still have administrative access to manage members and workspace settings, but ownership now belongs to the new owner.</p>

<div class="summary-box">
<p class="summary-title">As an Admin, you can still</p>
<ul>
<li>Manage workspace members</li>
<li>Edit workspace settings</li>
<li>Create and manage meetings, actions, and data</li>
</ul>
</div>
"""
        subject = f"[Board of One] Ownership transferred for {workspace_name}"

    html = _wrap_email(content)

    return subject, html


def render_role_changed_email(
    workspace_name: str,
    old_role: str,
    new_role: str,
) -> tuple[str, str]:
    """Render email notifying user of role change.

    Args:
        workspace_name: Name of the workspace
        old_role: Previous role
        new_role: New role

    Returns:
        Tuple of (subject, html_content)
    """
    is_promotion = new_role == "admin" and old_role == "member"

    if is_promotion:
        content = f"""
<h2>You've been promoted to Admin</h2>

<p>Your role in <strong>{workspace_name}</strong> has been changed from <strong>Member</strong> to <strong>Admin</strong>.</p>

<div class="summary-box">
<p class="summary-title">What this means</p>
<ul>
<li>You can now invite and manage workspace members</li>
<li>You can approve or reject join requests</li>
<li>You can edit workspace settings</li>
</ul>
</div>

<p>
<a href="https://boardof.one/settings/workspace" class="button">Manage Workspace</a>
</p>
"""
        subject = f"[Board of One] You're now an Admin of {workspace_name}"
    else:
        # Demotion
        content = f"""
<h2>Your role has been updated</h2>

<p>Your role in <strong>{workspace_name}</strong> has been changed from <strong>{old_role.title()}</strong> to <strong>{new_role.title()}</strong>.</p>

<p>You still have full access to create meetings, manage actions, and collaborate with your team in this workspace.</p>

<p>
<a href="https://boardof.one/dashboard" class="button">Go to Dashboard</a>
</p>
"""
        subject = f"[Board of One] Your role in {workspace_name} has changed"

    html = _wrap_email(content)

    return subject, html


# =============================================================================
# Action Start/Deadline Reminder Emails (Frequency-aware)
# =============================================================================


def render_action_start_reminder_email(
    user_id: str,
    action_title: str,
    action_url: str,
    days_overdue: int,
    session_id: str = "",
) -> tuple[str, str]:
    """Render email for an action whose start date has passed.

    Args:
        user_id: User ID for unsubscribe link
        action_title: Title of the action
        action_url: URL to view/edit the action
        days_overdue: Days since the start date passed
        session_id: Source meeting ID

    Returns:
        Tuple of (html_content, plain_text)
    """
    urgency = "overdue" if days_overdue > 3 else "due-soon"
    days_text = (
        "today"
        if days_overdue == 0
        else f"{days_overdue} day{'s' if days_overdue != 1 else ''} ago"
    )

    content = f"""
<h2>Action start date has passed</h2>

<div class="action-item {urgency}">
<p class="action-title">{action_title}</p>
<p class="action-due">Planned start: {days_text}</p>
</div>

<p>This action was scheduled to begin but hasn't been started yet. Would you like to start it now or adjust the timeline?</p>

<p>
<a href="{action_url}" class="button">View Action</a>
</p>

<p style="font-size: 14px; color: #666;">
You can snooze or disable reminders for this action from the action detail page.
</p>
"""

    html = _wrap_email(content, user_id, "reminders")

    plain_text = f"""Action start date has passed

Title: {action_title}
Planned start: {days_text}

This action was scheduled to begin but hasn't been started yet.

View action: {action_url}

---
You can snooze or disable reminders from the action detail page.
"""

    return html, plain_text


def render_action_deadline_reminder_email(
    user_id: str,
    action_title: str,
    action_url: str,
    days_until: int,
    session_id: str = "",
) -> tuple[str, str]:
    """Render email for an action with an approaching deadline.

    Args:
        user_id: User ID for unsubscribe link
        action_title: Title of the action
        action_url: URL to view/edit the action
        days_until: Days until the deadline
        session_id: Source meeting ID

    Returns:
        Tuple of (html_content, plain_text)
    """
    if days_until <= 0:
        urgency = "overdue"
        if days_until == 0:
            days_text = "today"
        else:
            days_text = f"{abs(days_until)} day{'s' if abs(days_until) != 1 else ''} overdue"
    else:
        urgency = "due-soon"
        days_text = f"in {days_until} day{'s' if days_until != 1 else ''}"

    content = f"""
<h2>Action deadline approaching</h2>

<div class="action-item {urgency}">
<p class="action-title">{action_title}</p>
<p class="action-due">Due: {days_text}</p>
</div>

<p>Your deadline is coming up. Make sure to complete or update this action.</p>

<p>
<a href="{action_url}" class="button">View Action</a>
</p>

<p style="font-size: 14px; color: #666;">
You can snooze or disable reminders for this action from the action detail page.
</p>
"""

    html = _wrap_email(content, user_id, "reminders")

    plain_text = f"""Action deadline approaching

Title: {action_title}
Due: {days_text}

Your deadline is coming up. Make sure to complete or update this action.

View action: {action_url}

---
You can snooze or disable reminders from the action detail page.
"""

    return html, plain_text
