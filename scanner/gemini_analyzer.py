"""
LD76 Domain Finder
Gemini Analyzer - Rate-Limited Production Layer

Purpose:
Python scanner ke strong candidates ko Gemini se classify karna.

Design:
- Gemini ko har domain nahi bhejna.
- Same content hash dobara analyze nahi hoga.
- Thread-safe cache and request budget.
- Daily/request hard limits.
- Compact evidence only.
- API key environment variable se.
- APK mein API key nahi.
"""

import hashlib
import json
import os
import re
import threading
import time
from datetime import datetime, timezone

import requests

============================================================

CONFIGURATION

============================================================

GEMINI_API_KEY = os.getenv(
"GEMINI_API_KEY",
"",
).strip()

GEMINI_MODEL = os.getenv(
"GEMINI_MODEL",
"gemini-2.5-flash",
).strip()

GEMINI_DAILY_LIMIT = max(
0,
int(os.getenv("GEMINI_DAILY_LIMIT", "50")),
)

GEMINI_MAX_REQUESTS = max(
0,
int(os.getenv("GEMINI_MAX_REQUESTS", "10")),
)

GEMINI_CACHE_FILE = os.getenv(
"GEMINI_CACHE_FILE",
"data/gemini_cache.json",
)

GEMINI_REQUEST_DELAY = max(
0.0,
float(os.getenv("GEMINI_REQUEST_DELAY", "2.0")),
)

GEMINI_MAX_EVIDENCE_ITEMS = max(
1,
int(os.getenv("GEMINI_MAX_EVIDENCE_ITEMS", "12")),
)

GEMINI_MAX_EVIDENCE_CHARS = max(
500,
int(os.getenv("GEMINI_MAX_EVIDENCE_CHARS", "4500")),
)

GEMINI_HTTP_TIMEOUT = max(
5,
int(os.getenv("GEMINI_HTTP_TIMEOUT", "30")),
)

GEMINI_MAX_RETRIES = max(
0,
int(os.getenv("GEMINI_MAX_RETRIES", "1")),
)

============================================================

GLOBAL LOCK

============================================================

Queue concurrent ho sakti hai, lekin cache/budget mutation

ek waqt mein sirf ek thread karega.

_CACHE_LOCK = threading.RLock()

============================================================

TIME HELPERS

============================================================

def utc_now():
return datetime.now(
timezone.utc
).replace(
microsecond=0
).isoformat()

def utc_date():
return datetime.now(
timezone.utc
).strftime(
"%Y-%m-%d"
)

============================================================

JSON HELPERS

============================================================

def load_json(path, default):
if not os.path.exists(path):
return default

try:
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)

except (
    OSError,
    json.JSONDecodeError,
):
    return default

def save_json(path, data):
directory = os.path.dirname(path)

if directory:
    os.makedirs(
        directory,
        exist_ok=True,
    )

temporary_path = (
    path + ".tmp"
)

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

============================================================

CACHE

============================================================

def load_cache():
cache = load_json(
GEMINI_CACHE_FILE,
{},
)

if not isinstance(
    cache,
    dict,
):
    cache = {}

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
with _CACHE_LOCK:
save_json(
GEMINI_CACHE_FILE,
cache,
)

============================================================

CONTENT HASH

============================================================

def make_content_hash(value):
if isinstance(
value,
bytes,
):
raw = value
else:
raw = str(
value or ""
).encode(
"utf-8",
errors="replace",
)

return hashlib.sha256(
    raw
).hexdigest()

============================================================

REQUEST BUDGET

============================================================

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
    usage = int(
        meta.get(
            "requests_today",
            0,
        )
    )
except (
    TypeError,
    ValueError,
):
    usage = 0

meta["requests_today"] = max(
    0,
    usage,
)

return meta["requests_today"]

def get_effective_limit():
limits = []

if GEMINI_DAILY_LIMIT > 0:
    limits.append(
        GEMINI_DAILY_LIMIT
    )

if GEMINI_MAX_REQUESTS > 0:
    limits.append(
        GEMINI_MAX_REQUESTS
    )

if not limits:
    return 0

return min(limits)

def reserve_request(cache):
"""
Atomic budget reservation.

Important:
    can_make_request() + register_request()
    ko separate calls nahi rakha gaya.
    Is function mein check + increment ek lock ke
    andar hota hai.
"""

with _CACHE_LOCK:
    usage = get_daily_usage(
        cache
    )

    limit = get_effective_limit()

    if limit <= 0:
        return False

    if usage >= limit:
        return False

    cache["meta"][
        "requests_today"
    ] = usage + 1

    cache["meta"][
        "last_request_at"
    ] = utc_now()

    save_json(
        GEMINI_CACHE_FILE,
        cache,
    )

    return True

