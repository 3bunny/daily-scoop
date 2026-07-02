"""Scan world-news RSS feeds per category. Returns recent, de-duplicated items."""
import html
import re
from datetime import datetime, timedelta, timezone

import feedparser
from dateutil import parser as dateparser

KST = timezone(timedelta(hours=9))
UA = "DailyScoop/1.0 (English-learning news reader; eelcchrisyoo@gmail.com)"


def _clean(t):
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def _published(entry):
    for a in ("published", "updated", "created"):
        v = entry.get(a)
        if v:
            try:
                d = dateparser.parse(v)
                if d.tzinfo is None:
                    d = d.replace(tzinfo=timezone.utc)
                return d.astimezone(KST)
            except (ValueError, TypeError):
                continue
    return None


def collect(config, per_category=8, mock=None):
    if mock:
        import json
        return json.load(open(mock, encoding="utf-8"))
    lookback = int(config.get("lookback_hours", 30))
    cutoff = datetime.now(KST) - timedelta(hours=lookback)
    out = {}
    for cat in config["categories"]:
        seen, items = set(), []
        for url in cat.get("feeds", []):
            try:
                parsed = feedparser.parse(url, agent=UA)
            except Exception as e:  # noqa: BLE001
                print(f"[scan] {cat['key']} failed {url}: {e}")
                continue
            src = (parsed.feed.get("title") if parsed.feed else "") or "News"
            for e in parsed.entries:
                title = _clean(e.get("title", ""))
                if not title:
                    continue
                norm = re.sub(r"[^a-z0-9]", "", title.lower())[:60]
                if norm in seen:
                    continue
                pub = _published(e)
                if pub and pub < cutoff:
                    continue
                seen.add(norm)
                items.append({
                    "title": title, "link": e.get("link", ""), "source": src.strip(),
                    "published": (pub or datetime.now(KST)).isoformat(),
                    "summary": _clean(e.get("summary", ""))[:1000]})
        items.sort(key=lambda x: x["published"], reverse=True)
        out[cat["key"]] = items[:per_category]
        print(f"[scan] {cat['key']}: {len(items[:per_category])} items")
    return out
