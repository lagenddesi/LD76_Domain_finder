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
# LD76 DOMAIN FINDER
# Phase 1 - Python Scanner Engine
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

RESULTS_FILE = os.path.join(DATA_DIR, "results.json")
HISTORY_FILE = os.path.join(DATA_DIR, "scan_history.json")

TLD = os.getenv("DOMAIN_TLD", "top")

DISCOVERY_LIMIT = int(os.getenv("DISCOVERY_LIMIT", "200"))

REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "8"))
MAX_RESPONSE_BYTES = int(
    os.getenv("MAX_RESPONSE_BYTES", str(2 * 1024 * 1024))
)

CRTSH_TIMEOUT = float(os.getenv("CRTSH_TIMEOUT", "30"))

MIN_SCORE = int(os.getenv("PYTHON_MIN_SCORE", "60"))
RESULT_SCORE = int(os.getenv("PYTHON_RESULT_SCORE", "80"))

SCAN_DELAY = float(os.getenv("SCAN_DELAY", "0.25"))

USER_AGENT = os.getenv(
    "SCANNER_USER_AGENT",
    "LD76-Domain-Finder/1.0 (+domain-security-research)"
)


# ============================================================
# SIGNAL MATRIX
# ============================================================

SIGNALS = {
    "investment": {
        "weight": 20,
        "keywords": [
            "investment",
            "invest",
            "investment plan",
            "investment package",
            "investment program",
            "invest plan",
            "deposit plan",
            "capital",
            "roi",
        ],
    },

    "profit": {
        "weight": 25,
        "keywords": [
            "daily profit",
            "daily return",
            "daily income",
            "daily earning",
            "weekly profit",
            "weekly return",
            "monthly profit",
            "monthly return",
            "guaranteed profit",
            "guaranteed return",
            "fixed return",
            "high return",
            "passive income",
            "profit plan",
        ],
    },

    "deposit": {
        "weight": 15,
        "keywords": [
            "deposit",
            "minimum deposit",
            "min deposit",
            "make deposit",
            "deposit now",
            "fund account",
            "add money",
            "recharge",
        ],
    },

    "withdrawal": {
        "weight": 15,
        "keywords": [
            "withdraw",
            "withdrawal",
            "cash out",
            "minimum withdrawal",
            "min withdrawal",
            "withdraw funds",
            "withdraw money",
        ],
    },

    "referral": {
        "weight": 10,
        "keywords": [
            "referral",
            "referral commission",
            "team commission",
            "invite friends",
            "invite friend",
            "affiliate",
            "affiliate commission",
            "level income",
            "team income",
            "referral bonus",
        ],
    },

    "crypto": {
        "weight": 10,
        "keywords": [
            "usdt",
            "trc20",
            "bep20",
            "erc20",
            "bitcoin",
            "btc",
            "ethereum",
            "eth",
            "crypto",
            "cryptocurrency",
            "wallet address",
        ],
    },

    "pk_payment": {
        "weight": 10,
        "keywords": [
            "easypaisa",
            "easy paisa",
            "jazzcash",
            "jazz cash",
            "nayapay",
            "sadapay",
            "raast",
            "mobicash",
            "meezan bank",
            "hbl",
            "ubl",
            "bank alfalah",
            "alfalah",
            "pkr",
            "rs.",
            "rupees",
        ],
    },

    "vip": {
        "weight": 15,
        "keywords": [
            "vip plan",
            "vip investment",
            "vip level",
            "vip package",
            "premium plan",
            "premium investment",
        ],
    },

    "communication": {
        "weight": 5,
        "keywords": [
            "telegram",
            "whatsapp",
            "support group",
            "telegram group",
            "telegram channel",
            "whatsapp group",
        ],
    },
}


# Strong combinations receive additional points.
COMBINATION_BONUSES = [
    (
        {"investment", "profit"},
        15,
        "investment + profit combination",
    ),
    (
        {"investment", "deposit"},
        10,
        "investment + deposit combination",
    ),
    (
        {"deposit", "withdrawal"},
        10,
        "deposit + withdrawal combination",
    ),
    (
        {"profit", "deposit", "withdrawal"},
        15,
        "profit + deposit + withdrawal combination",
    ),
    (
        {"investment", "profit", "deposit"},
        15,
        "investment + profit + deposit combination",
    ),
]


# Negative phrases reduce false positives.
NEGATIVE_PATTERNS = [
    "not an investment",
    "not an investment service",
    "not an investment company",
    "no investment required",
    "no investment services",
    "do not invest",
    "don't invest",
    "avoid investment",
    "investment scam warning",
    "investment scam alert",
    "beware of investment scams",
    "we do not offer investment",
    "we don't offer investment",
]


