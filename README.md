# The Daily Scoop 🗞️

World news rewritten for English learners — a fresh edition every morning.

- Six categories: Business, Economics, Politics, Sports, Finance, Entertainment.
- Home page of top headlines; five stories per category.
- Every article at **three reading levels** (Beginner / Intermediate / Advanced) with a
  **vocabulary list**, the article, and **two comprehension questions**.
- **Fast Reading** (bionic) toggle, and mobile **Back / Top** buttons.

## How it works
`generate.py` scans world RSS feeds per category and, with Gemini, writes each story at
three levels plus study aids into `data/edition.json`; `build_site.py` renders it into a
single mobile-friendly `docs/index.html` served by GitHub Pages. It rebuilds daily via
GitHub Actions.

## Setup
1. Add a free Gemini key as repo secret `GEMINI_API_KEY` (Settings → Secrets → Actions).
2. Enable Pages: Settings → Pages → Deploy from branch → main / /docs.
3. Actions → **Build Daily Scoop** → Run workflow.

It's AI-simplified news for study; tap "Read the original" to see the source article.

## Local preview (no key)
```
python src/build_site.py --edition config/mock_edition.json
```
