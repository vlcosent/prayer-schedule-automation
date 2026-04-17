"""Generate the HTML and plain-text schedule files for the current week.

The public orchestrator :func:`generate_schedule_content` returns the
``(html, text)`` tuple that ``cli.main`` writes to disk. The two content
formats are produced by :func:`generate_html_schedule` and
:func:`generate_text_schedule` respectively. Both must remain **byte-identical**
to the original single-file implementation, so the f-string literals below
preserve every space, newline, and indentation character from that version.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .elders import get_week_schedule


def _escape_html(family: str) -> str:
    """Escape the minimal HTML-unsafe characters (matches the original)."""
    return family.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_html_schedule(
    week_number: int,
    start_date: datetime,
    elder_assignments: dict[str, list[str]],
) -> str:
    """Build the HTML version of the weekly schedule as a single string.

    The output intentionally preserves the exact formatting of the previous
    single-file implementation (including indentation, embedded CSS, inline
    JavaScript, and the "Last updated" timestamp line).
    """
    schedule = get_week_schedule(week_number)
    end_date = start_date + timedelta(days=6)
    date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

    # HTML version for desktop - Professional style with FIXED ENCODING
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Prayer Schedule - Week {week_number}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="3600">
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: #2c3e50;
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 2.5em; }}
        .header h2 {{ margin: 0 0 10px 0; font-size: 1.8em; }}
        .header h3 {{ margin: 0; font-size: 1.2em; opacity: 0.9; }}
        .content {{ padding: 30px; }}
        /* Day-of-week navigation bar */
        .day-nav {{
            display: flex;
            justify-content: center;
            gap: 4px;
            padding: 15px 20px;
            background: #1a252f;
            flex-wrap: wrap;
        }}
        .day-nav .day-pill {{
            padding: 10px 18px;
            border-radius: 25px;
            font-size: 0.95em;
            font-weight: 600;
            color: #8899a6;
            background: transparent;
            border: 2px solid transparent;
            transition: all 0.3s ease;
            cursor: default;
            text-align: center;
            min-width: 80px;
        }}
        .day-nav .day-pill.today {{
            background: #e67e22;
            color: white;
            border-color: #e67e22;
            box-shadow: 0 2px 12px rgba(230, 126, 34, 0.4);
            transform: scale(1.08);
        }}
        .day-nav .day-pill.past {{
            color: #5a6a7a;
            border-color: #2c3e50;
        }}
        .day-nav .day-pill.future {{
            color: #8899a6;
            border-color: #2c3e50;
        }}
        .day-nav .day-pill .day-label {{
            display: block;
            font-size: 0.85em;
            opacity: 0.7;
        }}
        .day-nav .day-pill.today .day-label {{
            opacity: 1;
        }}
        /* Today's prayer focus banner */
        .today-banner {{
            background: linear-gradient(135deg, #e67e22, #d35400);
            color: white;
            padding: 25px 30px;
            text-align: center;
            display: none;
        }}
        .today-banner h2 {{
            margin: 0 0 8px 0;
            font-size: 1.5em;
        }}
        .today-banner .today-elder {{
            font-size: 1.3em;
            font-weight: bold;
            margin: 5px 0;
        }}
        .today-banner .today-count {{
            font-size: 0.95em;
            opacity: 0.9;
        }}
        .schedule-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .schedule-table th, .schedule-table td {{
            border: 1px solid #ddd;
            padding: 15px;
            text-align: left;
        }}
        .schedule-table th {{
            background: #3498db;
            color: white;
            font-size: 1.1em;
        }}
        .schedule-table tr:nth-child(even) {{ background-color: #f8f9fa; }}
        .schedule-table tr:hover {{ background-color: #e8f4f8; }}
        .schedule-table tr.today-row {{
            background-color: #fef3e2 !important;
            border-left: 4px solid #e67e22;
        }}
        .schedule-table tr.today-row td {{
            font-weight: bold;
            color: #d35400;
        }}
        .highlight {{ background-color: #fff3cd !important; font-weight: bold; }}
        .prayer-list {{
            margin: 40px 0;
            page-break-inside: avoid;
            border-left: 4px solid #3498db;
            padding-left: 20px;
        }}
        .prayer-list.today-prayer-list {{
            border-left-color: #e67e22;
            background: #fef9f3;
            padding: 20px;
            border-radius: 0 8px 8px 0;
        }}
        .prayer-list h3 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            font-size: 1.3em;
        }}
        .prayer-list.today-prayer-list h3 {{
            color: #d35400;
            border-bottom-color: #e67e22;
        }}
        .family-list {{
            columns: 2;
            column-gap: 40px;
            list-style-type: none;
            padding: 0;
        }}
        .family-list li {{
            margin: 8px 0;
            padding: 5px;
            border-radius: 5px;
            transition: background-color 0.3s;
        }}
        .family-list li:hover {{
            background-color: #e8f4f8;
        }}
        .family-list li:before {{
            content: "\\2022";  /* FIXED: Using proper CSS escape for bullet */
            color: #3498db;
            font-weight: bold;
            margin-right: 8px;
        }}
        .today-prayer-list .family-list li:before {{
            color: #e67e22;
        }}
        .update-time {{
            text-align: center;
            color: #7f8c8d;
            margin-top: 20px;
            font-style: italic;
        }}
        .note {{
            background-color: #e8f4fd;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 20px 0;
        }}
        @media print {{
            body {{ background: white; }}
            .container {{ box-shadow: none; }}
            .day-nav {{ display: none; }}
            .today-banner {{ display: none !important; }}
        }}
        @media (max-width: 600px) {{
            .day-nav .day-pill {{
                padding: 8px 10px;
                min-width: 40px;
                font-size: 0.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Crossville Church of Christ</h1>
            <h2>Elder Prayer Schedule - Week {week_number}</h2>
            <h3>{date_range}</h3>
        </div>

        <!-- Day-of-week navigation bar: highlights current day -->
        <div class="day-nav" id="dayNav">
    """

    # Generate day pills with data attributes for JS highlighting
    current_date_for_nav = start_date
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        elders_for_day = schedule[day]
        elder_names_for_nav = " & ".join(elders_for_day)
        date_str = current_date_for_nav.strftime('%Y-%m-%d')
        html += f"""        <div class="day-pill" data-date="{date_str}" data-day="{day}">
                {day[:3]}
                <span class="day-label">{current_date_for_nav.strftime('%b %d')}</span>
            </div>
    """
        current_date_for_nav += timedelta(days=1)

    html += f"""    </div>

        <!-- Today's prayer focus banner (shown dynamically via JS) -->
        <div class="today-banner" id="todayBanner">
            <h2>Today's Prayer Focus</h2>
            <div class="today-elder" id="todayElder"></div>
            <div class="today-count" id="todayCount"></div>
        </div>

        <div class="content">
            <div class="note">
                <strong>Note:</strong> Each elder has 19-21 families to ensure complete rotation coverage.
                Monday always has two elders assigned for prayer.
                Daily emails are sent each morning to remind everyone of today's prayer assignment.
            </div>

            <h2>This Week's Prayer Schedule</h2>
            <table class="schedule-table">
                <tr>
                    <th scope="col">Day</th>
                    <th scope="col">Date</th>
                    <th scope="col">Elder(s) Assigned</th>
                </tr>
    """

    # Add daily schedule rows.
    current_date = start_date
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        elders = schedule[day]
        elder_names = " & ".join(elders)
        highlight_class = "highlight" if len(elders) > 1 else ""
        date_attr = current_date.strftime('%Y-%m-%d')

        html += f"""
                <tr class="{highlight_class}" data-date="{date_attr}" data-day="{day}">
                    <td><strong>{day}</strong></td>
                    <td>{current_date.strftime('%B %d')}</td>
                    <td>{elder_names}</td>
                </tr>
        """
        current_date += timedelta(days=1)

    # NOTE: The original template contains trailing whitespace after the
    # </table> line (and before the <h2>).  It is reproduced verbatim here so
    # the emitted HTML is byte-identical to the pre-refactor output.
    html += (
        "\n"
        "            </table>\n"
        "            \n"
        "            <h2>Prayer Lists for This Week</h2>\n"
        "    "
    )

    # Add prayer lists.
    current_date = start_date
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        elders = schedule[day]
        date_attr = current_date.strftime('%Y-%m-%d')

        for elder in elders:
            prayer_group = elder_assignments[elder]

            html += f"""
            <div class="prayer-list" data-date="{date_attr}" data-day="{day}" data-elder="{elder}" data-count="{len(prayer_group)}">
                <h3>{elder} - {day}, {current_date.strftime('%B %d')}</h3>
                <p><em>{len(prayer_group)} families to pray for:</em></p>
                <ul class="family-list">
            """

            for family in prayer_group:
                family_escaped = _escape_html(family)
                html += f"            <li>{family_escaped}</li>\n"

            html += """            </ul>
            </div>
            """

        current_date += timedelta(days=1)

    # Footer with JavaScript for dynamic day highlighting.
    html += f"""
            <div class="update-time">
                Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                <br>Daily emails sent every morning. Schedule regenerated each Monday.
            </div>
        </div>
    </div>

    <script>
    (function() {{
        // Get today's date in YYYY-MM-DD format (local timezone)
        var now = new Date();
        var yyyy = now.getFullYear();
        var mm = String(now.getMonth() + 1).padStart(2, '0');
        var dd = String(now.getDate()).padStart(2, '0');
        var todayStr = yyyy + '-' + mm + '-' + dd;
        var todayDayIdx = now.getDay(); // 0=Sun, 1=Mon, ...

        // Highlight the day pill
        var pills = document.querySelectorAll('.day-pill');
        var foundToday = false;
        pills.forEach(function(pill) {{
            var pillDate = pill.getAttribute('data-date');
            if (pillDate === todayStr) {{
                pill.classList.add('today');
                foundToday = true;
            }} else if (pillDate < todayStr) {{
                pill.classList.add('past');
            }} else {{
                pill.classList.add('future');
            }}
        }});

        // Highlight today's row in the schedule table
        var rows = document.querySelectorAll('.schedule-table tr[data-date]');
        rows.forEach(function(row) {{
            if (row.getAttribute('data-date') === todayStr) {{
                row.classList.add('today-row');
            }}
        }});

        // Highlight today's prayer list sections and show the banner
        var prayerLists = document.querySelectorAll('.prayer-list[data-date]');
        var todayElders = [];
        var todayFamilyCount = 0;
        prayerLists.forEach(function(pl) {{
            if (pl.getAttribute('data-date') === todayStr) {{
                pl.classList.add('today-prayer-list');
                todayElders.push(pl.getAttribute('data-elder'));
                todayFamilyCount += parseInt(pl.getAttribute('data-count') || '0');
            }}
        }});

        // Show the today banner if we found today in the schedule
        if (todayElders.length > 0) {{
            var banner = document.getElementById('todayBanner');
            var elderEl = document.getElementById('todayElder');
            var countEl = document.getElementById('todayCount');
            if (banner && elderEl && countEl) {{
                elderEl.textContent = todayElders.join(' & ');
                countEl.textContent = todayFamilyCount + ' families being prayed for today';
                banner.style.display = 'block';
            }}
        }}
    }})();
    </script>
</body>
</html>
    """

    return html