# ============================================================
# HTTP SESSION
# ============================================================

def build_session():
    """
    Controlled HTTP session.

    Retries sirf temporary/network-level failures ke liye.
    Infinite retry nahi hoti.
    """

    session = requests.Session()

    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=10,
        pool_maxsize=10,
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.8",
        }
    )

    return session


SESSION = build_session()


# ============================================================
# TIME / JSON HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    temporary_path = path + ".tmp"

    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    os.replace(temporary_path, path)


# ============================================================
# DOMAIN NORMALIZATION
# ============================================================

def normalize_domain(value):
    """
    Domain ko canonical form mein convert karta hai.

    Examples:
        *.example.top
        https://example.top/path
        EXAMPLE.TOP
    ->
        example.top
    """

    if not value:
        return None

    value = str(value).strip().lower()

    if not value:
        return None

    value = value.replace("\\r", "")
    value = value.replace("\\n", "")

    value = value.replace("*.", "")

    if "://" in value:
        try:
            value = urlparse(value).hostname or ""
        except Exception:
            return None

    value = value.split("/")[0]
    value = value.split("?")[0]
    value = value.split("#")[0]
    value = value.split(":")[0]

    value = value.strip(". ")

    if not value:
        return None

    # Basic hostname validation.
    if len(value) > 253:
        return None

    if not re.fullmatch(
        r"(?=.{1,253}$)"
        r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
        r"[a-z]{2,63}",
        value,
    ):
        return None

    if not value.endswith("." + TLD):
        return None

    return value


# ============================================================
# DOMAIN DISCOVERY
# ============================================================

def get_recent_domains(tld=TLD):
    """
    crt.sh se certificate transparency data fetch karta hai.

    Important:
    crt.sh ke latest array entries ko blindly "new domains"
    assume nahi karta. Returned certificates ke timestamps ko
    use karke records sort kiye jate hain.
    """

    print(f"[*] Discovering .{tld} domains from crt.sh...")

    url = f"https://crt.sh/?q=%25.{tld}&output=json"

    try:
        response = SESSION.get(
            url,
            timeout=CRTSH_TIMEOUT,
        )

        if response.status_code != 200:
            print(
                f"[!] crt.sh returned HTTP "
                f"{response.status_code}"
            )
            return []

        data = response.json()

        if not isinstance(data, list):
            print("[!] Unexpected crt.sh response format.")
            return []

    except requests.RequestException as exc:
        print(f"[!] crt.sh request failed: {exc}")
        return []

    except ValueError as exc:
        print(f"[!] crt.sh JSON parsing failed: {exc}")
        return []

    domain_dates = {}

    for item in data:
        if not isinstance(item, dict):
            continue

        name_value = item.get("name_value", "")

        timestamp = (
            item.get("entry_timestamp")
            or item.get("not_before")
            or ""
        )

        for raw_domain in str(name_value).splitlines():
            domain = normalize_domain(raw_domain)

            if not domain:
                continue

            previous = domain_dates.get(domain)

            if previous is None or str(timestamp) > str(previous):
                domain_dates[domain] = timestamp

    sorted_domains = sorted(
        domain_dates.items(),
        key=lambda item: str(item[1]),
        reverse=True,
    )

    domains = [
        domain
        for domain, _timestamp in sorted_domains[:DISCOVERY_LIMIT]
    ]

    print(f"[*] Unique normalized domains: {len(domain_dates)}")
    print(f"[*] Domains selected for scanning: {len(domains)}")

    return domains


# ============================================================
# HISTORY
# ============================================================

def load_history():
    history = load_json(HISTORY_FILE, {})

    if not isinstance(history, dict):
        return {}

    return history


def get_history_record(history, domain):
    record = history.get(domain)

    if isinstance(record, dict):
        return record

    return {}


def update_history(
    history,
    domain,
    *,
    scan_time,
    status,
    http_status=None,
    python_score=0,
    content_hash=None,
    error=None,
):
    existing = get_history_record(history, domain)

    first_seen = existing.get("first_seen") or scan_time

    history[domain] = {
        "domain": domain,
        "first_seen": first_seen,
        "last_seen": scan_time,
        "last_scan": scan_time,
        "status": status,
        "http_status": http_status,
        "python_score": python_score,
        "content_hash": content_hash,
        "error": error,
    }


# ============================================================
# WEBSITE FETCH
# ============================================================

