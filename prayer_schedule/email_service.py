"""Email composition and delivery via Gmail SMTP.

Every day the CLI sends exactly one "combined" email per recipient that
contains:

* today's prayer assignment and family list,
* the week-at-a-glance table,
* (on Mondays only) the full prayer lists for every elder that week.
"""

from __future__ import annotations

import smtplib
import time
import traceback
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from . import config
from .elders import get_week_schedule
from .file_io import log_activity
from .validation import verify_email_date


def _email_styles() -> dict[str, str]:
    """Return inline CSS snippets used by the email HTML builder.

    Visual design mirrors the website (GitHub Pages) layout:
      - Header: #2c3e50 (dark navy) with church name, schedule title, date range
      - Day nav bar: #1a252f (darker navy) with day pill buttons
      - Today accent: #e67e22 (warm orange) for today's banner and highlights
      - Table headers: #3498db (blue) matching website schedule table
      - Text: #333333 (near-black) on white/#f8f9fa backgrounds

    Email compatibility notes:
      - All styles are inline (no <style> block) for Gmail/Outlook/Apple Mail
      - No CSS opacity (Outlook ignores it) - uses explicit color values instead
      - No box-shadow (Outlook ignores it) - uses borders for depth
      - Day pills use inline-block (widely supported) with table fallback structure
      - border-radius degrades gracefully to square corners in older Outlook
    """
    return {
        'body': 'margin:0;padding:0;background-color:#f5f5f5;font-family:Segoe UI,Arial,Helvetica,sans-serif;',
        'wrapper': 'width:100%;background-color:#f5f5f5;padding:30px 0;',
        'container': 'max-width:620px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;border:1px solid #d0d4d9;',
        'header': 'background:#2c3e50;color:#ffffff;padding:28px 30px 22px 30px;text-align:center;',
        'header_h1': 'margin:0 0 8px 0;font-size:26px;font-weight:700;color:#ffffff;',
        'header_h2': 'margin:0 0 6px 0;font-size:19px;font-weight:600;color:#ffffff;',
        'header_sub': 'margin:0;font-size:14px;font-weight:700;color:#b0bec5;',
        'day_nav': 'background:#1a252f;padding:14px 8px;text-align:center;font-size:0;',
        'day_pill': 'display:inline-block;padding:8px 6px;border-radius:20px;font-size:12px;font-weight:600;color:#8899a6;border:2px solid #2c3e50;text-align:center;width:60px;margin:2px;',
        'day_pill_today': 'display:inline-block;padding:8px 6px;border-radius:20px;font-size:12px;font-weight:700;color:#ffffff;background-color:#e67e22;border:2px solid #e67e22;text-align:center;width:60px;margin:2px;',
        'day_pill_past': 'display:inline-block;padding:8px 6px;border-radius:20px;font-size:12px;font-weight:600;color:#c5d0db;border:2px solid #2c3e50;text-align:center;width:60px;margin:2px;',
        'day_pill_label': 'display:block;font-size:10px;color:#d0d9e2;margin-top:2px;',
        'day_pill_label_today': 'display:block;font-size:10px;color:#ffffff;margin-top:2px;',
        'day_pill_label_past': 'display:block;font-size:10px;color:#b8c4d1;margin-top:2px;',
        'today_banner': 'background-color:#b75e10;padding:22px 30px;text-align:center;',
        'today_banner_h2': 'margin:0 0 6px 0;font-size:18px;font-weight:700;color:#ffffff;',
        'today_elder': 'margin:4px 0;font-size:20px;font-weight:700;color:#ffffff;',
        'today_count': 'margin:4px 0 0 0;font-size:13px;color:#ffffff;',
        'content': 'padding:24px 30px;color:#333333;font-size:15px;line-height:1.7;',
        'section_label': 'font-size:12px;font-weight:700;color:#555555;margin:20px 0 10px 0;',
        'table': 'width:100%;border-collapse:collapse;margin:10px 0;border:1px solid #ddd;',
        'th': 'background:#3498db;color:#ffffff;padding:10px 12px;text-align:left;font-size:12px;font-weight:600;',
        'td': 'padding:10px 12px;border-bottom:1px solid #e8eaed;font-size:14px;color:#333333;',
        'td_alt': 'padding:10px 12px;border-bottom:1px solid #e8eaed;font-size:14px;color:#333333;background:#f8f9fa;',
        'td_today': 'padding:10px 12px;border-bottom:1px solid #e8eaed;font-size:14px;color:#d35400;font-weight:700;background:#fef3e2;border-left:4px solid #e67e22;',
        'td_today_inner': 'padding:10px 12px;border-bottom:1px solid #e8eaed;font-size:14px;color:#d35400;font-weight:700;background:#fef3e2;',
        'elder_block': 'margin:12px 0;border-left:4px solid #3498db;padding:12px 16px;background:#f8f9fa;',
        'elder_block_today': 'margin:12px 0;border-left:4px solid #e67e22;padding:14px 18px;background:#fef9f3;',
        'elder_name': 'font-size:15px;font-weight:700;color:#2c3e50;margin:0 0 2px 0;',
        'elder_count': 'font-size:13px;color:#777777;margin:0 0 8px 0;font-style:italic;',
        'family_item': 'padding:3px 0;font-size:14px;color:#444444;',
        'divider': 'height:1px;background:#e0e3e7;margin:20px 0;',
        'footer': 'padding:18px 30px;text-align:center;background:#f7f8f9;border-top:1px solid #e0e3e7;',
        'footer_link': 'display:inline-block;background:#2c3e50;color:#ffffff;text-decoration:none;padding:10px 24px;border-radius:4px;font-size:13px;font-weight:600;',
        'footer_text': 'margin:10px 0 0 0;font-size:12px;color:#999999;',
    }


