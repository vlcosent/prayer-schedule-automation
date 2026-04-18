"""Generate the GitHub Pages landing page (`index.html`).

Produces a static landing page that links to the current week's schedule
and shows a chronological archive of prior weeks. Called from the
deploy-pages workflow so the archive list is always current.

Reads:
  - `archive/Prayer_Schedule_<YYYY-MM-DD>_Week<N>.txt` filenames (no file contents)
  - `Prayer_Schedule_Current_Week.html` (to confirm it exists; not parsed)

Writes:
  - `index.html` (overwrites the existing redirect stub)
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from html import escape


ARCHIVE_RE = re.compile(
    r"^Prayer_Schedule_(?P<date>\d{4}-\d{2}-\d{2})_Week(?P<week>\d+)\.txt$"
)


def collect_archive_entries(archive_dir: str) -> list[dict]:
    """Return archive entries sorted newest-first."""
    if not os.path.isdir(archive_dir):
        return []

    entries: list[dict] = []
    for name in os.listdir(archive_dir):
        m = ARCHIVE_RE.match(name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group("date"), "%Y-%m-%d").date()
        except ValueError:
            continue
        entries.append({
            "filename": name,
            "date": d,
            "week": int(m.group("week")),
        })
    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


def render(entries: list[dict], current_exists: bool) -> str:
    current_link = (
        '<a class="current-link" href="Prayer_Schedule_Current_Week.html">'
        "View This Week&rsquo;s Schedule &rarr;</a>"
        if current_exists
        else '<p class="current-missing">Current week schedule not yet generated.</p>'
    )

    if entries:
        rows = []
        for e in entries:
            pretty_date = e["date"].strftime("%A, %B %d, %Y")
            rows.append(
                f'<li><a href="archive/{escape(e["filename"])}">'
                f'Week {e["week"]} &middot; {escape(pretty_date)}'
                "</a></li>"
            )
        archive_block = (
            '<section aria-labelledby="archive-heading">'
            '<h2 id="archive-heading">Archive</h2>'
            f'<p class="count">{len(entries)} prior schedule(s)</p>'
            f'<ul class="archive">{"".join(rows)}</ul>'
            "</section>"
        )
    else:
        archive_block = (
            '<section aria-labelledby="archive-heading">'
            '<h2 id="archive-heading">Archive</h2>'
            '<p>No archived schedules yet.</p>'
            "</section>"
        )

    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Crossville Church of Christ &mdash; Prayer Schedule</title>
    <meta name="description" content="Elder prayer schedule for Crossville Church of Christ: current week plus archive.">
    <style>
        :root {{ color-scheme: light dark; }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            background: #f5f5f5;
            color: #222;
            line-height: 1.5;
        }}
        header {{
            background: #2c3e50;
            color: #fff;
            padding: 28px 20px 24px;
            text-align: center;
        }}
        header h1 {{ margin: 0 0 6px; font-size: 1.7rem; }}
        header p {{ margin: 0; color: #cfd8dc; font-size: 0.95rem; }}
        main {{ max-width: 760px; margin: 0 auto; padding: 24px 20px 40px; }}
        .current-link {{
            display: block;
            background: #e67e22;
            color: #fff;
            text-decoration: none;
            text-align: center;
            padding: 18px 20px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 1.15rem;
            margin: 0 0 28px;
        }}
        .current-link:focus {{ outline: 3px solid #fff; outline-offset: 2px; }}
        .current-missing {{
            background: #fff3cd;
            color: #614400;
            padding: 14px 18px;
            border-radius: 8px;
            margin: 0 0 28px;
        }}
        section h2 {{ margin: 0 0 6px; font-size: 1.2rem; color: #2c3e50; }}
        .count {{ margin: 0 0 12px; color: #666; font-size: 0.9rem; }}
        ul.archive {{ list-style: none; padding: 0; margin: 0; }}
        ul.archive li {{
            border-bottom: 1px solid #e0e3e7;
        }}
        ul.archive a {{
            display: block;
            padding: 12px 4px;
            color: #2c3e50;
            text-decoration: none;
        }}
        ul.archive a:hover,
        ul.archive a:focus {{
            background: #eef3f7;
            outline: none;
        }}
        footer {{
            max-width: 760px;
            margin: 0 auto;
            padding: 16px 20px 32px;
            color: #666;
            font-size: 0.85rem;
            text-align: center;
        }}
        @media (prefers-color-scheme: dark) {{
            body {{ background: #1a1f24; color: #e8ebed; }}
            header {{ background: #1a252f; }}
            section h2 {{ color: #d0d9e2; }}
            ul.archive li {{ border-color: #333a40; }}
            ul.archive a {{ color: #d0d9e2; }}
            ul.archive a:hover, ul.archive a:focus {{ background: #262c32; }}
            .count, footer {{ color: #aab0b6; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Crossville Church of Christ</h1>
        <p>Elder Prayer Schedule</p>
    </header>
    <main>
        {current_link}
        {archive_block}
    </main>
    <footer>
        <p>Schedule rotates 8 elders through church families on an 8-week cycle.<br>
           Generated {generated}</p>
    </footer>
</body>
</html>
"""


def main() -> int:
    base = os.path.dirname(os.path.abspath(__file__))
    archive_dir = os.path.join(base, "archive")
    current = os.path.join(base, "Prayer_Schedule_Current_Week.html")
    out_path = os.path.join(base, "index.html")

    entries = collect_archive_entries(archive_dir)
    html = render(entries, current_exists=os.path.exists(current))

    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, out_path)
    print(f"[OK] Wrote {out_path} with {len(entries)} archive entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
