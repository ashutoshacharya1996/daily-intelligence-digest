# Daily Intelligence Digest — Live Version 1

A deliberately small RSS pipeline that collects recent articles, removes duplicate URLs,
classifies stories with transparent keyword rules, and writes a Markdown digest. It uses no
AI API, database, server, or framework.

## Run it

1. Install Python 3.11 or newer.
2. Create and activate a virtual environment.
3. Install dependencies: `python -m pip install -r requirements.txt`
4. Run: `python digest.py`
5. Open `daily_digest.md`.

To preview the website, run `python digest.py --site-dir docs` and open `docs/index.html`.

Use `python digest.py --hours 30` to change the collection window. Edit `feeds.json` to
replace or add feeds, and edit `TOPICS` in `digest.py` to tune classification.

Feed items without a publication timestamp or without a taxonomy keyword are intentionally
excluded. A broken feed is reported at the bottom of the digest while the remaining feeds
continue to work.

## Check it

Install the development requirements with `python -m pip install -r requirements-dev.txt`,
then run `python -m pytest`.

## Live deployment

The GitHub Actions workflow runs at 06:00 IST every day and can also be started manually
from the repository's **Actions** tab. It collects the latest feed items, builds the website,
saves a dated archive, and deploys it through GitHub Pages.

For the first deployment, open **Settings → Pages** in GitHub and set **Source** to
**GitHub Actions**. Then open **Actions → Build and publish daily digest → Run workflow**.

## Roadmap

This remains the transparent, rules-based release. Fuzzy headline matching, event clustering,
AI summaries, historical memory, and email delivery are intentionally staged as later upgrades.
