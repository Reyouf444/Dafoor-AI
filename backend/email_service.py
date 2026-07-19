"""
Email service for Dafoor AI — password reset emails.

Uses Gmail SMTP with an App Password for sending.  This is the simplest
approach for a small app and avoids third-party dependencies.

To set up a Gmail App Password:
  1. Go to https://myaccount.google.com/security
  2. Enable 2-Step Verification (required)
  3. Go to App passwords → Generate a new one for "Mail"
  4. Use that 16-character password as SMTP_PASSWORD

Environment variables:
    SMTP_HOST     — SMTP server  (default: smtp.gmail.com)
    SMTP_PORT     — SMTP port    (default: 587)
    SMTP_USER     — sender email (e.g. your-app@gmail.com)
    SMTP_PASSWORD — Gmail App Password (NOT your Gmail password)
    APP_BASE_URL  — base URL of the app (e.g. https://dafoor-ai-xxx.run.app)
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
APP_BASE_URL  = os.getenv("APP_BASE_URL", "http://localhost:8000")


# ── Public API ────────────────────────────────────────────────────────────────

def send_password_reset_email(to_email: str, reset_token: str, username: str) -> bool:
    """Send a password reset email with a link containing the reset token.

    Returns True if the email was sent successfully, False otherwise.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error(
            "SMTP credentials not configured (SMTP_USER / SMTP_PASSWORD). "
            "Cannot send password reset email."
        )
        return False

    reset_link = f"{APP_BASE_URL}/#reset-password?token={reset_token}"

    subject = "Dafoor AI — Password Reset Request"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                background-color: #0B0F19;
                color: #f3f4f6;
                font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 520px;
                margin: 40px auto;
                background: rgba(17, 24, 39, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 40px;
            }}
            .logo {{
                text-align: center;
                font-size: 24px;
                font-weight: 700;
                background: linear-gradient(135deg, #10b981, #059669);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 24px;
            }}
            h2 {{
                color: #ffffff;
                font-size: 22px;
                margin-bottom: 16px;
            }}
            p {{
                color: #9ca3af;
                line-height: 1.7;
                font-size: 15px;
            }}
            .reset-btn {{
                display: inline-block;
                background: linear-gradient(135deg, #10b981, #059669);
                color: #ffffff !important;
                text-decoration: none;
                padding: 14px 32px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 16px;
                margin: 24px 0;
            }}
            .footer {{
                margin-top: 32px;
                padding-top: 20px;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                font-size: 13px;
                color: #6b7280;
                text-align: center;
            }}
            .token-fallback {{
                background: rgba(255, 255, 255, 0.05);
                padding: 10px 16px;
                border-radius: 6px;
                font-family: monospace;
                font-size: 13px;
                color: #d1d5db;
                word-break: break-all;
                margin-top: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">Dafoor AI</div>
            <h2>Password Reset Request</h2>
            <p>Hi <strong style="color:#ffffff;">{username}</strong>,</p>
            <p>
                We received a request to reset your password. Click the button below
                to choose a new password. This link expires in <strong style="color:#ffffff;">1 hour</strong>.
            </p>
            <div style="text-align: center;">
                <a href="{reset_link}" class="reset-btn">Reset My Password</a>
            </div>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <div class="token-fallback">{reset_link}</div>
            <p>If you didn't request a password reset, you can safely ignore this email.</p>
            <div class="footer">
                <p>Dafoor AI — Elevate Your Learning</p>
                <p>Created by Reyouf Alfawzan</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Dafoor AI — Password Reset

    Hi {username},

    We received a request to reset your password.
    Click this link to set a new password (expires in 1 hour):

    {reset_link}

    If you didn't request this, ignore this email.
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"Dafoor AI <{SMTP_USER}>"
        msg["To"]      = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info("Password reset email sent to %s", to_email)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD. "
            "For Gmail, use an App Password (not your regular password)."
        )
        return False
    except Exception as exc:
        logger.error("Failed to send password reset email to %s: %s", to_email, exc)
        return False