def _build_combined_email_html(
    today: datetime,
    today_name: str,
    week_num: int,
    monday: datetime,
    schedule: dict[str, list[str]],
    elder_assignments: dict[str, list[str]],
) -> str:
    """Return the full combined daily email as an HTML string.

    Layout mirrors the website (GitHub Pages) design:

      1. Header: Church name (large), "Elder Prayer Schedule - Week X", date range
      2. Day navigation bar: Pill buttons for each day, today highlighted orange
      3. Today's Prayer List banner: Orange bar with elder name and family count
      4. Today's families: Elder block(s) with numbered family lists
      5. Week schedule table: All 7 days, today's row highlighted with orange accent
      6. On Mondays only: Full prayer lists for every elder that week
      7. Footer: Link to view full schedule online
    """
    s = _email_styles()
    is_monday = today.weekday() == 0

    todays_elders = schedule.get(today_name, [])
    elder_names_display = " &amp; ".join(todays_elders)

    end_date = monday + timedelta(days=6)
    date_range = f"{monday.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

    # --- Calculate total families being prayed for today ---
    today_family_count = 0
    for elder in todays_elders:
        today_family_count += len(elder_assignments.get(elder, []))

    # --- Day navigation pills (matches website day-nav bar) ---
    day_pills = ""
    current_date = monday
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        is_today_pill = (day == today_name)
        is_past = (current_date < today and not is_today_pill)

        if is_today_pill:
            pill_style = s['day_pill_today']
            label_style = s['day_pill_label_today']
        elif is_past:
            pill_style = s['day_pill_past']
            label_style = s['day_pill_label_past']
        else:
            pill_style = s['day_pill']
            label_style = s['day_pill_label']

        day_pills += f'<div style="{pill_style}">{day[:3]}<span style="{label_style}">{current_date.strftime("%b %d")}</span></div>\n'
        current_date += timedelta(days=1)

    # --- Today's prayer list sections ---
    today_prayer_sections = ""
    for elder in todays_elders:
        families = elder_assignments.get(elder, [])
        family_list = ""
        for j, family in enumerate(families, 1):
            family_escaped = family.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            family_list += f'<div style="{s["family_item"]}">{j}. {family_escaped}</div>\n'

        today_prayer_sections += f"""
        <div style="{s['elder_block_today']}">
            <p style="{s['elder_name']}">{elder}</p>
            <p style="{s['elder_count']}">{len(families)} families</p>
            {family_list}
        </div>"""

    # --- Week schedule table ---
    table_rows = ""
    current_date = monday
    for i, day in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
        elders = schedule[day]
        elder_names_row = " &amp; ".join(elders)
        date_str = current_date.strftime('%b %d')

        is_today = (day == today_name)
        if is_today:
            # First cell gets left border accent; inner cells get same style without border.
            td_first = s['td_today']
            td_rest = s['td_today_inner']
        elif i % 2 == 1:
            td_first = s['td_alt']
            td_rest = s['td_alt']
        else:
            td_first = s['td']
            td_rest = s['td']

        arrow = "&#9654; " if is_today else ""
        table_rows += f"""<tr>
            <td style="{td_first}">{arrow}<strong>{day}</strong></td>
            <td style="{td_rest}">{date_str}</td>
            <td style="{td_rest}">{elder_names_row}</td>
        </tr>"""
        current_date += timedelta(days=1)

    # --- Monday-only: full prayer lists for all elders ---
    full_prayer_lists = ""
    if is_monday:
        full_prayer_lists += f'<p style="{s["section_label"]}">ALL PRAYER LISTS THIS WEEK</p>'
        current_date = monday
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            elders = schedule[day]
            for elder in elders:
                families = elder_assignments.get(elder, [])
                date_str = current_date.strftime('%b %d')
                family_list = ""
                for j, family in enumerate(families, 1):
                    family_escaped = family.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    family_list += f'<div style="{s["family_item"]}">{j}. {family_escaped}</div>\n'

                full_prayer_lists += f"""
                <div style="{s['elder_block']}">
                    <p style="{s['elder_name']}">{elder} &mdash; {day}, {date_str}</p>
                    <p style="{s['elder_count']}">{len(families)} families</p>
                    {family_list}
                </div>"""
            current_date += timedelta(days=1)
        full_prayer_lists += f'<div style="{s["divider"]}"></div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="{s['body']}">
