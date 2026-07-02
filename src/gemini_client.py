"""Free Gemini API wrapper with rate pacing + descriptive errors."""
import json, os, time, urllib.error, urllib.request

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
STATUS = {"ok": 0, "fail": 0, "last_error": None}
MIN_INTERVAL = float(os.environ.get("GEMINI_MIN_INTERVAL", "5"))
_LAST = [0.0]


def available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _pace():
    gap = time.time() - _LAST[0]
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)
    _LAST[0] = time.time()


def generate_json(prompt, retries=3, max_output_tokens=8192):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json",
                                 "maxOutputTokens": max_output_tokens}}
    url = ENDPOINT.format(model=MODEL) + "?key=" + key
    data = json.dumps(body).encode("utf-8")
    for attempt in range(retries):
        try:
            _pace()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            cands = payload.get("candidates")
            if not cands:
                raise RuntimeError(f"no candidates; {payload.get('promptFeedback')}")
            parts = (cands[0].get("content") or {}).get("parts")
            if not parts:
                raise RuntimeError(f"empty; finishReason={cands[0].get('finishReason')}")
            result = json.loads(parts[0].get("text", ""))
            STATUS["ok"] += 1
            return result
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(30 * (attempt + 1)); continue
            STATUS["fail"] += 1; STATUS["last_error"] = f"HTTP {e.code}"
            print(f"[gemini] HTTP {e.code}: {e.read()[:160]!r}")
            return None
        except Exception as e:  # noqa: BLE001
            print(f"[gemini] {type(e).__name__}: {e}")
            if attempt < retries - 1:
                time.sleep(5); continue
            STATUS["fail"] += 1; STATUS["last_error"] = str(e)
            return None
    return None
