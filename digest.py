"""Build a simple, rules-based daily news digest from RSS/Atom feeds."""

from __future__ import annotations

import argparse
import calendar
import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser


TOPICS = {
    "Financial": {
        "inflation", "interest rate", "central bank", "gdp", "employment",
        "bond", "yield", "equity", "stock", "market", "currency", "oil",
        "commodity", "earnings", "merger", "bankruptcy", "investment",
        "rbi", "sebi", "nifty", "fiscal", "federal reserve", "economy",
    },
    "AI": {
        "artificial intelligence", " ai ", "machine learning", "foundation model",
        "language model", "multimodal", "open source model", "ai agent",
        "automation", "gpu", "data centre", "data center", "semiconductor",
        "robotics", "openai", "anthropic", "deepmind", "nvidia", "chatgpt",
    },
    "Geopolitics": {
        "military", "war", "conflict", "ceasefire", "sanction", "defence",
        "defense", "diplomacy", "summit", "treaty", "nato", "united nations",
        "trade restriction", "export control", "critical mineral", "energy security",
        "government", "prime minister", "president", "foreign minister", "border",
        "election", "gaza", "west bank", "middle east", "indo-pacific",
    },
}

TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def canonicalize_url(url: str) -> str:
    """Remove fragments and common tracking parameters from a URL."""
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith(("utm_", "at_")) and key.lower() not in TRACKING_PARAMETERS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def entry_datetime(entry: dict) -> datetime | None:
    """Return an RSS entry timestamp in UTC, if the feed supplied one."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def classify(title: str, description: str) -> str | None:
    """Choose the topic with the most keyword matches; reject unmatched items."""
    searchable = f" {title} {description} ".lower()
    scores = {
        topic: sum(1 for keyword in keywords if keyword in searchable)
        for topic, keywords in TOPICS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else None


def collect(feeds: list[dict], since: datetime) -> tuple[list[dict], list[str]]:
    articles: list[dict] = []
    warnings: list[str] = []
    for source in feeds:
        result = feedparser.parse(source["url"], request_headers={"User-Agent": "DailyDigest/1.0"})
        if result.get("bozo") and not result.entries:
            warnings.append(f'{source["name"]}: feed could not be read')
            continue
        for entry in result.entries:
            published_at = entry_datetime(entry)
            if published_at is None or published_at < since:
                continue
            title = clean_text(entry.get("title", ""))
            description = clean_text(entry.get("summary", entry.get("description", "")))
            url = canonicalize_url(entry.get("link", ""))
            topic = classify(title, description)
            if not title or not url or topic is None:
                continue
            articles.append({
                "id": hashlib.sha256(url.encode()).hexdigest()[:12],
                "title": title,
                "url": url,
                "source": source["name"],
                "published_at": published_at,
                "topic": topic,
            })
    return articles, warnings


def deduplicate(articles: list[dict]) -> list[dict]:
    unique: dict[str, dict] = {}
    for article in articles:
        unique.setdefault(article["url"], article)
    return sorted(unique.values(), key=lambda item: item["published_at"], reverse=True)


def render(articles: list[dict], generated_at: datetime, hours: int, warnings: list[str]) -> str:
    lines = [
        f"# Daily Intelligence Digest — {generated_at:%d %B %Y}",
        "",
        f"Collected {len(articles)} relevant articles published in the previous {hours} hours.",
        "",
    ]
    for topic in TOPICS:
        lines.extend([f"## {topic}", ""])
        matches = [article for article in articles if article["topic"] == topic]
        if not matches:
            lines.extend(["_No matching articles found._", ""])
            continue
        for article in matches:
            timestamp = article["published_at"].strftime("%H:%M UTC")
            lines.append(f'- [{article["title"]}]({article["url"]}) — {article["source"]} ({timestamp})')
        lines.append("")
    lines.extend(["---", "", f"* {len(articles)} unique, relevant articles included"])
    if warnings:
        lines.append(f"* {len(warnings)} feed warning(s): " + "; ".join(warnings))
    return "\n".join(lines) + "\n"


def render_html(articles: list[dict], generated_at: datetime, hours: int, warnings: list[str]) -> str:
    """Render a standalone, responsive page suitable for GitHub Pages."""
    topic_cards = []
    for topic in TOPICS:
        matches = [article for article in articles if article["topic"] == topic]
        items = []
        for article in matches:
            items.append(
                '<article class="story">'
                f'<a href="{html.escape(article["url"], quote=True)}" target="_blank" rel="noopener">'
                f'{html.escape(article["title"])}</a>'
                f'<div class="meta">{html.escape(article["source"])} · '
                f'{article["published_at"]:%H:%M UTC}</div></article>'
            )
        content = "".join(items) or '<p class="empty">No matching developments today.</p>'
        topic_cards.append(
            f'<section><div class="section-title"><h2>{topic}</h2>'
            f'<span>{len(matches)} stories</span></div>{content}</section>'
        )
    warning_html = ""
    if warnings:
        warning_html = f'<p class="warning">{len(warnings)} feed warning(s): {html.escape("; ".join(warnings))}</p>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="A daily briefing on financial markets, AI and geopolitics.">
<title>Daily Intelligence Digest</title><style>
:root{{--ink:#172033;--muted:#667085;--paper:#f4f1ea;--card:#fff;--accent:#175cd3;--line:#ddd8ce}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}}
header{{background:#111827;color:white;padding:56px 20px 44px}}.wrap{{max-width:920px;margin:auto}}.kicker{{color:#9ec5ff;font-size:13px;font-weight:700;letter-spacing:.13em;text-transform:uppercase}}
h1{{font-family:Georgia,serif;font-size:clamp(38px,7vw,68px);line-height:1.02;margin:12px 0}}header p{{color:#cbd5e1;max-width:650px;margin:0}}
.stats{{display:flex;gap:12px;flex-wrap:wrap;margin-top:26px}}.pill{{background:#ffffff16;border:1px solid #ffffff24;border-radius:999px;padding:7px 12px;font-size:13px}}
main{{padding:28px 20px 64px}}section{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px;margin:18px 0;box-shadow:0 4px 20px #1720330a}}
.section-title{{display:flex;align-items:baseline;justify-content:space-between;border-bottom:1px solid var(--line);margin-bottom:5px}}h2{{font:700 27px Georgia,serif;margin:0 0 15px}}.section-title span,.meta{{color:var(--muted);font-size:13px}}
.story{{padding:17px 0;border-bottom:1px solid #eeeae2}}.story:last-child{{border:0}}.story a{{color:var(--ink);font:700 19px/1.35 Georgia,serif;text-decoration:none}}.story a:hover{{color:var(--accent);text-decoration:underline}}.meta{{margin-top:6px}}.empty,.warning{{color:var(--muted)}}
footer{{text-align:center;color:var(--muted);font-size:13px;padding:0 20px 40px}}@media(max-width:560px){{header{{padding-top:38px}}section{{padding:18px}}}}
</style></head><body><header><div class="wrap"><div class="kicker">Independent daily briefing</div>
<h1>Daily Intelligence Digest</h1><p>Financial markets, artificial intelligence and geopolitics—filtered from trusted feeds without hype.</p>
<div class="stats"><span class="pill">{generated_at:%d %B %Y}</span><span class="pill">{len(articles)} relevant articles</span><span class="pill">Previous {hours} hours</span></div></div></header>
<main class="wrap">{''.join(topic_cards)}{warning_html}</main>
<footer>Automatically refreshed daily · Rules-based Version 1 · Source links open original reporting</footer></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feeds", type=Path, default=Path("feeds.json"))
    parser.add_argument("--output", type=Path, default=Path("daily_digest.md"))
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--site-dir", type=Path, help="Also write a live site and dated archive")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    feeds = json.loads(args.feeds.read_text(encoding="utf-8"))
    collected, warnings = collect(feeds, now - timedelta(hours=args.hours))
    articles = deduplicate(collected)
    args.output.write_text(render(articles, now, args.hours, warnings), encoding="utf-8")
    if args.site_dir:
        args.site_dir.mkdir(parents=True, exist_ok=True)
        archive = args.site_dir / "archive"
        archive.mkdir(exist_ok=True)
        page = render_html(articles, now, args.hours, warnings)
        (args.site_dir / "index.html").write_text(page, encoding="utf-8")
        (archive / f"{now:%Y-%m-%d}.html").write_text(page, encoding="utf-8")
        (args.site_dir / ".nojekyll").touch()
    print(f"Created {args.output} with {len(articles)} articles.")


if __name__ == "__main__":
    main()