<div style="{s['wrapper']}">
<div style="{s['container']}">

    <!-- Header -->
    <div style="{s['header']}">
        <h1 style="{s['header_h1']}">Crossville Church of Christ</h1>
        <h2 style="{s['header_h2']}">Daily Prayer Reminder</h2>
        <p style="{s['header_sub']}">{today.strftime('%A, %B %d, %Y')}: {elder_names_display} &mdash; Week {week_num}</p>
    </div>

    <!-- Day Navigation Bar -->
    <div style="{s['day_nav']}">
        {day_pills}
    </div>

    <!-- Today's Prayer List Banner -->
    <div style="{s['today_banner']}">
        <h2 style="{s['today_banner_h2']}">Today's Prayer List</h2>
        <p style="{s['today_elder']}">{elder_names_display}</p>
        <p style="{s['today_count']}">{today_family_count} families being prayed for today</p>
    </div>

    <!-- Today's Families -->
    <div style="{s['content']}">
        <p style="{s['section_label']}">TODAY'S FAMILIES</p>
        {today_prayer_sections}

        <div style="{s['divider']}"></div>

        <!-- Week Schedule Table -->
        <p style="{s['section_label']}">THIS WEEK AT A GLANCE</p>
        <table style="{s['table']}">
            <tr>
                <th style="{s['th']}">DAY</th>
                <th style="{s['th']}">DATE</th>
                <th style="{s['th']}">ELDER(S)</th>
            </tr>
            {table_rows}
        </table>

        {full_prayer_lists}

        <p style="text-align:center;color:#999999;font-size:13px;margin:16px 0 0 0;">
            Thank you for faithfully praying for our church family.
        </p>
    </div>

    <!-- Footer -->
    <div style="{s['footer']}">
        <a href="https://vlcosent.github.io/prayer-schedule-automation/" style="{s['footer_link']}">View Full Schedule Online</a>
        <p style="{s['footer_text']}">Crossville Church of Christ &bull; Elder Prayer List</p>
    </div>