def can_make_request(cache):
with _CACHE_LOCK:
usage = get_daily_usage(
cache
)

    limit = get_effective_limit()

    if limit <= 0:
        return False

    return usage < limit

============================================================

TEXT HELPERS

============================================================

def clean_text(value):
if not value:
return ""

value = re.sub(
    r"\s+",
    " ",
    str(value),
)

return value.strip()

============================================================

EVIDENCE COMPACTION

============================================================

def compact_evidence(result):
if not isinstance(
result,
dict,
):
return {
"domain": "",
"python_score": 0,
"signals": [],
"evidence": [],
}

domain = clean_text(
    result.get(
        "domain",
        "",
    )
)

python_score = result.get(
    "python_score",
    result.get(
        "score",
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
    if isinstance(
        item,
        dict,
    ):
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

    elif isinstance(
        item,
        str,
    ):
        text = clean_text(
            item
        )

        if text:
            compact_items.append(
                {
                    "category": "",
                    "keyword": "",
                    "text": text[:500],
                }
            )

    if (
        len(compact_items)
        >= GEMINI_MAX_EVIDENCE_ITEMS
    ):
        break

payload = {
    "domain": domain,
    "python_score": python_score,
    "signals": signals[:20],
    "evidence": compact_items,
}

def serialized_size():
    return len(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        )
    )

while (
    compact_items
    and serialized_size()
    > GEMINI_MAX_EVIDENCE_CHARS
):
    compact_items.pop()

return payload

============================================================

PROMPT

============================================================

def build_prompt(compact_data):
return f"""
You are the secondary classification engine for LD76 Domain Finder.

This is defensive web research and website classification.

The Python scanner has already filtered this website.
Use ONLY the supplied evidence.

Do not assume a keyword alone proves fraud.
Do not invent facts, payment methods, profit percentages,
investment plans, or website behavior.

Return ONLY valid JSON.
Do not use Markdown.
Do not add text outside the JSON.

Required schema:

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
2. Arrays must contain only evidence-supported items.
3. Never invent payment methods.
4. Never invent profit percentages.
5. Negative statements such as "not an investment" must be considered.
6. The word "investment" alone does not prove high risk.
7. High-risk classification should normally require multiple meaningful
   signals such as investment + profit/return + deposit/withdrawal,
   referral, or similar financial mechanics.
8. If evidence is insufficient, use "unclear".
9. This is not a legal determination.
10. Keep reason concise.

Python scanner data:

{json.dumps(
compact_data,
ensure_ascii=False,
indent=2,
)}
""".strip()

============================================================

GEMINI API CALL

============================================================

def call_gemini(prompt):
if not GEMINI_API_KEY:
return {
"success": False,
"error": "GEMINI_API_KEY is not configured.",
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

last_error = ""

for attempt in range(
    GEMINI_MAX_RETRIES + 1
):
    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=GEMINI_HTTP_TIMEOUT,
        )

    except requests.RequestException as exc:
        last_error = (
            f"Gemini request failed: {exc}"
        )

        if attempt < GEMINI_MAX_RETRIES:
            time.sleep(
                min(
                    5.0,
                    2.0 ** attempt,
                )
            )
            continue

        return {
            "success": False,
            "error": last_error,
        }

    if response.status_code == 200:
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

    last_error = (
        f"Gemini HTTP {response.status_code}: "
        f"{response.text[:500]}"
    )

    # Retry only transient errors.
    if response.status_code in {
        429,
        500,
        502,
        503,
        504,
    } and attempt < GEMINI_MAX_RETRIES:
        time.sleep(
            min(
                10.0,
                2.0 ** attempt,
            )
        )
        continue

    return {
        "success": False,
        "error": last_error,
    }

return {
    "success": False,
    "error": last_error or "Unknown Gemini error.",
}

============================================================

RESPONSE PARSING

============================================================

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
        if not isinstance(
            part,
            dict,
        ):
            continue

        text = part.get(
            "text",
            "",
        )

        if text:
            texts.append(
                str(text)
            )

    return "\n".join(
        texts
    ).strip()

except (
    AttributeError,
    TypeError,
    IndexError,
):
    return ""

def parse_json_response(text):
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
    parsed = json.loads(
        text
    )

    if isinstance(
        parsed,
        dict,
    ):
        return parsed

except json.JSONDecodeError:
    pass

return None

============================================================

RESULT NORMALIZATION

============================================================

def normalize_result(result):
if not isinstance(
result,
dict,
):
return None

allowed_classifications = {
    "high_risk_investment",
    "investment_related",
    "payment_or_finance",
    "unclear",
    "not_relevant",
}

classification = clean_text(
    result.get(
        "classification",
        "unclear",
    )
)

if (
    classification
    not in allowed_classifications
):
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
        item = clean_text(
            item
        )

        if item:
            cleaned.append(
                item
            )

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

reason = clean_text(
    result.get(
        "reason",
        "",
    )
)[:1000]

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
    "reason": reason,
}