def fetch_site(domain):
    """
    HTTPS first, HTTP fallback.

    Scanner kisi ek failed domain ki wajah se crash nahi hota.
    """

    urls = [
        f"https://{domain}",
        f"http://{domain}",
    ]

    last_error = None

    for url in urls:
        try:
            response = SESSION.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                stream=True,
            )

            status_code = response.status_code

            content_type = (
                response.headers.get("Content-Type", "")
                .lower()
            )

            if status_code >= 400:
                response.close()
                last_error = f"HTTP {status_code}"
                continue

            if content_type and not (
                "text/html" in content_type
                or "application/xhtml+xml" in content_type
            ):
                response.close()
                return {
                    "success": False,
                    "status": "non_html",
                    "http_status": status_code,
                    "url": response.url,
                    "error": f"Non-HTML content: {content_type}",
                }

            chunks = []
            total_bytes = 0

            for chunk in response.iter_content(
                chunk_size=16384,
                decode_unicode=False,
            ):
                if not chunk:
                    continue

                remaining = MAX_RESPONSE_BYTES - total_bytes

                if remaining <= 0:
                    break

                chunk = chunk[:remaining]

                chunks.append(chunk)
                total_bytes += len(chunk)

                if total_bytes >= MAX_RESPONSE_BYTES:
                    break

            response.close()

            raw_content = b"".join(chunks)

            encoding = response.encoding or "utf-8"

            try:
                html = raw_content.decode(
                    encoding,
                    errors="replace",
                )
            except LookupError:
                html = raw_content.decode(
                    "utf-8",
                    errors="replace",
                )

            return {
                "success": True,
                "status": "active",
                "http_status": status_code,
                "url": response.url,
                "content_type": content_type,
                "html": html,
                "bytes": total_bytes,
            }

        except requests.RequestException as exc:
            last_error = str(exc)

    return {
        "success": False,
        "status": "failed",
        "http_status": None,
        "url": None,
        "error": last_error or "Unknown request error",
    }


# ============================================================
# CONTENT EXTRACTION
# ============================================================

def clean_text(value):
    if not value:
        return ""

    value = re.sub(r"\s+", " ", str(value))
    return value.strip()


def unique_strings(values, max_items=50):
    result = []
    seen = set()

    for value in values:
        value = clean_text(value)

        if not value:
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

        if len(result) >= max_items:
            break

    return result


def extract_content(html):
    """
    Website se sirf relevant human-readable evidence extract karta hai.

    Raw HTML Gemini ko future mein nahi bhejna.
    """

    soup = BeautifulSoup(html, "html.parser")

    # Completely useless/non-visible areas.
    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "template",
            "svg",
            "canvas",
        ]
    ):
        tag.decompose()

    title = clean_text(
        soup.title.get_text(" ", strip=True)
        if soup.title
        else ""
    )

    meta_description = ""

    meta = soup.find(
        "meta",
        attrs={"name": re.compile("^description$", re.I)},
    )

    if meta:
        meta_description = clean_text(
            meta.get("content", "")
        )

    headings = unique_strings(
        [
            tag.get_text(" ", strip=True)
            for tag in soup.find_all(
                ["h1", "h2", "h3", "h4"]
            )
        ],
        max_items=40,
    )

    buttons = unique_strings(
        [
            tag.get_text(" ", strip=True)
            for tag in soup.find_all(
                ["button", "a", "input"]
            )
        ],
        max_items=80,
    )

    forms = []

    for form in soup.find_all("form"):
        form_text = clean_text(
            form.get_text(" ", strip=True)
        )

        if form_text:
            forms.append(form_text)

    forms = unique_strings(forms, max_items=30)

    body_text = clean_text(
        soup.get_text(" ", strip=True)
    )

    # Avoid absurdly large stored evidence.
    body_text = body_text[:100000]

    # Compact searchable corpus.
    corpus_parts = [
        title,
        meta_description,
        " ".join(headings),
        " ".join(buttons),
        " ".join(forms),
        body_text,
    ]

    corpus = clean_text(" ".join(corpus_parts))

    return {
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "buttons": buttons,
        "forms": forms,
        "body_text": body_text,
        "corpus": corpus,
    }


# ============================================================
# CONTENT HASH
# ============================================================

def calculate_content_hash(content):
    """
    Normalized evidence ka SHA-256 hash.

    Future Gemini phase mein:
        same hash -> Gemini SKIP
        changed hash -> Gemini re-analysis
    """

    normalized = re.sub(
        r"\s+",
        " ",
        content.get("corpus", "").lower(),
    ).strip()

    return hashlib.sha256(
        normalized.encode("utf-8", errors="ignore")
    ).hexdigest()


