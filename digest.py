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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feeds", type=Path, default=Path("feeds.json"))
    parser.add_argument("--output", type=Path, default=Path("daily_digest.md"))
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    feeds = json.loads(args.feeds.read_text(encoding="utf-8"))
    collected, warnings = collect(feeds, now - timedelta(hours=args.hours))
    articles = deduplicate(collected)
    args.output.write_text(render(articles, now, args.hours, warnings), encoding="utf-8")
    print(f"Created {args.output} with {len(articles)} articles.")


if __name__ == "__main__":
    main()