============================================================

MAIN ANALYSIS

============================================================

def analyze_candidate(
scanner_result,
*,
force=False,
):
if not isinstance(
scanner_result,
dict,
):
return {
"success": False,
"status": "invalid_candidate",
"domain": "",
}

domain = clean_text(
    scanner_result.get(
        "domain",
        "",
    )
)

if not domain:
    return {
        "success": False,
        "status": "missing_domain",
        "domain": "",
    }

compact_data = compact_evidence(
    scanner_result
)

# Content hash evidence + scanner content hash.
source_hash = clean_text(
    scanner_result.get(
        "content_hash",
        "",
    )
)

if not source_hash:
    source_hash = make_content_hash(
        json.dumps(
            compact_data,
            ensure_ascii=False,
            sort_keys=True,
        )
    )

# --------------------------------------------------------
# CACHE CHECK
# --------------------------------------------------------

with _CACHE_LOCK:
    cache = load_cache()

    cached = cache.get(
        "analyses",
        {}
    ).get(
        source_hash
    )

    if (
        cached
        and not force
    ):
        return {
            "success": True,
            "status": "cache_hit",
            "domain": domain,
            "content_hash": source_hash,
            "analysis": cached.get(
                "analysis"
            ),
        }

# --------------------------------------------------------
# API KEY CHECK
# --------------------------------------------------------

if not GEMINI_API_KEY:
    return {
        "success": False,
        "status": "missing_api_key",
        "domain": domain,
        "content_hash": source_hash,
    }

# --------------------------------------------------------
# ATOMIC REQUEST RESERVATION
# --------------------------------------------------------

with _CACHE_LOCK:
    cache = load_cache()

    if not reserve_request(
        cache
    ):
        return {
            "success": False,
            "status": "budget_exhausted",
            "domain": domain,
            "content_hash": source_hash,
        }

# --------------------------------------------------------
# REQUEST DELAY
# --------------------------------------------------------

if GEMINI_REQUEST_DELAY > 0:
    time.sleep(
        GEMINI_REQUEST_DELAY
    )

# --------------------------------------------------------
# API CALL
# --------------------------------------------------------

prompt = build_prompt(
    compact_data
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
        "content_hash": source_hash,
        "error": api_result.get(
            "error",
            "Unknown Gemini error.",
        ),
    }

# --------------------------------------------------------
# PARSE
# --------------------------------------------------------

response_text = extract_text_from_response(
    api_result.get(
        "data",
        {},
    )
)

parsed = parse_json_response(
    response_text
)

normalized = normalize_result(
    parsed
)

if normalized is None:
    return {
        "success": False,
        "status": "invalid_model_response",
        "domain": domain,
        "content_hash": source_hash,
    }

# --------------------------------------------------------
# CACHE SUCCESSFUL ANALYSIS
# --------------------------------------------------------

cache_entry = {
    "domain": domain,
    "content_hash": source_hash,
    "analyzed_at": utc_now(),
    "model": GEMINI_MODEL,
    "analysis": normalized,
}

with _CACHE_LOCK:
    cache = load_cache()

    cache.setdefault(
        "analyses",
        {},
    )[source_hash] = cache_entry

    save_cache(
        cache
    )

return {
    "success": True,
    "status": "analyzed",
    "domain": domain,
    "content_hash": source_hash,
    "analysis": normalized,
}

============================================================

STATUS

============================================================

def get_gemini_status():
with _CACHE_LOCK:
cache = load_cache()
usage = get_daily_usage(
cache
)

    limit = get_effective_limit()

    return {
        "configured": bool(
            GEMINI_API_KEY
        ),
        "model": GEMINI_MODEL,
        "requests_today": usage,
        "request_limit": limit,
        "remaining": max(
            0,
            limit - usage,
        ),
        "cache_entries": len(
            cache.get(
                "analyses",
                {},
            )
        ),
    }

============================================================

STANDALONE TEST

============================================================

if name == "main":
status = get_gemini_status()

print(
    "LD76 Gemini Analyzer"
)
print(
    "--------------------"
)
print(
    "Configured:",
    status["configured"],
)
print(
    "Model:",
    status["model"],
)
print(
    "Requests today:",
    status["requests_today"],
)
print(
    "Request limit:",
    status["request_limit"],
)
print(
    "Remaining:",
    status["remaining"],
)
print(
    "Cache entries:",
    status["cache_entries"],
)
