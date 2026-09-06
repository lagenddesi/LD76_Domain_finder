"""
LD76 Domain Finder
Gemini Analyzer - Phase 2 Foundation

Purpose:
    Python scanner ke strong candidates ko Gemini se classify karna.

Important design rules:
    - Gemini ko har domain nahi bhejna.
    - Caller sirf already-filtered candidates bheje.
    - Same content hash dobara analyze nahi hoga.
    - Local cache use hogi.
    - Daily/request budget configurable hai.
    - Gemini ko minimum compact evidence bheji jayegi.
    - API key sirf environment variable se li jayegi.
    - APK mein API key kabhi nahi honi chahiye.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
).strip()

GEMINI_DAILY_LIMIT = int(
    os.getenv("GEMINI_DAILY_LIMIT", "50")
)

GEMINI_MAX_REQUESTS = int(
    os.getenv("GEMINI_MAX_REQUESTS", "10")
)

GEMINI_CACHE_FILE = os.getenv(
    "GEMINI_CACHE_FILE",
    "data/gemini_cache.json",
)

GEMINI_REQUEST_DELAY = float(
    os.getenv("GEMINI_REQUEST_DELAY", "2.0")
)

GEMINI_MAX_EVIDENCE_ITEMS = int(
    os.getenv("GEMINI_MAX_EVIDENCE_ITEMS", "12")
)

GEMINI_MAX_EVIDENCE_CHARS = int(
    os.getenv("GEMINI_MAX_EVIDENCE_CHARS", "4500")
)


# ============================================================
# TIME HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()


def utc_date():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d"
    )


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return default


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    temporary_path = path + ".tmp"

    with open(
        temporary_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )

    os.replace(
        temporary_path,
        path,
    )


# ============================================================
# CACHE
# ============================================================

def load_cache():
    cache = load_json(
        GEMINI_CACHE_FILE,
        {},
    )

    if not isinstance(cache, dict):
        return {
            "meta": {},
            "analyses": {},
        }

    if not isinstance(
        cache.get("meta"),
        dict,
    ):
        cache["meta"] = {}

    if not isinstance(
        cache.get("analyses"),
        dict,
    ):
        cache["analyses"] = {}

    return cache


def save_cache(cache):
    save_json(
        GEMINI_CACHE_FILE,
        cache,
    )


# ============================================================
# CONTENT HASH
# ============================================================

def make_content_hash(value):
    """
    Evidence/content ko stable SHA-256 hash deta hai.
    Same content dobara Gemini ko bhejne se bachne ke
    liye use hota hai.
    """

    if isinstance(value, bytes):
        raw = value
    else:
        raw = str(value or "").encode(
            "utf-8",
            errors="replace",
        )

    return hashlib.sha256(raw).hexdigest()


# ============================================================
# REQUEST BUDGET
# ============================================================

def get_daily_usage(cache):
    today = utc_date()

    meta = cache.setdefault(
        "meta",
        {},
    )

    if meta.get("date") != today:
        meta["date"] = today
        meta["requests_today"] = 0

    try:
        return int(
            meta.get(
                "requests_today",
                0,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        meta["requests_today"] = 0
        return 0


def can_make_request(cache):
    usage = get_daily_usage(cache)

    if usage >= GEMINI_DAILY_LIMIT:
        return False

    if GEMINI_MAX_REQUESTS > 0 and usage >= GEMINI_MAX_REQUESTS:
        return False

    return True


def register_request(cache):
    get_daily_usage(cache)

    cache["meta"]["requests_today"] = (
        int(
            cache["meta"].get(
                "requests_today",
                0,
            )
        )
        + 1
    )

    cache["meta"]["last_request_at"] = utc_now()

    save_cache(cache)


# ============================================================
# EVIDENCE COMPACTION
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = re.sub(
        r"\s+",
        " ",
        str(value),
    )

    return value.strip()


def compact_evidence(result):
    """
    Python scanner ke detailed result ko Gemini ke liye
    compact payload mein convert karta hai.

    Gemini ko complete webpage HTML nahi bhejna.
    """

    if not isinstance(result, dict):
        return {
            "domain": "",
            "python_score": 0,
            "signals": [],
            "evidence": [],
        }

    domain = clean_text(
        result.get("domain", "")
    )

    python_score = result.get(
        "score",
        result.get(
            "python_score",
            0,
        ),
    )

    signals = result.get(
        "signals",
        [],
    )

    if not isinstance(
        signals,
        list,
    ):
        signals = []

    evidence_source = result.get(
        "evidence",
        [],
    )

    if not isinstance(
        evidence_source,
        list,
    ):
        evidence_source = []

    compact_items = []

    for item in evidence_source:
        if isinstance(item, dict):
            text = clean_text(
                item.get(
                    "text",
                    item.get(
                        "snippet",
                        "",
                    ),
                )
            )

            category = clean_text(
                item.get(
                    "category",
                    "",
                )
            )

            keyword = clean_text(
                item.get(
                    "keyword",
                    "",
                )
            )

            if text:
                compact_items.append(
                    {
                        "category": category,
                        "keyword": keyword,
                        "text": text[:500],
                    }
                )

        elif isinstance(item, str):
            text = clean_text(item)

            if text:
                compact_items.append(
                    {
                        "category": "",
                        "keyword": "",
                        "text": text[:500],
                    }
                )

        if len(compact_items) >= GEMINI_MAX_EVIDENCE_ITEMS:
            break

    payload = {
        "domain": domain,
        "python_score": python_score,
        "signals": signals[:20],
        "evidence": compact_items,
    }

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    if len(serialized) > GEMINI_MAX_EVIDENCE_CHARS:
        while (
            compact_items
            and len(
                json.dumps(
                    {
                        **payload,
                        "evidence": compact_items,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            ) > GEMINI_MAX_EVIDENCE_CHARS
        ):
            compact_items.pop()

        payload["evidence"] = compact_items

    return payload


# ============================================================
# GEMINI PROMPT
# ============================================================

def build_prompt(compact_data):
    """
    Gemini ko strict JSON classification task deta hai.
    """

    return f"""