# ============================================================
# SIGNAL MATCHING
# ============================================================

def find_keyword_context(text, keyword, window=90):
    """
    Matched keyword ke around short evidence snippet return karta hai.
    """

    if not text or not keyword:
        return None

    text_lower = text.lower()
    keyword_lower = keyword.lower()

    position = text_lower.find(keyword_lower)

    if position == -1:
        return None

    start = max(0, position - window)
    end = min(
        len(text),
        position + len(keyword) + window,
    )

    snippet = clean_text(text[start:end])

    return snippet


def keyword_is_negative(text, keyword):
    """
    Keyword ke nearby context ko inspect karta hai.

    Example:
        "we do not offer investment services"

    ko positive investment signal nahi banana.
    """

    if not text:
        return False

    text_lower = text.lower()

    for pattern in NEGATIVE_PATTERNS:
        if pattern in text_lower:
            return True

    return False


def match_signals(content):
    corpus = content.get("corpus", "").lower()

    detected = {}
    matched_keywords = []
    evidence = []

    for signal_name, config in SIGNALS.items():
        matches = []

        for keyword in config["keywords"]:
            if keyword.lower() not in corpus:
                continue

            context = find_keyword_context(
                content.get("body_text", ""),
                keyword,
            )

            # Negative phrase ka direct/global presence ho to
            # obvious false-positive signal ko suppress karo.
            if keyword_is_negative(
                context or ""
            ):
                continue

            matches.append(keyword)
            matched_keywords.append(keyword)

            if context:
                evidence.append(
                    {
                        "signal": signal_name,
                        "keyword": keyword,
                        "context": context,
                    }
                )

        if matches:
            detected[signal_name] = {
                "matched": True,
                "keywords": unique_strings(matches),
                "weight": config["weight"],
            }

    return detected, unique_strings(
        matched_keywords,
        max_items=100,
    ), evidence


# ============================================================
# SCORING
# ============================================================

def calculate_score(detected):
    score = 0
    bonus_signals = []

    signal_names = set(detected.keys())

    for signal_name, data in detected.items():
        score += int(data["weight"])

    for required_signals, bonus, label in COMBINATION_BONUSES:
        if required_signals.issubset(signal_names):
            score += bonus

            bonus_signals.append(
                {
                    "reason": label,
                    "points": bonus,
                }
            )

    # Strong investment-site combination.
    if (
        "investment" in signal_names
        and "profit" in signal_names
        and "deposit" in signal_names
        and "withdrawal" in signal_names
    ):
        score += 20
        bonus_signals.append(
            {
                "reason": "complete investment transaction pattern",
                "points": 20,
            }
        )

    # Cap is deliberately high enough for future tuning.
    score = min(score, 200)

    return score, bonus_signals


def get_classification(score):
    if score >= 120:
        return "very_strong_candidate"

    if score >= 100:
        return "strong_candidate"

    if score >= 80:
        return "high_candidate"

    if score >= 60:
        return "possible_candidate"

    if score >= 30:
        return "weak_candidate"

    return "irrelevant"


# ============================================================
# SITE ANALYSIS
# ============================================================

def analyze_site(domain):
    scan_time = utc_now()

    fetched = fetch_site(domain)

    if not fetched.get("success"):
        return {
            "domain": domain,
            "status": fetched.get("status", "failed"),
            "http_status": fetched.get("http_status"),
            "url": fetched.get("url"),
            "score": 0,
            "classification": "unavailable",
            "content_hash": None,
            "signals": {},
            "matched_keywords": [],
            "evidence": [],
            "scanned_at": scan_time,
            "error": fetched.get("error"),
        }

    html = fetched.get("html", "")

    content = extract_content(html)

    content_hash = calculate_content_hash(content)

    detected, matched_keywords, evidence = match_signals(
        content
    )

    score, bonuses = calculate_score(detected)

    classification = get_classification(score)

    signals_output = {}

    for name, data in detected.items():
        signals_output[name] = {
            "matched": True,
            "keywords": data["keywords"],
            "weight": data["weight"],
        }

    result = {
        "domain": domain,
        "status": "active",
        "http_status": fetched.get("http_status"),
        "url": fetched.get("url"),
        "score": score,
        "classification": classification,
        "content_hash": content_hash,

        "signals": signals_output,

        "matched_keywords": matched_keywords,

        "score_breakdown": {
            "signals": {
                name: data["weight"]
                for name, data in detected.items()
            },
            "bonuses": bonuses,
            "total": score,
        },

        "evidence": evidence[:100],

        "page": {
            "title": content["title"],
            "meta_description": content[
                "meta_description"
            ],
            "headings": content["headings"][:20],
            "buttons": content["buttons"][:30],
            "forms": content["forms"][:20],
        },

        "scanned_at": scan_time,
        "error": None,
    }

    return result


