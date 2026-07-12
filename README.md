# Daily Intelligence Digest — Version 1

A deliberately small RSS pipeline that collects recent articles, removes duplicate URLs,
classifies stories with transparent keyword rules, and writes a Markdown digest. It uses no
AI API, database, server, or framework.

## Run it

1. Install Python 3.11 or newer.
2. Create and activate a virtual environment.
3. Install dependencies: `python -m pip install -r requirements.txt`
4. Run: `python digest.py`
5. Open `daily_digest.md`.

Use `python digest.py --hours 30` to change the collection window. Edit `feeds.json` to
replace or add feeds, and edit `TOPICS` in `digest.py` to tune classification.

Feed items without a publication timestamp or without a taxonomy keyword are intentionally
excluded. A broken feed is reported at the bottom of the digest while the remaining feeds
continue to work.

## Check it

Install the development requirements with `python -m pip install -r requirements-dev.txt`,
then run `python -m pytest`.

## Scope

This is the first milestone only. Fuzzy headline matching, event clustering, summaries,
historical memory, email delivery, and scheduling belong in later versions after this basic
pipeline is producing useful output consistently.
