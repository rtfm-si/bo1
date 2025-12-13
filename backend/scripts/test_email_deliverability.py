#!/usr/bin/env python3
"""CLI script for testing email deliverability across clients.

Usage:
    python -m backend.scripts.test_email_deliverability --recipient test@gmail.com
    python -m backend.scripts.test_email_deliverability --recipient test@gmail.com --template welcome
    python -m backend.scripts.test_email_deliverability --recipient test@gmail.com --template all

Templates:
    welcome          - Welcome email for new users
    meeting_completed - Meeting completed with summary and actions
    action_reminder  - Action due/overdue reminder
    weekly_digest    - Weekly activity digest
    workspace_invitation - Workspace team invitation
    all              - Send all templates (default)
"""

import argparse
import sys
import uuid
from datetime import date, timedelta

from backend.services.email import EmailError, send_email
from backend.services.email_templates import (
    render_action_reminder_email,
    render_meeting_completed_email,
    render_weekly_digest_email,
    render_welcome_email,
    render_workspace_invitation_email,
)

# =============================================================================
# Test Data Fixtures
# =============================================================================

TEST_USER_ID = "test-user-" + str(uuid.uuid4())[:8]
TEST_USER_NAME = "Test User"


def get_welcome_data() -> dict:
    """Get test data for welcome email."""
    return {
        "user_name": TEST_USER_NAME,
        "user_id": TEST_USER_ID,
    }


def get_meeting_completed_data() -> dict:
    """Get test data for meeting completed email."""
    return {
        "user_id": TEST_USER_ID,
        "problem_statement": "Should we expand into the European market in Q2 2025, "
        "and if so, which countries should we prioritize first?",
        "summary": "After deliberation, the experts recommend prioritizing Germany "
        "and the Netherlands for initial European expansion. Germany offers the "
        "largest market potential with strong e-commerce adoption, while the "
        "Netherlands provides favorable logistics infrastructure and English "
        "proficiency for smoother operations.",
        "recommendations": [
            "Start with Germany as primary market (largest EU economy, high e-commerce adoption)",
            "Use Netherlands as logistics hub and secondary market",
            "Delay UK entry until post-Brexit trade clarity improves",
            "Allocate €150K initial budget with 6-month runway",
            "Partner with local fulfillment provider rather than own warehousing",
        ],
        "actions": [
            {
                "title": "Research German e-commerce regulations",
                "due_date": "2025-01-15",
                "priority": "high",
            },
            {
                "title": "Identify top 3 fulfillment partners in Netherlands",
                "due_date": "2025-01-20",
                "priority": "high",
            },
            {
                "title": "Create market entry financial model",
                "due_date": "2025-01-25",
                "priority": "medium",
            },
            {
                "title": "Schedule calls with German market consultants",
                "due_date": "2025-01-22",
                "priority": "medium",
            },
        ],
        "meeting_url": "https://boardof.one/meeting/test-meeting-123",
    }


def get_action_reminder_data(is_overdue: bool = False) -> dict:
    """Get test data for action reminder email."""
    if is_overdue:
        due_date = date.today() - timedelta(days=3)
    else:
        due_date = date.today() + timedelta(days=1)

    return {
        "user_id": TEST_USER_ID,
        "action_title": "Complete competitor analysis for German market",
        "action_description": "Analyze the top 5 competitors in the German market segment. "
        "Focus on pricing strategy, product range, delivery options, and customer service. "
        "Document findings in the shared spreadsheet and prepare a 1-page summary for the "
        "strategy meeting next week.",
        "due_date": due_date,
        "action_url": "https://boardof.one/actions/test-action-456",
        "is_overdue": is_overdue,
    }


def get_weekly_digest_data() -> dict:
    """Get test data for weekly digest email."""
    return {
        "user_id": TEST_USER_ID,
        "overdue_actions": [
            {"title": "Submit quarterly report", "due_date": "2025-01-08"},
            {"title": "Review budget proposal", "due_date": "2025-01-10"},
        ],
        "upcoming_actions": [
            {"title": "Team standup presentation", "due_date": "2025-01-16"},
            {"title": "Client demo preparation", "due_date": "2025-01-17"},
            {"title": "Update product roadmap", "due_date": "2025-01-18"},
        ],
        "completed_count": 7,
        "meetings_count": 3,
    }