# ============================================================
# MAIN SCANNER
# ============================================================

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("LD76 DOMAIN FINDER")
    print("Phase 1 - Python Scanner Engine")
    print("=" * 60)

    scan_started = utc_now()

    history = load_history()

    existing_results = load_json(
        RESULTS_FILE,
        [],
    )

    if not isinstance(existing_results, list):
        existing_results = []

    domains = get_recent_domains(TLD)

    if not domains:
        print("[!] No domains discovered.")
        return

    print(
        f"[*] Starting scan of {len(domains)} domains..."
    )

    current_results = []

    statistics = {
        "discovered": len(domains),
        "checked": 0,
        "active": 0,
        "failed": 0,
        "python_candidates": 0,
        "high_candidates": 0,
    }

    for index, domain in enumerate(
        domains,
        start=1,
    ):
        statistics["checked"] += 1

        print(
            f"[{index}/{len(domains)}] "
            f"Scanning {domain}"
        )

        try:
            result = analyze_site(domain)

            content_hash = result.get(
                "content_hash"
            )

            score = int(
                result.get("score", 0)
            )

            status = result.get(
                "status",
                "failed",
            )

            if status == "active":
                statistics["active"] += 1
            else:
                statistics["failed"] += 1

            if score >= MIN_SCORE:
                statistics["python_candidates"] += 1

            if score >= RESULT_SCORE:
                statistics["high_candidates"] += 1

                print(
                    f"  [MATCH] {domain} "
                    f"score={score} "
                    f"class={result.get('classification')}"
                )

                current_results.append(result)

            elif status == "active":
                print(
                    f"  [-] score={score}"
                )

            else:
                print(
                    f"  [!] {result.get('error')}"
                )

            update_history(
                history,
                domain,
                scan_time=result.get(
                    "scanned_at",
                    utc_now(),
                ),
                status=status,
                http_status=result.get(
                    "http_status"
                ),
                python_score=score,
                content_hash=content_hash,
                error=result.get("error"),
            )

        except Exception as exc:
            # One unexpected domain must never crash
            # the entire scan.
            print(
                f"  [ERROR] {domain}: {exc}"
            )

            update_history(
                history,
                domain,
                scan_time=utc_now(),
                status="scanner_error",
                python_score=0,
                error=str(exc),
            )

        if SCAN_DELAY > 0:
            time.sleep(SCAN_DELAY)

    # --------------------------------------------------------
    # Merge current high-quality results into results.json.
    # Same domain + same content hash = update rather than
    # creating endless duplicate entries.
    # --------------------------------------------------------

    result_index = {}

    for item in existing_results:
        if not isinstance(item, dict):
            continue

        domain = normalize_domain(
            item.get("domain")
        )

        if not domain:
            continue

        result_index[domain] = item

    for item in current_results:
        domain = item.get("domain")

        if not domain:
            continue

        result_index[domain] = item

    final_results = list(
        result_index.values()
    )

    final_results.sort(
        key=lambda item: (
            int(item.get("score", 0)),
            str(item.get("scanned_at", "")),
        ),
        reverse=True,
    )

    save_json(
        RESULTS_FILE,
        final_results,
    )

    save_json(
        HISTORY_FILE,
        history,
    )

    scan_finished = utc_now()

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)

    print(
        f"Discovered:       "
        f"{statistics['discovered']}"
    )

    print(
        f"Websites checked: "
        f"{statistics['checked']}"
    )

    print(
        f"Active websites:  "
        f"{statistics['active']}"
    )

    print(
        f"Failed/inactive:  "
        f"{statistics['failed']}"
    )

    print(
        f"Python candidates: "
        f"{statistics['python_candidates']}"
    )

    print(
        f"High candidates:   "
        f"{statistics['high_candidates']}"
    )

    print(
        f"Results stored:    "
        f"{len(final_results)}"
    )

    print(
        f"Started:           "
        f"{scan_started}"
    )

    print(
        f"Finished:          "
        f"{scan_finished}"
    )

    print()
    print(
        f"[*] Results: {RESULTS_FILE}"
    )

    print(
        f"[*] History: {HISTORY_FILE}"
    )


if __name__ == "__main__":
    main()
