"""
Build the daily English-learner edition.

One Gemini call per article returns THREE reading levels + a teaser excerpt +
an English vocabulary list + two comprehension questions. Resilient: an article
that can't be generated falls back to the feed's own text (no study aids).

Run in CI (GEMINI_API_KEY set):  python src/generate.py
"""
import datetime as dt
import hashlib
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(__file__))
import scanner          # noqa: E402
import gemini_client    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS = ["Beginner", "Intermediate", "Advanced"]


def load_cfg():
    with open(os.path.join(ROOT, "config", "categories.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def aid(link, title):
    return "a" + hashlib.md5((link or title).encode("utf-8")).hexdigest()[:10]


def make_article(item):
    prompt = (
        "You help people learn English by reading world news. Using the news item "
        "below, write a clear, self-contained article IN ENGLISH at three difficulty "
        "levels, plus study aids. Stay faithful to the facts in the source; do not "
        "invent specific numbers, names, or quotes. Neutral, factual news tone.\n\n"
        "Levels:\n"
        "- Beginner: short simple sentences, very common words (~150 words).\n"
        "- Intermediate: clear everyday English (~280 words).\n"
        "- Advanced: natural news English (~320 words).\n\n"
        "Return JSON: {"
        '"headline": str (clear, <=12 words), '
        '"excerpt": str (one ~20-word teaser sentence), '
        '"levels": {"Beginner": str, "Intermediate": str, "Advanced": str}, '
        '"vocab": [{"word": str, "definition": str (simple English definition)}] (6-8 useful words from the article), '
        '"questions": [{"q": str, "a": str (short answer)}] (exactly 2 reading-comprehension questions)'
        "}\n\n"
        f"NEWS ITEM:\nHeadline: {item['title']}\nSource: {item['source']}\n"
        f"Summary: {item['summary']}"
    )
    r = gemini_client.generate_json(prompt)
    if isinstance(r, dict) and isinstance(r.get("levels"), dict) and r["levels"].get("Intermediate"):
        return {
            "headline": str(r.get("headline") or item["title"]).strip(),
            "excerpt": str(r.get("excerpt", "")).strip(),
            "levels": {lv: str(r["levels"].get(lv, "")).strip() for lv in LEVELS},
            "vocab": r.get("vocab", []) if isinstance(r.get("vocab"), list) else [],
            "questions": r.get("questions", []) if isinstance(r.get("questions"), list) else [],
        }
    # fallback: no study aids, just the feed text
    body = item.get("summary") or "Full article unavailable. Tap the source link to read more."
    return {"headline": item["title"], "excerpt": body[:140],
            "levels": {lv: body for lv in LEVELS}, "vocab": [], "questions": []}


def main():
    cfg = load_cfg()
    n = int(cfg.get("articles_per_category", 5))
    print(f"[gen] LLM available: {gemini_client.available()}")
    scanned = scanner.collect(cfg, per_category=n + 3)

    edition = {"built": dt.datetime.utcnow().strftime("%Y-%m-%d"), "categories": [], "home": []}
    for cat in cfg["categories"]:
        items = scanned.get(cat["key"], [])[:n]
        articles = []
        for i, item in enumerate(items):
            print(f"[gen] {cat['key']} {i+1}/{len(items)}: {item['title'][:50]}")
            art = make_article(item)
            art.update({"id": aid(item["link"], item["title"]), "source": item["source"],
                        "link": item["link"], "published": item["published"],
                        "category": cat["key"]})
            articles.append(art)
        edition["categories"].append({"key": cat["key"], "title": cat["title"], "articles": articles})
        if articles:  # lead story of each category feeds the homepage
            lead = dict(articles[0]); lead["category_title"] = cat["title"]
            edition["home"].append(lead)

    d = os.path.join(ROOT, "data")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "edition.json"), "w", encoding="utf-8") as f:
        json.dump(edition, f, ensure_ascii=False, indent=2)
    with open(os.path.join(d, "_diag.json"), "w", encoding="utf-8") as f:
        json.dump({"available": gemini_client.available(), "gemini": gemini_client.STATUS}, f, indent=2)
    total = sum(len(c["articles"]) for c in edition["categories"])
    print(f"[gen] wrote edition.json ({total} articles); gemini ok/fail="
          f"{gemini_client.STATUS['ok']}/{gemini_client.STATUS['fail']}")


if __name__ == "__main__":
    main()
