from datetime import datetime, timezone

from digest import canonicalize_url, classify, deduplicate, render, render_html


def test_canonicalize_url_removes_tracking_and_fragment():
    url = "HTTPS://Example.COM/story/?utm_source=x&at_medium=RSS&id=7&fbclid=y#section"
    assert canonicalize_url(url) == "https://example.com/story?id=7"


def test_classify_topics_and_reject_irrelevant_content():
    assert classify("Federal Reserve holds interest rates", "Bond yields fell") == "Financial"
    assert classify("New multimodal AI model", "The system uses GPUs") == "AI"
    assert classify("Ceasefire talks resume", "Diplomacy continues") == "Geopolitics"
    assert classify("Local art exhibition opens", "Paintings are on display") is None
    assert classify("China's second typhoon makes landfall", "Heavy rain is forecast") is None


def test_deduplicate_keeps_one_canonical_url():
    date = datetime(2026, 7, 12, tzinfo=timezone.utc)
    article = {"url": "https://example.com/a", "published_at": date}
    assert len(deduplicate([article, dict(article)])) == 1


def test_render_contains_all_sections():
    output = render([], datetime(2026, 7, 12, tzinfo=timezone.utc), 24, [])
    assert "## Financial" in output
    assert "## AI" in output
    assert "## Geopolitics" in output


def test_html_is_standalone_and_escapes_titles():
    date = datetime(2026, 7, 12, tzinfo=timezone.utc)
    article = {
        "title": "Markets < AI", "url": "https://example.com/a?x=1&y=2",
        "source": "Example", "published_at": date, "topic": "AI",
    }
    output = render_html([article], date, 24, [])
    assert "<!doctype html>" in output
    assert "Markets &lt; AI" in output
    assert "x=1&amp;y=2" in output