def generate_text_schedule(
    week_number: int,
    start_date: datetime,
    elder_assignments: dict[str, list[str]],
) -> str:
    """Build the plain-text version of the weekly schedule as a single string."""
    schedule = get_week_schedule(week_number)
    end_date = start_date + timedelta(days=6)
    date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

    text = f"""============================================================
CROSSVILLE CHURCH OF CHRIST
Week {week_number}: {date_range}
============================================================

Note: Monday always has two elders assigned.

"""

    # Add daily schedule.
    current_date = start_date
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        elders = schedule[day]
        elder_names = " & ".join(elders)
        text += f"{day}, {current_date.strftime('%B %d')}: {elder_names}\n"
        current_date += timedelta(days=1)

    text += f"\n{'='*60}\nPRAYER LISTS\n{'='*60}\n"

    # Add prayer lists.
    current_date = start_date
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        elders = schedule[day]

        for elder in elders:
            prayer_group = elder_assignments[elder]

            text += f"\n{elder} - {day}, {current_date.strftime('%B %d')}\n"
            text += f"{'-'*50}\n"
            text += f"{len(prayer_group)} families:\n\n"

            for i, family in enumerate(prayer_group, 1):
                text += f"{i:3}. {family}\n"

            text += "\n"

        current_date += timedelta(days=1)

    text += "=" * 60 + "\n"
    text += "-- Crossville Church of Christ Elder Ministry --\n"

    return text


def generate_schedule_content(
    week_number: int,
    start_date: datetime,
    elder_assignments: dict[str, list[str]],
) -> tuple[str, str]:
    """Return ``(html, text)`` schedule content for the given week."""
    html = generate_html_schedule(week_number, start_date, elder_assignments)
    text = generate_text_schedule(week_number, start_date, elder_assignments)
    return html, text
