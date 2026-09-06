"""
LD76 Domain Finder
Main Scanner Engine - Phase 2 Gemini Integration

Pipeline:

    Domain Discovery
        ↓
    Normalize / Deduplicate
        ↓
    HTTP Check
        ↓
    HTML/Text Extraction
        ↓
    Python Signal Detection
        ↓
    Python Scoring
        ↓
    Strong Candidates
        ↓
    Gemini Queue
        ↓
    Gemini Classification
        ↓
    Results + History

Important:
    Gemini ko har domain nahi bhejna.
    Python maximum filtering karega.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# CONFIGURATION
# ============================================================

DOMAIN_TLD = os.getenv(
    "DOMAIN_TLD",
    "top",
).strip().lower()

DISCOVERY_LIMIT = int(
    os.getenv(
        "DISCOVERY_LIMIT",
        "200",
    )
)

REQUEST_TIMEOUT = int(
    os.getenv(
        "REQUEST_TIMEOUT",
        "8",
    )
)

CRTSH_TIMEOUT = int(
    os.getenv(
        "CRTSH_TIMEOUT",
        "30",
    )
)

MAX_RESPONSE_BYTES = int(
    os.getenv(
        "MAX_RESPONSE_BYTES",
        "2097152",
    )
)

PYTHON_MIN_SCORE = int(
    os.getenv(
        "PYTHON_MIN_SCORE",
        "60",
    )
)

PYTHON_RESULT_SCORE = int(
    os.getenv(
        "PYTHON_RESULT_SCORE",
        "80",
    )
)

SCAN_DELAY = float(
    os.getenv(
        "SCAN_DELAY",
        "0.25",
    )
)

SCANNER_USER_AGENT = os.getenv(
    "SCANNER_USER_AGENT",
    "LD76-Domain-Finder/1.0 (+domain-security-research)",
)

ENABLE_GEMINI = os.getenv(
    "ENABLE_GEMINI",
    "true",
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

GEMINI_FORCE_REANALYSIS = os.getenv(
    "GEMINI_FORCE_REANALYSIS",
    "false",
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

RESULTS_FILE = os.getenv(
    "RESULTS_FILE",
    "data/results.json",
)

HISTORY_FILE = os.getenv(
    "HISTORY_FILE",
    "data/scan_history.json",
)


# ============================================================
# SIGNAL MATRIX
# ============================================================

SIGNAL_GROUPS = {
    "investment": {
        "weight": 30,
        "keywords": [
            "investment plan",
            "investment package",
            "invest now",
            "invest today",
            "investment",
            "invest",
            "investing",
            "capital plan",
            "fund plan",
        ],
    },

    "profit": {
        "weight": 30,
        "keywords": [
            "daily profit",
            "daily return",
            "daily income",
            "daily earning",
            "guaranteed profit",
            "guaranteed return",
            "fixed profit",
            "fixed return",
            "high return",
            "high profit",
            "profit rate",
            "return on investment",
            "roi",
            "passive income",
            "earn daily",
            "earn every day",
        ],
    },

    "deposit": {
        "weight": 20,
        "keywords": [
            "deposit",
            "min deposit",
            "minimum deposit",
            "make a deposit",
            "fund your account",
            "recharge account",
            "recharge",
            "add funds",
            "top up",
            "top-up",
        ],
    },

    "withdrawal": {
        "weight": 20,
        "keywords": [
            "withdraw",
            "withdrawal",
            "withdraw money",
            "withdraw funds",
            "cash out",
            "payout",
            "minimum withdrawal",
            "withdraw profit",
        ],
    },

    "referral": {
        "weight": 20,
        "keywords": [
            "referral commission",
            "referral bonus",
            "referral reward",
            "invite friends",
            "invite your friends",
            "refer and earn",
            "team commission",
            "team bonus",
            "network commission",
            "affiliate commission",
            "level commission",
            "direct bonus",
            "indirect bonus",
        ],
    },

    "crypto": {
        "weight": 15,
        "keywords": [
            "usdt",
            "usdc",
            "bitcoin",
            "btc",
            "ethereum",
            "eth",
            "tron",
            "trx",
            "bnb",
            "binance",
            "crypto payment",
            "cryptocurrency",
            "wallet address",
        ],
    },

    "pk_payment": {
        "weight": 20,
        "keywords": [
            "easypaisa",
            "easy paisa",
            "jazzcash",
            "jazz cash",
            "nayapay",
            "naya pay",
            "sadapay",
            "sada pay",
            "raast",
            "mobicash",
            "hbl",
            "ubl",
            "alfalah",
            "meezan bank",
            "pkr",
            "rs.",
            "rs ",
        ],
    },

    "vip": {
        "weight": 15,
        "keywords": [
            "vip 1",
            "vip 2",
            "vip 3",
            "vip level",
            "vip membership",
            "vip package",
            "premium plan",
            "level 1",
            "level 2",
            "level 3",
        ],
    },

    "communication": {
        "weight": 10,
        "keywords": [
            "chat.whatsapp.com",
            "wa.me/",
            "t.me/",
            "telegram",
            "whatsapp",
            "join our group",
            "contact support",
            "customer support",
        ],
    },
}


# ============================================================
# COMBINATION BONUSES
# ============================================================

COMBINATION_BONUSES = [
    (
        {"investment", "profit"},
        20,
        "investment + profit",
    ),

    (
        {"investment", "deposit"},
        15,
        "investment + deposit",
    ),

    (
        {"investment", "withdrawal"},
        15,
        "investment + withdrawal",
    ),

    (
        {"deposit", "withdrawal"},
        15,
        "deposit + withdrawal",
    ),

    (
        {"profit", "deposit"},
        15,
        "profit + deposit",
    ),

    (
        {"profit", "withdrawal"},
        15,
        "profit + withdrawal",
    ),

    (
        {"investment", "referral"},
        15,
        "investment + referral",
    ),

    (
        {"deposit", "referral"},
        10,
        "deposit + referral",
    ),

    (
        {"profit", "referral"},
        10,
        "profit + referral",
    ),
]


# ============================================================
# NEGATIVE / FALSE-POSITIVE PATTERNS
# ============================================================

NEGATIVE_PATTERNS = [
    r"\bnot an investment\b",
    r"\bnot investment advice\b",
    r"\bdo not invest\b",
    r"\bdon't invest\b",
    r"\bnever invest\b",
    r"\bno investment required\b",
    r"\bnot a financial product\b",
    r"\bnot financial advice\b",
    r"\bfor educational purposes only\b",
    r"\bexample investment\b",
]


# ============================================================
# SESSION
# ============================================================

def create_session():
    session = requests.Session()

    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.5,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=[
            "GET",
        ],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=20,
        pool_maxsize=20,
    )

    session.mount(
        "https://",
        adapter,
    )

    session.mount(
        "http://",
        adapter,
    )

    session.headers.update(
        {
            "User-Agent": SCANNER_USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
        }
    )

    return session


# ============================================================
# TIME / HASH HELPERS
# ============================================================

def utc_now():
    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


def make_hash(value):
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


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(
    path,
    default,
):
    if not os.path.exists(
        path
    ):
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


def save_json(
    path,
    data,
):
    directory = os.path.dirname(
        path
    )

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    temporary = (
        path + ".tmp"
    )

    with open(
        temporary,
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
        temporary,
        path,
    )


# ============================================================
# DOMAIN NORMALIZATION
# ============================================================

def normalize_domain(
    value,
):
    if not value:
        return ""

    value = str(
        value
    ).strip().lower()

    value = value.replace(
        "*.",
        "",
    )

    value = value.split(
        "/"
    )[0]

    value = value.split(
        ":"
    )[0]

    value = value.strip(
        "."
    )

    if (
        not value
        or " " in value
    ):
        return ""

    if not re.match(
        r"^[a-z0-9.-]+$",
        value,
    ):
        return ""

    if not value.endswith(
        "." + DOMAIN_TLD
    ):
        return ""

    return value


# ============================================================
# DOMAIN DISCOVERY
# ============================================================

def get_recent_domains(
    tld=None,
):
    """
    crt.sh se certificate transparency records leta hai.

    Important:
        Last 100 raw rows ko simply "new domains" nahi mana jata.
        Certificate timestamp ko use karke candidates sort kiye jate hain.
    """

    tld = (
        tld
        or DOMAIN_TLD
    )

    print(
        f"[*] Fetching .{tld} domains from crt.sh..."
    )

    url = (
        "https://crt.sh/"
        f"?q=%.{tld}"
        "&output=json"
    )

    try:
        response = requests.get(
            url,
            timeout=CRTSH_TIMEOUT,
            headers={
                "User-Agent": SCANNER_USER_AGENT,
            },
        )

        if response.status_code != 200:
            print(
                "[!] crt.sh HTTP",
                response.status_code,
            )
            return []

        data = response.json()

    except Exception as exc:
        print(
            "[!] crt.sh error:",
            exc,
        )
        return []

    discovered = {}

    for item in data:
        if not isinstance(
            item,
            dict,
        ):
            continue

        timestamp = (
            item.get(
                "entry_timestamp"
            )
            or item.get(
                "not_before"
            )
            or ""
        )

        names = str(
            item.get(
                "name_value",
                "",
            )
        )

        for raw_name in names.split(
            "\n"
        ):
            domain = normalize_domain(
                raw_name
            )

            if not domain:
                continue

            current = discovered.get(
                domain
            )

            if (
                current is None
                or str(timestamp)
                > str(
                    current
                )
            ):
                discovered[
                    domain
                ] = timestamp

    ordered = sorted(
        discovered.items(),
        key=lambda item: str(
            item[1]
        ),
        reverse=True,
    )

    domains = [
        domain
        for domain, _ in ordered[
            :DISCOVERY_LIMIT
        ]
    ]

    return domains


# ============================================================
# HTTP FETCH
# ============================================================

def fetch_site(
    session,
    domain,
):
    """
    HTTPS first, HTTP fallback.
    """

    urls = [
        f"https://{domain}",
        f"http://{domain}",
    ]

    for url in urls:
        try:
            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                stream=True,
            )

        except requests.RequestException:
            continue

        if response.status_code < 200:
            response.close()
            continue

        if response.status_code >= 400:
            response.close()
            continue

        content_type = (
            response.headers.get(
                "Content-Type",
                "",
            ).lower()
        )

        if content_type:
            allowed = (
                "text/html",
                "application/xhtml+xml",
                "text/plain",
            )

            if not any(
                item in content_type
                for item in allowed
            ):
                response.close()
                continue

        try:
            chunks = []
            total = 0

            for chunk in response.iter_content(
                chunk_size=65536
            ):
                if not chunk:
                    continue

                remaining = (
                    MAX_RESPONSE_BYTES
                    - total
                )

                if remaining <= 0:
                    break

                chunk = chunk[
                    :remaining
                ]

                chunks.append(
                    chunk
                )

                total += len(
                    chunk
                )

                if total >= MAX_RESPONSE_BYTES:
                    break

            content = b"".join(
                chunks
            )

        except requests.RequestException:
            response.close()
            continue

        finally:
            response.close()

        if not content:
            continue

        encoding = (
            response.encoding
            or "utf-8"
        )

        try:
            html = content.decode(
                encoding,
                errors="replace",
            )
        except (
            LookupError,
        ):
            html = content.decode(
                "utf-8",
                errors="replace",
            )

        return {
            "url": response.url,
            "status_code": response.status_code,
            "content_type": content_type,
            "html": html,
        }

    return None


# ============================================================
# TEXT EXTRACTION
# ============================================================

def clean_text(
    value,
):
    if not value:
        return ""

    value = re.sub(
        r"\s+",
        " ",
        str(value),
    )

    return value.strip()


def extract_site_content(
    html,
):
    """
    Important content areas ko priority ke saath extract karta hai.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "template",
        ]
    ):
        tag.decompose()

    title = clean_text(
        soup.title.get_text(
            " ",
            strip=True,
        )
        if soup.title
        else ""
    )

    meta_description = ""

    meta = soup.find(
        "meta",
        attrs={
            "name": re.compile(
                r"^description$",
                re.IGNORECASE,
            )
        },
    )

    if meta:
        meta_description = clean_text(
            meta.get(
                "content",
                "",
            )
        )

    headings = []

    for tag in soup.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
        ]
    ):
        text = clean_text(
            tag.get_text(
                " ",
                strip=True,
            )
        )

        if text:
            headings.append(
                text
            )

    buttons = []

    for tag in soup.find_all(
        [
            "button",
            "a",
            "input",
        ]
    ):
        text = clean_text(
            tag.get(
                "value",
                "",
            )
            or tag.get_text(
                " ",
                strip=True,
            )
        )

        if text:
            buttons.append(
                text
            )

    forms = []

    for form in soup.find_all(
        "form"
    ):
        text = clean_text(
            form.get_text(
                " ",
                strip=True,
            )
        )

        if text:
            forms.append(
                text
            )

    body = clean_text(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    # Limit individual sections to keep memory/payload sane.
    title = title[:1000]
    meta_description = meta_description[:2000]

    headings = headings[
        :50
    ]

    buttons = buttons[
        :100
    ]

    forms = forms[
        :50
    ]

    body = body[
        :30000
    ]

    combined = "\n".join(
        [
            title,
            meta_description,
            "\n".join(
                headings
            ),
            "\n".join(
                buttons
            ),
            "\n".join(
                forms
            ),
            body,
        ]
    )

    return {
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "buttons": buttons,
        "forms": forms,
        "body": body,
        "combined_text": combined,
    }


# ============================================================
# NEGATIVE CONTEXT
# ============================================================

def is_negative_context(
    text,
    keyword,
):
    """
    Keyword ke around negative phrase check karta hai.

    Example:
        "This is NOT an investment platform."

    Isay direct investment signal nahi banana.
    """

    text = str(
        text or ""
    ).lower()

    keyword = str(
        keyword or ""
    ).lower()

    position = text.find(
        keyword
    )

    if position < 0:
        return False

    start = max(
        0,
        position - 180,
    )

    end = min(
        len(text),
        position + len(keyword) + 180,
    )

    context = text[
        start:end
    ]

    for pattern in NEGATIVE_PATTERNS:
        if re.search(
            pattern,
            context,
            flags=re.IGNORECASE,
        ):
            return True

    return False


# ============================================================
# SIGNAL MATCHING
# ============================================================

def find_signal_matches(
    extracted,
):
    """
    Har signal group ke keywords ko scan karta hai.

    Returns:
        signal names
        matched keywords
        evidence snippets
    """

    sections = [
        (
            "title",
            extracted.get(
                "title",
                "",
            ),
        ),
        (
            "meta_description",
            extracted.get(
                "meta_description",
                "",
            ),
        ),
        (
            "headings",
            "\n".join(
                extracted.get(
                    "headings",
                    [],
                )
            ),
        ),
        (
            "buttons",
            "\n".join(
                extracted.get(
                    "buttons",
                    [],
                )
            ),
        ),
        (
            "forms",
            "\n".join(
                extracted.get(
                    "forms",
                    [],
                )
            ),
        ),
        (
            "body",
            extracted.get(
                "body",
                "",
            ),
        ),
    ]

    signal_names = set()
    matched_keywords = []
    evidence = []
    seen_keyword = set()

    for category, config in SIGNAL_GROUPS.items():
        keywords = config.get(
            "keywords",
            [],
        )

        for keyword in keywords:
            keyword_lower = keyword.lower()

            matched = False
            matched_section = ""
            matched_text = ""

            for section_name, section_text in sections:
                section_text = str(
                    section_text or ""
                )

                if keyword_lower not in section_text.lower():
                    continue

                if is_negative_context(
                    section_text,
                    keyword_lower,
                ):
                    continue

                matched = True
                matched_section = section_name

                pos = section_text.lower().find(
                    keyword_lower
                )

                start = max(
                    0,
                    pos - 100,
                )

                end = min(
                    len(section_text),
                    pos + len(keyword) + 180,
                )

                matched_text = clean_text(
                    section_text[
                        start:end
                    ]
                )

                break

            if not matched:
                continue

            signal_names.add(
                category
            )

            if keyword_lower not in seen_keyword:
                seen_keyword.add(
                    keyword_lower
                )

                matched_keywords.append(
                    {
                        "category": category,
                        "keyword": keyword,
                    }
                )

                evidence.append(
                    {
                        "category": category,
                        "keyword": keyword,
                        "section": matched_section,
                        "text": matched_text[
                            :500
                        ],
                    }
                )

    return (
        signal_names,
        matched_keywords,
        evidence,
    )


# ============================================================
# PYTHON SCORING
# ============================================================

def calculate_score(
    signal_names,
):
    score = 0
    score_breakdown = {}

    for signal in signal_names:
        weight = SIGNAL_GROUPS.get(
            signal,
            {},
        ).get(
            "weight",
            0,
        )

        score += weight

        score_breakdown[
            signal
        ] = weight

    combination_matches = []

    for required, bonus, label in COMBINATION_BONUSES:
        if required.issubset(
            signal_names
        ):
            score += bonus

            combination_matches.append(
                {
                    "signals": sorted(
                        required
                    ),
                    "bonus": bonus,
                    "reason": label,
                }
            )

    score = min(
        score,
        200,
    )

    return (
        score,
        score_breakdown,
        combination_matches,
    )


def classify_python_score(
    score,
):
    if score >= 130:
        return "very_strong"

    if score >= PYTHON_RESULT_SCORE:
        return "strong"

    if score >= PYTHON_MIN_SCORE:
        return "candidate"

    return "weak"


# ============================================================
# SINGLE DOMAIN ANALYSIS
# ============================================================

def analyze_site(
    session,
    domain,
):
    """
    Ek domain ko Python scanner se analyze karta hai.
    """

    fetched = fetch_site(
        session,
        domain,
    )

    if not fetched:
        return {
            "domain": domain,
            "status": "inactive_or_unreachable",
            "scanned_at": utc_now(),
        }

    html = fetched.get(
        "html",
        "",
    )

    extracted = extract_site_content(
        html
    )

    (
        signals,
        matched_keywords,
        evidence,
    ) = find_signal_matches(
        extracted
    )

    (
        score,
        score_breakdown,
        combination_matches,
    ) = calculate_score(
        signals
    )

    content_hash = make_hash(
        html
    )

    classification = classify_python_score(
        score
    )

    result = {
        "domain": domain,
        "url": fetched.get(
            "url",
            "",
        ),
        "http_status": fetched.get(
            "status_code"
        ),
        "content_type": fetched.get(
            "content_type",
            "",
        ),
        "status": "active",
        "python_score": score,
        "score": score,
        "python_classification": classification,
        "signals": sorted(
            signals
        ),
        "matched_keywords": matched_keywords[
            :100
        ],
        "score_breakdown": score_breakdown,
        "combination_bonuses": combination_matches,
        "evidence": evidence[
            :100
        ],
        "content_hash": content_hash,
        "content_length": len(
            html.encode(
                "utf-8",
                errors="replace",
            )
        ),
        "title": extracted.get(
            "title",
            "",
        ),
        "scanned_at": utc_now(),
        "gemini_analyzed": False,
    }

    return result


# ============================================================
# HISTORY
# ============================================================

def load_history():
    history = load_json(
        HISTORY_FILE,
        {},
    )

    if not isinstance(
        history,
        dict,
    ):
        history = {}

    if not isinstance(
        history.get(
            "domains"
        ),
        dict,
    ):
        history["domains"] = {}

    return history


def update_history(
    history,
    result,
):
    domain = result.get(
        "domain",
        "",
    )

    if not domain:
        return

    domains = history.setdefault(
        "domains",
        {},
    )

    previous = domains.get(
        domain,
        {},
    )

    if not isinstance(
        previous,
        dict,
    ):
        previous = {}

    content_hash = result.get(
        "content_hash",
        "",
    )

    previous_hash = previous.get(
        "content_hash",
        "",
    )

    if content_hash:
        previous[
            "content_hash"
        ] = content_hash

    previous[
        "domain"
    ] = domain

    if not previous.get(
        "first_seen"
    ):
        previous[
            "first_seen"
        ] = result.get(
            "scanned_at",
            utc_now(),
        )

    previous[
        "last_seen"
    ] = result.get(
        "scanned_at",
        utc_now(),
    )

    previous[
        "last_scan"
    ] = result.get(
        "scanned_at",
        utc_now(),
    )

    previous[
        "python_score"
    ] = result.get(
        "python_score",
        0,
    )

    previous[
        "gemini_score"
    ] = result.get(
        "gemini",
        {},
    ).get(
        "confidence",
        previous.get(
            "gemini_score",
            0,
        ),
    ) if isinstance(
        result.get(
            "gemini"
        ),
        dict,
    ) else previous.get(
        "gemini_score",
        0,
    )

    previous[
        "gemini_analyzed"
    ] = bool(
        result.get(
            "gemini_analyzed",
            previous.get(
                "gemini_analyzed",
                False,
            ),
        )
    )

    previous[
        "content_changed"
    ] = bool(
        previous_hash
        and content_hash
        and previous_hash != content_hash
    )

    domains[
        domain
    ] = previous


# ============================================================
# RESULTS MERGING
# ============================================================

def load_existing_results():
    data = load_json(
        RESULTS_FILE,
        [],
    )

    if isinstance(
        data,
        list,
    ):
        return data

    if isinstance(
        data,
        dict,
    ):
        # Backward compatibility if old results were stored
        # as a dictionary.
        return list(
            data.values()
        )

    return []


def merge_results(
    existing,
    current,
):
    by_domain = {}

    for item in existing:
        if not isinstance(
            item,
            dict,
        ):
            continue

        domain = normalize_domain(
            item.get(
                "domain",
                "",
            )
        )

        if domain:
            by_domain[
                domain
            ] = item

    for item in current:
        if not isinstance(
            item,
            dict,
        ):
            continue

        domain = normalize_domain(
            item.get(
                "domain",
                "",
            )
        )

        if not domain:
            continue

        previous = by_domain.get(
            domain,
            {},
        )

        if not isinstance(
            previous,
            dict,
        ):
            previous = {}

        merged = dict(
            previous
        )

        merged.update(
            item
        )

        by_domain[
            domain
        ] = merged

    return sorted(
        by_domain.values(),
        key=lambda item: (
            int(
                item.get(
                    "python_score",
                    item.get(
                        "score",
                        0,
                    ),
                )
                or 0
            ),
            str(
                item.get(
                    "scanned_at",
                    "",
                )
            ),
        ),
        reverse=True,
    )


# ============================================================
# GEMINI INTEGRATION
# ============================================================

def run_gemini_analysis(
    current_results,
):
    """
    Gemini queue ko optional rakha gaya hai.

    Agar Gemini disabled ya key missing ho to Python scan
    successfully continue karta hai.
    """

    if not ENABLE_GEMINI:
        print(
            "[Gemini] Disabled by configuration."
        )

        return current_results

    try:
        from gemini_queue import (
            run_gemini_queue,
            merge_gemini_results,
            print_queue_summary,
        )
    except ImportError:
        try:
            from scanner.gemini_queue import (
                run_gemini_queue,
                merge_gemini_results,
                print_queue_summary,
            )
        except ImportError as exc:
            print(
                "[Gemini] Queue import failed:",
                exc,
            )
            return current_results

    try:
        queue_result = run_gemini_queue(
            current_results,
            force=GEMINI_FORCE_REANALYSIS,
        )

        print_queue_summary(
            queue_result
        )

        gemini_results = queue_result.get(
            "results",
            [],
        )

        return merge_gemini_results(
            current_results,
            gemini_results,
        )

    except Exception as exc:
        print(
            "[Gemini] Integration error:",
            exc,
        )

        # Gemini failure must never destroy Python results.
        return current_results


# ============================================================
# MAIN
# ============================================================

def main():
    started_at = utc_now()

    print(
        "=========================================="
    )

    print(
        "LD76 Domain Finder"
    )

    print(
        "Python + Gemini Scanner"
    )

    print(
        "=========================================="
    )

    print(
        "[Config]"
    )

    print(
        "  TLD:",
        DOMAIN_TLD,
    )

    print(
        "  Discovery limit:",
        DISCOVERY_LIMIT,
    )

    print(
        "  Python Gemini threshold:",
        PYTHON_MIN_SCORE,
    )

    print(
        "  Python result threshold:",
        PYTHON_RESULT_SCORE,
    )

    print(
        "  Gemini enabled:",
        ENABLE_GEMINI,
    )

    session = create_session()

    domains = get_recent_domains(
        DOMAIN_TLD
    )

    print(
        f"[*] Discovered {len(domains)} domains."
    )

    current_results = []

    for index, domain in enumerate(
        domains,
        start=1,
    ):
        print(
            f"[{index}/{len(domains)}] Scanning {domain}"
        )

        try:
            result = analyze_site(
                session,
                domain,
            )

            current_results.append(
                result
            )

            if result.get(
                "status"
            ) == "active":
                score = result.get(
                    "python_score",
                    0,
                )

                if score >= PYTHON_MIN_SCORE:
                    print(
                        f"  [Python candidate] "
                        f"{domain} -> score={score}"
                    )

                if score >= PYTHON_RESULT_SCORE:
                    print(
                        f"  [STRONG] "
                        f"{domain} -> score={score}"
                    )

        except Exception as exc:
            print(
                f"  [!] Domain error: {exc}"
            )

            current_results.append(
                {
                    "domain": domain,
                    "status": "scan_error",
                    "error": str(exc),
                    "scanned_at": utc_now(),
                }
            )

        if SCAN_DELAY > 0:
            time.sleep(
                SCAN_DELAY
            )

    # --------------------------------------------------------
    # Keep only strong Python results for permanent result set.
    # History still receives all scanned domains.
    # --------------------------------------------------------

    strong_results = [
        result
        for result in current_results
        if isinstance(
            result,
            dict,
        )
        and result.get(
            "python_score",
            result.get(
                "score",
                0,
            ),
        ) >= PYTHON_RESULT_SCORE
    ]

    print(
        f"[*] Python strong candidates: "
        f"{len(strong_results)}"
    )

    # --------------------------------------------------------
    # Gemini only sees strong candidates.
    # --------------------------------------------------------

    analyzed_results = run_gemini_analysis(
        strong_results
    )

    # --------------------------------------------------------
    # Merge Gemini results into permanent results.
    # --------------------------------------------------------

    existing_results = load_existing_results()

    final_results = merge_results(
        existing_results,
        analyzed_results,
    )

    os.makedirs(
        "data",
        exist_ok=True,
    )

    save_json(
        RESULTS_FILE,
        final_results,
    )

    # --------------------------------------------------------
    # History
    # --------------------------------------------------------

    history = load_history()

    for result in current_results:
        update_history(
            history,
            result,
        )

    history[
        "last_scan_started_at"
    ] = started_at

    history[
        "last_scan_finished_at"
    ] = utc_now()

    history[
        "last_scan_domains"
    ] = len(
        domains
    )

    history[
        "last_scan_strong_candidates"
    ] = len(
        strong_results
    )

    history[
        "last_scan_gemini_enabled"
    ] = ENABLE_GEMINI

    save_json(
        HISTORY_FILE,
        history,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    active = sum(
        1
        for result in current_results
        if result.get(
            "status"
        ) == "active"
    )

    print(
        "=========================================="
    )

    print(
        "Scan complete"
    )

    print(
        "  Domains discovered:",
        len(domains),
    )

    print(
        "  Active sites:",
        active,
    )

    print(
        "  Strong Python candidates:",
        len(strong_results),
    )

    print(
        "  Saved results:",
        len(final_results),
    )

    print(
        "=========================================="
    )


if __name__ == "__main__":
    main()