</div>
</div>
</body>
</html>"""
    return html


def send_daily_combined_email(
    today: datetime,
    week_num: int,
    monday: datetime,
    elder_assignments: dict[str, list[str]],
) -> bool:
    """Send ONE combined daily email with today's prayer assignment + week overview.

    Every day (Mon-Sun) this sends a single email containing:

    * Today's day/date and assigned elder(s) prominently at top
    * Today's family prayer list
    * Week-at-a-glance schedule table (today's row highlighted)
    * On Mondays only: full prayer lists for all elders that week

    Returns ``True`` when at least one recipient received the email.
    """
    if not config.EMAIL_ENABLED:
        print("   [INFO] Email is disabled (EMAIL_ENABLED not set to 'true')")
        return False

    if not config.SENDER_PASSWORD:
        print("   [WARNING] Email password not configured (SENDER_PASSWORD not set)")
        print("   [INFO] Skipping email delivery")
        return False

    try:
        # Parse recipient emails.
        recipients = [
            email.strip() for email in config.RECIPIENT_EMAILS.split(',') if email.strip()
        ]

        if not recipients:
            print("   [WARNING] No recipient emails configured")
            return False

        # Verify the date is correct before composing the email.
        date_valid, date_msg = verify_email_date(today, monday)
        print(f"   [DATE CHECK] {date_msg}")
        if not date_valid:
            print("   [X] DATE VERIFICATION FAILED - not sending email")
            return False

        # Determine today's day name.
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        today_name = day_names[today.weekday()]
        today_formatted = today.strftime('%A, %B %d, %Y')

        # Get today's schedule.
        schedule = get_week_schedule(week_num)
        todays_elders = schedule.get(today_name, [])

        if not todays_elders:
            print(f"   [INFO] No elders assigned for {today_name} - skipping email")
            return False

        elder_names = " & ".join(todays_elders)

        # Build plain text version.
        end_date = monday + timedelta(days=6)
        date_range = f"{monday.strftime('%b %d')}-{end_date.strftime('%d, %Y')}"

        # Today's elder details (plain text).
        elder_details = ""
        for elder in todays_elders:
            families = elder_assignments.get(elder, [])
            elder_details += f"\n{elder} - {len(families)} families:\n"
            elder_details += "-" * 50 + "\n"
            for i, family in enumerate(families, 1):
                elder_details += f"  {i:3}. {family}\n"
            elder_details += "\n"

        # Week overview (plain text).
        week_overview = "\nThis Week's Schedule:\n"
        week_overview += f"{'Day':<12} {'Date':<10} {'Elder(s)'}\n"
        week_overview += "-" * 50 + "\n"
        current_date = monday
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            elders = schedule[day]
            marker = ">>>" if day == today_name else "   "
            week_overview += f"{marker} {day:<9} {current_date.strftime('%b %d'):<10} {' & '.join(elders)}\n"
            current_date += timedelta(days=1)

        # Build email content once (reused for each recipient).
        subject = f"Daily Prayer Reminder - {today_formatted}: {elder_names}"
        plain_body = f"""Crossville Church of Christ
Daily Prayer Reminder - {today_formatted}: {elder_names}
Week {week_num} ({date_range})

Today's Elder: {elder_names}
{elder_details}
{week_overview}
Please keep these families in your prayers.

View the full schedule online: https://vlcosent.github.io/prayer-schedule-automation/
"""
        html_body = _build_combined_email_html(
            today, today_name, week_num, monday, schedule, elder_assignments
        )

        # Connect to Gmail SMTP server with retry for transient failures.
        max_retries = config.EMAIL_RETRY_MAX
        last_error: Exception | None = None
        server: smtplib.SMTP | None = None
        for attempt in range(1, max_retries + 1):
            try:
                print(f"   [EMAIL] Connecting to {config.SMTP_SERVER}:{config.SMTP_PORT} (attempt {attempt}/{max_retries})...")
                print(f"   [EMAIL] Email date: {today_formatted}")
                server = smtplib.SMTP(
                    config.SMTP_SERVER,
                    config.SMTP_PORT,
                    timeout=config.EMAIL_CONNECT_TIMEOUT,
                )
                server.starttls()
                print(f"   [EMAIL] Logging in as {config.SENDER_EMAIL}...")
                server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
                break  # Connected successfully.

            except smtplib.SMTPAuthenticationError as exc:
                print(f"   [ERROR] Email authentication failed: {exc}")
                print("   [INFO] Please verify SENDER_PASSWORD is a valid Gmail App Password")
                log_activity(f"Email FAILED (auth error): {exc}")
                return False
            except (smtplib.SMTPException, OSError) as exc:
                last_error = exc
                print(f"   [WARNING] Connection attempt {attempt} failed: {exc}")
                if attempt < max_retries:
                    wait = 2 ** attempt  # 2s, 4s.
                    print(f"   [INFO] Retrying in {wait}s...")
                    time.sleep(wait)
        else:
            # All connection retries exhausted.
            print(f"   [ERROR] SMTP connection failed after {max_retries} attempts: {last_error}")
            log_activity(f"Email FAILED (connection) after {max_retries} attempts: {last_error}")
            return False

        # Send individually to each recipient for better deliverability.
        succeeded: list[str] = []
        failed: list[str] = []
        try:
            for recipient in recipients:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['From'] = config.SENDER_EMAIL
                    msg['To'] = recipient
                    msg['Subject'] = subject
                    msg['Date'] = formatdate(localtime=True)
                    msg['Message-ID'] = make_msgid(domain='gmail.com')
                    msg['Reply-To'] = config.SENDER_EMAIL
                    # Gmail & RFC 8058 best practice: machine-readable unsubscribe
                    # endpoint. "mailto:" form works everywhere; the sender then
                    # removes the address from RECIPIENT_EMAILS manually. Keeps us
                    # out of spam folders and satisfies Gmail's 2024 bulk-sender
                    # requirements.
                    msg['List-Unsubscribe'] = f'<mailto:{config.SENDER_EMAIL}?subject=Unsubscribe>'
                    msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
                    msg['X-Mailer'] = 'Crossville-CoC-Prayer-Schedule/1.0'

                    msg.attach(MIMEText(plain_body, 'plain'))
                    msg.attach(MIMEText(html_body, 'html'))

                    assert server is not None  # narrows type for mypy
                    server.send_message(msg)
                    succeeded.append(recipient)
                    print(f"   [OK] Sent to {recipient}")
                except (smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError) as exc:
                    failed.append(recipient)
                    print(f"   [WARNING] Failed to send to {recipient}: {exc}")
        finally:
            if server is not None:
                server.quit()

        # Report results.
        if failed:
            print(f"   [WARNING] Failed recipients ({len(failed)}): {', '.join(failed)}")
            log_activity(
                f"Email partially sent for {today_name}, {today.strftime('%B %d, %Y')}: "
                f"{len(succeeded)} succeeded, {len(failed)} failed ({', '.join(failed)})"
            )
        if succeeded:
            print(
                f"   [OK] Daily email sent for {today_name}, {today.strftime('%B %d, %Y')} "
                f"to {len(succeeded)} of {len(recipients)} recipient(s)"
            )
            if not failed:
                log_activity(
                    f"Email sent for {today_name}, {today.strftime('%B %d, %Y')} "
                    f"to {len(succeeded)} recipient(s)"
                )
            return True
        else:
            print(f"   [ERROR] Email delivery failed for all {len(recipients)} recipients")
            log_activity(f"Email FAILED for all recipients on {today_name}, {today.strftime('%B %d, %Y')}")
            return False

    except Exception as exc:
        print(f"   [ERROR] Failed to send email: {exc}")
        traceback.print_exc()
        log_activity(f"Email FAILED (unexpected error): {exc}")
        return False
