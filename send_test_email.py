#!/usr/bin/env python3
"""
send_test_email.py - Send test emails via the Brevo (formerly Sendinblue) transactional email API.

Reads HTML email templates from disk and sends them through Brevo's SMTP API.
The API key is read from the BREVO_API_KEY environment variable.

Usage examples:
    python send_test_email.py --to test@email.com --template 1
    python send_test_email.py --to test@email.com --template 2 --dry-run
    python send_test_email.py --to test@email.com --template 3 --from sender@example.com
    python send_test_email.py --template 1 --preview
"""

import argparse
import os
import sys
import tempfile
import webbrowser

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

TEMPLATES = {
    1: {
        "file": os.path.join(os.path.dirname(os.path.abspath(__file__)), "emails", "email-1-announcement.html"),
        "subject": "15 Research Frontiers in 5D Parallelism \u2014 Your Path to NeurIPS",
    },
    2: {
        "file": os.path.join(os.path.dirname(os.path.abspath(__file__)), "emails", "email-2-deepdive.html"),
        "subject": "From Diffusion LLMs to MoE: GPU Research That Gets Published",
    },
    3: {
        "file": os.path.join(os.path.dirname(os.path.abspath(__file__)), "emails", "email-3-lastcall.html"),
        "subject": "NeurIPS 2026 Deadline Approaching \u2014 Start Your Research Today",
    },
}

DEFAULT_SENDER_EMAIL = "hello@vizuara.ai"
SENDER_NAME = "Vizuara AI Labs"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_template(template_id: int) -> str:
    """Read the HTML template file from disk and return its contents."""
    info = TEMPLATES[template_id]
    path = info["file"]

    if not os.path.isfile(path):
        print(f"Error: Template file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def build_payload(
    sender_email: str,
    recipient_email: str,
    subject: str,
    html_content: str,
) -> dict:
    """Build the JSON payload expected by the Brevo transactional email API."""
    return {
        "sender": {
            "name": SENDER_NAME,
            "email": sender_email,
        },
        "to": [
            {"email": recipient_email},
        ],
        "subject": subject,
        "htmlContent": html_content,
    }


def send_email(api_key: str, payload: dict) -> None:
    """POST the payload to Brevo and print the result."""
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }

    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=30)
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Brevo API. Check your network connection.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: Request to Brevo API timed out.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        print(f"Error: Request failed -- {exc}", file=sys.stderr)
        sys.exit(1)

    if response.status_code in (200, 201):
        print(f"Success! Email sent. (HTTP {response.status_code})")
        print(f"Response: {response.json()}")
    else:
        print(f"Failed to send email. (HTTP {response.status_code})", file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
        sys.exit(1)


def preview_in_browser(html_content: str) -> None:
    """Write the HTML to a temporary file and open it in the default browser."""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(html_content)
        tmp_path = tmp.name

    print(f"Opening preview in browser: {tmp_path}")
    webbrowser.open(f"file://{tmp_path}")


def print_dry_run(sender_email: str, recipient_email: str, subject: str, template_id: int) -> None:
    """Print what would be sent without actually sending."""
    info = TEMPLATES[template_id]
    print("=" * 60)
    print("DRY RUN -- no email will be sent")
    print("=" * 60)
    print(f"  From:     {SENDER_NAME} <{sender_email}>")
    print(f"  To:       {recipient_email}")
    print(f"  Subject:  {subject}")
    print(f"  Template: {template_id} ({os.path.basename(info['file'])})")
    print(f"  File:     {info['file']}")
    print(f"  API URL:  {BREVO_API_URL}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send test emails via the Brevo transactional email API.",
        epilog=(
            "Examples:\n"
            "  python send_test_email.py --to test@email.com --template 1\n"
            "  python send_test_email.py --to test@email.com --template 2 --dry-run\n"
            "  python send_test_email.py --template 1 --preview\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--to",
        metavar="EMAIL",
        help="Recipient email address (required unless --preview is used).",
    )
    parser.add_argument(
        "--template",
        type=int,
        choices=[1, 2, 3],
        required=True,
        help="Email template to send (1=announcement, 2=deepdive, 3=lastcall).",
    )
    parser.add_argument(
        "--from",
        dest="sender",
        metavar="EMAIL",
        default=DEFAULT_SENDER_EMAIL,
        help=f"Sender email address (default: {DEFAULT_SENDER_EMAIL}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print email details without sending.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Open the HTML template in the default web browser.",
    )

    args = parser.parse_args(argv)

    # Validate: --to is required unless we are only previewing
    if not args.preview and not args.to:
        parser.error("--to is required when not using --preview")

    return args


def main(argv=None) -> None:
    args = parse_args(argv)

    template_id = args.template
    subject = TEMPLATES[template_id]["subject"]

    # ---- Preview mode ----
    if args.preview:
        html_content = load_template(template_id)
        preview_in_browser(html_content)
        # If only previewing (no --to), exit here
        if not args.to:
            return

    # ---- Dry-run mode ----
    if args.dry_run:
        # Verify the template file exists even in dry-run so we catch errors early
        if not os.path.isfile(TEMPLATES[template_id]["file"]):
            print(f"Warning: Template file not found: {TEMPLATES[template_id]['file']}", file=sys.stderr)
        print_dry_run(args.sender, args.to, subject, template_id)
        return

    # ---- Send mode ----
    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        print(
            "Error: BREVO_API_KEY environment variable is not set.\n"
            "       Export it before running this script:\n"
            "         export BREVO_API_KEY='your-api-key-here'",
            file=sys.stderr,
        )
        sys.exit(1)

    html_content = load_template(template_id)
    payload = build_payload(args.sender, args.to, subject, html_content)

    print(f"Sending template {template_id} to {args.to} ...")
    send_email(api_key, payload)


if __name__ == "__main__":
    main()