def get_workspace_invitation_data() -> dict:
    """Get test data for workspace invitation email."""
    return {
        "workspace_name": "Acme Corp Strategy Team",
        "inviter_name": "Sarah Johnson",
        "role": "member",
        "accept_url": "https://boardof.one/invite/test-token-789",
        "expires_at": date.today() + timedelta(days=7),
    }


# =============================================================================
# Email Sending Functions
# =============================================================================

TEMPLATES = {
    "welcome": ("Welcome Email", render_welcome_email, get_welcome_data),
    "meeting_completed": (
        "Meeting Completed Email",
        render_meeting_completed_email,
        get_meeting_completed_data,
    ),
    "action_reminder": (
        "Action Reminder (Due Tomorrow)",
        render_action_reminder_email,
        lambda: get_action_reminder_data(is_overdue=False),
    ),
    "action_reminder_overdue": (
        "Action Reminder (Overdue)",
        render_action_reminder_email,
        lambda: get_action_reminder_data(is_overdue=True),
    ),
    "weekly_digest": ("Weekly Digest Email", render_weekly_digest_email, get_weekly_digest_data),
    "workspace_invitation": (
        "Workspace Invitation Email",
        render_workspace_invitation_email,
        get_workspace_invitation_data,
    ),
}


def send_test_email(recipient: str, template_name: str) -> bool:
    """Send a single test email.

    Args:
        recipient: Email address to send to
        template_name: Template key from TEMPLATES

    Returns:
        True if sent successfully, False otherwise
    """
    if template_name not in TEMPLATES:
        print(f"❌ Unknown template: {template_name}")
        return False

    display_name, render_fn, data_fn = TEMPLATES[template_name]
    data = data_fn()

    print(f"📧 Sending: {display_name}")
    print(f"   To: {recipient}")

    try:
        html, text = render_fn(**data)

        # Determine subject based on template
        subject_map = {
            "welcome": "Welcome to Board of One!",
            "meeting_completed": "Your Meeting is Complete - Board of One",
            "action_reminder": "[Reminder] Action due tomorrow",
            "action_reminder_overdue": "[Overdue] Action requires attention",
            "weekly_digest": "Your Weekly Summary - Board of One",
            "workspace_invitation": f"You've been invited to join {data.get('workspace_name', 'a workspace')}",
        }
        subject = f"[TEST] {subject_map.get(template_name, 'Test Email')}"

        result = send_email(
            to=recipient,
            subject=subject,
            html=html,
            text=text,
            tags=[{"name": "type", "value": "deliverability_test"}],
        )

        if result:
            print(f"   ✅ Sent! ID: {result.get('id', 'unknown')}")
            return True
        else:
            print("   ⚠️  Email not sent (no API key configured)")
            return False

    except EmailError as e:
        print(f"   ❌ Failed: {e}")
        return False


def send_all_test_emails(recipient: str) -> dict:
    """Send all test email templates.

    Args:
        recipient: Email address to send to

    Returns:
        Dict with success/failure counts
    """
    results = {"sent": 0, "failed": 0, "templates": []}

    for template_name in TEMPLATES:
        success = send_test_email(recipient, template_name)
        if success:
            results["sent"] += 1
        else:
            results["failed"] += 1
        results["templates"].append({"name": template_name, "success": success})
        print()  # Blank line between emails

    return results


# =============================================================================
# CLI Entry Point
# =============================================================================


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test email deliverability across clients",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--recipient",
        "-r",
        required=True,
        help="Email address to send test emails to",
    )

    parser.add_argument(
        "--template",
        "-t",
        choices=list(TEMPLATES.keys()) + ["all"],
        default="all",
        help="Template to send (default: all)",
    )

    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List available templates and exit",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        args: Command line arguments (for testing)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parsed = parse_args(args)

    if parsed.list_templates:
        print("Available templates:")
        for key, (name, _, _) in TEMPLATES.items():
            print(f"  {key:25} - {name}")
        return 0

    print("=" * 60)
    print("EMAIL DELIVERABILITY TEST")
    print("=" * 60)
    print()

    if parsed.template == "all":
        results = send_all_test_emails(parsed.recipient)

        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Sent:   {results['sent']}")
        print(f"Failed: {results['failed']}")

        return 0 if results["failed"] == 0 else 1
    else:
        success = send_test_email(parsed.recipient, parsed.template)
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