You are the secondary classification engine for LD76 Domain Finder.

Your task is defensive web research and website classification.

Do NOT assume that a keyword alone proves fraud.
Classify only from the supplied evidence.

The Python scanner has already filtered this website.
You are receiving compact evidence, not the complete webpage.

Return ONLY valid JSON.
Do not use Markdown.
Do not add explanations outside the JSON.

Required JSON schema:

{{
  "classification": "high_risk_investment|investment_related|payment_or_finance|unclear|not_relevant",
  "confidence": 0,
  "investment_signals": [],
  "payment_methods": [],
  "profit_claims": [],
  "deposit_withdrawal": {{
    "deposit": false,
    "withdrawal": false
  }},
  "referral_signals": [],
  "communication_channels": [],
  "reason": ""
}}

Rules:

1. confidence must be an integer from 0 to 100.
2. Keep arrays short and evidence-based.
3. Do not invent payment methods.
4. Do not invent profit percentages.
5. If evidence contains negative statements such as
   "not an investment" or "do not invest", consider them.
6. "investment" by itself does not automatically mean high risk.
7. High-risk classification should require multiple meaningful
   signals such as investment + profit/return + deposit/withdrawal,
   referral, or similar financial mechanics.
8. If evidence is insufficient, use "unclear".
9. This is website classification, not a legal determination.
10. Keep "reason" concise.

Python scanner data:

{json.dumps(
    compact_data,
    ensure_ascii=False,
    indent=2,
)}
""".strip()


# ============================================================
# GEMINI API
# ============================================================

def call_gemini(prompt):
    """
    Gemini API call.

    API key environment variable se li jati hai.
    Agar key missing ho to request nahi ki jati.

    REST endpoint use kiya gaya hai taake analyzer ko
    SDK-specific implementation se loosely coupled rakha ja sake.
    """

    if not GEMINI_API_KEY:
        return {
            "success": False,
            "error": "GEMINI_API_KEY is not configured.",
        }

    try:
        import requests
    except ImportError:
        return {
            "success": False,
            "error": "requests package is not installed.",
        }

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=30,
        )

    except requests.RequestException as exc:
        return {
            "success": False,
            "error": f"Gemini request failed: {exc}",
        }

    if response.status_code != 200:
        return {
            "success": False,
            "error": (
                f"Gemini HTTP {response.status_code}: "
                f"{response.text[:500]}"
            ),
        }

    try:
        data = response.json()
    except ValueError:
        return {
            "success": False,
            "error": "Gemini returned invalid JSON.",
        }

    return {
        "success": True,
        "data": data,
    }


# ============================================================
# GEMINI RESPONSE PARSER
# ============================================================

def extract_text_from_response(data):
    try:
        candidates = data.get(
            "candidates",
            [],
        )

        if not candidates:
            return ""

        content = candidates[0].get(
            "content",
            {},
        )

        parts = content.get(
            "parts",
            [],
        )

        texts = []

        for part in parts:
            if isinstance(part, dict):
                text = part.get(
                    "text",
                    "",
                )

                if text:
                    texts.append(
                        str(text)
                    )

        return "\n".join(texts).strip()

    except (
        AttributeError,
        TypeError,
    ):
        return ""


def parse_json_response(text):
    """
    Gemini normally direct JSON return karega.

    Safety ke liye accidental code fences bhi remove
    kiye jate hain.
    """

    if not text:
        return None

    text = text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    try:
        parsed = json.loads(text)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    return None


# ============================================================
# RESULT NORMALIZATION
# ============================================================

def normalize_result(result):
    if not isinstance(
        result,
        dict,
    ):
        return None

    classification = clean_text(
        result.get(
            "classification",
            "unclear",
        )
    )

    allowed = {
        "high_risk_investment",
        "investment_related",
        "payment_or_finance",
        "unclear",
        "not_relevant",
    }

    if classification not in allowed:
        classification = "unclear"

    try:
        confidence = int(
            result.get(
                "confidence",
                0,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        confidence = 0

    confidence = max(
        0,
        min(
            100,
            confidence,
        ),
    )

    def clean_list(value):
        if not isinstance(
            value,
            list,
        ):
            return []

        cleaned = []

        for item in value[:10]:
            item = clean_text(item)

            if item:
                cleaned.append(item)

        return cleaned

    deposit_withdrawal = result.get(
        "deposit_withdrawal",
        {},
    )

    if not isinstance(
        deposit_withdrawal,
        dict,
    ):
        deposit_withdrawal = {}

    return {
        "classification": classification,
        "confidence": confidence,
        "investment_signals": clean_list(
            result.get(
                "investment_signals",
                [],
            )
        ),
        "payment_methods": clean_list(
            result.get(
                "payment_methods",
                [],
            )
        ),
        "profit_claims": clean_list(
            result.get(
                "profit_claims",
                [],
            )
        ),
        "deposit_withdrawal": {
            "deposit": bool(
                deposit_withdrawal.get(
                    "deposit",
                    False,
                )
            ),
            "withdrawal": bool(
                deposit_withdrawal.get(
                    "withdrawal",
                    False,
                )
            ),
        },
        "referral_signals": clean_list(
            result.get(
                "referral_signals",
                [],
            )
        ),
        "communication_channels": clean_list(
            result.get(
                "communication_channels",
                [],
            )
        ),
        "reason": clean_text(
            result.get(
                "reason",
                "",
            )
        )[:1000],
    }


# ============================================================
# MAIN ANALYZER
# ============================================================

def analyze_candidate(
    scanner_result,
    *,
    force=False,
):
    """
    Strong Python candidate ko Gemini se analyze karta hai.

    force=True sirf intentional manual re-analysis ke liye hai.

    Normal flow:
        candidate
        -> content hash
        -> cache check
        -> budget check
        -> Gemini
        -> cache
        -> result
    """

    if not isinstance(
        scanner_result,
        dict,
    ):
        return {
            "success": False,
            "status": "invalid_input",
            "error": "Scanner result must be a dictionary.",
        }

    compact_data = compact_evidence(
        scanner_result
    )

    domain = compact_data.get(
        "domain",
        "",
    )

    if not domain:
        return {
            "success": False,
            "status": "invalid_input",
            "error": "Candidate domain is missing.",
        }

    # Prefer the scanner's real content hash.
    content_hash = clean_text(
        scanner_result.get(
            "content_hash",
            "",
        )
    )

    if not content_hash:
        content_hash = make_content_hash(
            json.dumps(
                compact_data,
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    cache = load_cache()

    analyses = cache.setdefault(
        "analyses",
        {},
    )

    cached = analyses.get(
        content_hash
    )

    if cached and not force:
        return {
            "success": True,
            "status": "cache_hit",
            "cached": True,
            "domain": domain,
            "content_hash": content_hash,
            "analysis": cached.get(
                "analysis"
            ),
        }

    if not GEMINI_API_KEY:
        return {
            "success": False,
            "status": "not_configured",
            "domain": domain,
            "content_hash": content_hash,
            "error": "GEMINI_API_KEY is not configured.",
        }

    if not can_make_request(cache):
        return {
            "success": False,
            "status": "budget_exhausted",
            "domain": domain,
            "content_hash": content_hash,
            "error": "Gemini request budget exhausted.",
        }

    # Small delay between requests.
    last_request_at = cache.get(
        "meta",
        {},
    ).get(
        "last_request_at"
    )

    if last_request_at:
        try:
            last_timestamp = datetime.fromisoformat(
                last_request_at
            ).timestamp()

            elapsed = time.time() - last_timestamp

            if elapsed < GEMINI_REQUEST_DELAY:
                time.sleep(
                    GEMINI_REQUEST_DELAY - elapsed
                )

        except (
            ValueError,
            TypeError,
        ):
            pass

    prompt = build_prompt(
        compact_data
    )

    register_request(
        cache
    )

    api_result = call_gemini(
        prompt
    )

    if not api_result.get(
        "success"
    ):
        return {
            "success": False,
            "status": "api_error",
            "domain": domain,
            "content_hash": content_hash,
            "error": api_result.get(
                "error",
                "Unknown Gemini error.",
            ),
        }

    response_text = extract_text_from_response(
        api_result.get(
            "data",
            {},
        )
    )

    parsed = parse_json_response(
        response_text
    )

    if parsed is None:
        return {
            "success": False,
            "status": "invalid_model_response",
            "domain": domain,
            "content_hash": content_hash,
            "error": "Gemini response could not be parsed as JSON.",
            "raw_response": response_text[:2000],
        }

    normalized = normalize_result(
        parsed
    )

    if normalized is None:
        return {
            "success": False,
            "status": "invalid_model_result",
            "domain": domain,
            "content_hash": content_hash,
            "error": "Gemini result normalization failed.",
        }

    # Cache by content hash.
    analyses[content_hash] = {
        "domain": domain,
        "content_hash": content_hash,
        "analyzed_at": utc_now(),
        "model": GEMINI_MODEL,
        "analysis": normalized,
    }

    save_cache(
        cache
    )

    return {
        "success": True,
        "status": "analyzed",
        "cached": False,
        "domain": domain,
        "content_hash": content_hash,
        "analysis": normalized,
    }


# ============================================================
# SIMPLE TEST
# ============================================================

if __name__ == "__main__":
    print("LD76 Gemini Analyzer")
    print("--------------------")

    if GEMINI_API_KEY:
        print("API key: configured")
    else:
        print("API key: NOT configured")

    print(f"Model: {GEMINI_MODEL}")
    print(f"Daily limit: {GEMINI_DAILY_LIMIT}")
    print(f"Request limit: {GEMINI_MAX_REQUESTS}")
    print(f"Cache: {GEMINI_CACHE_FILE}")

    cache = load_cache()

    print(
        "Requests today:",
        get_daily_usage(cache),
    )

    print(
        "Budget available:",
        can_make_request(cache),
                 )
