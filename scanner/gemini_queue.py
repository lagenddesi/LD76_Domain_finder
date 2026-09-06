"""
LD76 Domain Finder
Gemini Queue - Phase 2 Hardened

Purpose:
    Python-filtered strong candidates ko controlled way mein
    Gemini analyzer tak bhejna.

Design:
    - Gemini ko har domain nahi bhejna.
    - Python threshold mandatory.
    - Domain-level deduplication.
    - Same content hash ko queue mein duplicate request nahi.
    - Gemini analyzer apni persistent content cache handle karta hai.
    - ThreadPool concurrency controlled.
    - Failed candidate poori scan ko crash nahi karta.
    - Original domain identity hamesha preserve hoti hai.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# CONFIGURATION
# ============================================================

GEMINI_CONCURRENCY = max(
    1,
    int(
        os.getenv(
            "GEMINI_CONCURRENCY",
            "2",
        )
    ),
)

PYTHON_GEMINI_THRESHOLD = max(
    0,
    int(
        os.getenv(
            "PYTHON_GEMINI_THRESHOLD",
            "80",
        )
    ),
)


# ============================================================
# HELPERS
# ============================================================

def get_domain(candidate):
    """
    Candidate se normalized domain return karta hai.
    """
    if not isinstance(candidate, dict):
        return ""

    return str(
        candidate.get(
            "domain",
            "",
        )
    ).strip().lower()


def get_content_hash(candidate):
    """
    Candidate ka content hash return karta hai.
    """
    if not isinstance(candidate, dict):
        return ""

    return str(
        candidate.get(
            "content_hash",
            "",
        )
    ).strip()


def get_python_score(candidate):
    """
    Python scanner score safely read karta hai.
    """

    if not isinstance(candidate, dict):
        return 0

    value = candidate.get(
        "score",
        candidate.get(
            "python_score",
            0,
        ),
    )

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return 0


# ============================================================
# CANDIDATE FILTER
# ============================================================

def is_gemini_candidate(scanner_result):
    """
    Decide karta hai ke candidate Gemini analysis ke liye
    strong enough hai ya nahi.
    """

    if not isinstance(
        scanner_result,
        dict,
    ):
        return False

    domain = get_domain(
        scanner_result
    )

    if not domain:
        return False

    score = get_python_score(
        scanner_result
    )

    if score < PYTHON_GEMINI_THRESHOLD:
        return False

    return True


# ============================================================
# DOMAIN DEDUPLICATION
# ============================================================

def deduplicate_candidates(candidates):
    """
    Domain-level deduplication.

    IMPORTANT:
        Content hash global dedup yahan intentionally nahi kiya
        jata.

    Reason:
        Do different domains ka identical content ho sakta hai.
        Dono domains ko result set mein preserve karna zaroori hai.

    Gemini analyzer ki persistent content cache same content ke
    liye unnecessary API request ko already prevent karti hai.
    """

    if not isinstance(
        candidates,
        list,
    ):
        return []

    seen_domains = set()
    unique = []

    for candidate in candidates:

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        domain = get_domain(
            candidate
        )

        if not domain:
            continue

        if domain in seen_domains:
            continue

        seen_domains.add(
            domain
        )

        unique.append(
            candidate
        )

    return unique


# ============================================================
# QUEUE PREPARATION
# ============================================================

def prepare_queue(scanner_results):
    """
    Python scanner results ko Gemini queue ke liye prepare karta hai.

    Sirf threshold pass karne wale candidates queue mein aate hain.
    """

    if not isinstance(
        scanner_results,
        list,
    ):
        return []

    candidates = []

    for result in scanner_results:

        if not is_gemini_candidate(
            result
        ):
            continue

        candidates.append(
            result
        )

    return deduplicate_candidates(
        candidates
    )


# ============================================================
# SINGLE CANDIDATE PROCESSOR
# ============================================================

def process_candidate(
    candidate,
    *,
    force=False,
):
    """
    Ek candidate ko Gemini analyzer ke through process karta hai.

    Exception ko yahin contain kiya jata hai taake ek broken
    candidate poori scan ko crash na kare.
    """

    domain = get_domain(
        candidate
    )

    try:
        from gemini_analyzer import (
            analyze_candidate,
        )

    except ImportError:
        try:
            from scanner.gemini_analyzer import (
                analyze_candidate,
            )

        except ImportError as exc:
            return {
                "success": False,
                "status": "import_error",
                "domain": domain,
                "content_hash": get_content_hash(
                    candidate
                ),
                "error": str(exc),
            }

    try:
        result = analyze_candidate(
            candidate,
            force=force,
        )

        if not isinstance(
            result,
            dict,
        ):
            return {
                "success": False,
                "status": "invalid_analyzer_result",
                "domain": domain,
                "content_hash": get_content_hash(
                    candidate
                ),
                "error": (
                    "Gemini analyzer returned "
                    "a non-dictionary result."
                ),
            }

        # Analyzer result mein domain missing ho to
        # original candidate ka domain restore karo.
        if not result.get(
            "domain"
        ):
            result["domain"] = domain

        if not result.get(
            "content_hash"
        ):
            result["content_hash"] = (
                get_content_hash(
                    candidate
                )
            )

        return result

    except Exception as exc:
        return {
            "success": False,
            "status": "candidate_error",
            "domain": domain,
            "content_hash": get_content_hash(
                candidate
            ),
            "error": str(exc),
        }


# ============================================================
# QUEUE RUNNER
# ============================================================

def run_gemini_queue(
    scanner_results,
    *,
    force=False,
):
    """
    Strong candidates ko controlled concurrency ke saath
    Gemini analyzer tak bhejta hai.

    Returns:

        {
            "queued": int,
            "processed": int,
            "successful": int,
            "failed": int,
            "results": [...]
        }
    """

    queue = prepare_queue(
        scanner_results
    )

    if not queue:
        return {
            "queued": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "results": [],
        }

    results = []

    with ThreadPoolExecutor(
        max_workers=GEMINI_CONCURRENCY
    ) as executor:

        future_map = {}

        for candidate in queue:

            future = executor.submit(
                process_candidate,
                candidate,
                force=force,
            )

            future_map[
                future
            ] = candidate

        for future in as_completed(
            future_map
        ):

            candidate = future_map[
                future
            ]

            try:
                result = future.result()

            except Exception as exc:
                result = {
                    "success": False,
                    "status": "queue_error",
                    "domain": get_domain(
                        candidate
                    ),
                    "content_hash": get_content_hash(
                        candidate
                    ),
                    "error": str(exc),
                }

            if not isinstance(
                result,
                dict,
            ):
                result = {
                    "success": False,
                    "status": "invalid_queue_result",
                    "domain": get_domain(
                        candidate
                    ),
                    "content_hash": get_content_hash(
                        candidate
                    ),
                    "error": (
                        "Queue received invalid "
                        "result object."
                    ),
                }

            results.append(
                result
            )

    successful = 0
    failed = 0

    for result in results:

        if result.get(
            "success",
            False,
        ):
            successful += 1
        else:
            failed += 1

    return {
        "queued": len(queue),
        "processed": len(results),
        "successful": successful,
        "failed": failed,
        "results": results,
    }


# ============================================================
# RESULT MERGING
# ============================================================

def merge_gemini_results(
    scanner_results,
    gemini_results,
):
    """
    Gemini results ko original Python scanner results ke saath
    domain ke basis par merge karta hai.

    Important:
        Original Python evidence kabhi delete nahi hoti.

    Agar Gemini fail ho:
        Python result phir bhi preserve rehta hai.
    """

    if not isinstance(
        scanner_results,
        list,
    ):
        return []

    if not isinstance(
        gemini_results,
        list,
    ):
        return scanner_results

    by_domain = {}

    for gemini_result in gemini_results:

        if not isinstance(
            gemini_result,
            dict,
        ):
            continue

        domain = get_domain(
            gemini_result
        )

        if not domain:
            continue

        by_domain[
            domain
        ] = gemini_result

    merged = []

    for scanner_result in scanner_results:

        if not isinstance(
            scanner_result,
            dict,
        ):
            continue

        item = dict(
            scanner_result
        )

        domain = get_domain(
            item
        )

        gemini = by_domain.get(
            domain
        )

        if gemini is None:

            # Candidate Gemini queue mein nahi gaya.
            item.setdefault(
                "gemini_analyzed",
                False,
            )

            merged.append(
                item
            )

            continue

        success = bool(
            gemini.get(
                "success",
                False,
            )
        )

        item[
            "gemini_analyzed"
        ] = success

        item[
            "gemini_status"
        ] = gemini.get(
            "status",
            "",
        )

        item[
            "gemini_content_hash"
        ] = gemini.get(
            "content_hash",
            get_content_hash(
                item
            ),
        )

        if gemini.get(
            "analysis"
        ) is not None:

            item[
                "gemini"
            ] = gemini[
                "analysis"
            ]

        if gemini.get(
            "error"
        ):
            item[
                "gemini_error"
            ] = gemini[
                "error"
            ]

        merged.append(
            item
        )

    return merged


# ============================================================
# RESULT SORTING
# ============================================================

def sort_gemini_results(
    results
):
    """
    High Python score ko upar rakhta hai.

    Gemini failure ya missing score ki wajah se crash nahi hota.
    """

    if not isinstance(
        results,
        list,
    ):
        return []

    def sort_key(item):

        if not isinstance(
            item,
            dict,
        ):
            return 0

        return get_python_score(
            item
        )

    return sorted(
        results,
        key=sort_key,
        reverse=True,
    )


# ============================================================
# SUMMARY
# ============================================================

def print_queue_summary(
    queue_result
):
    """
    Console-friendly queue summary.
    """

    if not isinstance(
        queue_result,
        dict,
    ):
        return

    print(
        "[Gemini Queue]"
    )

    print(
        "  Queued:",
        queue_result.get(
            "queued",
            0,
        ),
    )

    print(
        "  Processed:",
        queue_result.get(
            "processed",
            0,
        ),
    )

    print(
        "  Successful:",
        queue_result.get(
            "successful",
            0,
        ),
    )

    print(
        "  Failed:",
        queue_result.get(
            "failed",
            0,
        ),
    )


# ============================================================
# TEST / DEMO
# ============================================================

if __name__ == "__main__":

    print(
        "LD76 Gemini Queue"
    )

    print(
        "-----------------"
    )

    print(
        "Concurrency:",
        GEMINI_CONCURRENCY,
    )

    print(
        "Python threshold:",
        PYTHON_GEMINI_THRESHOLD,
    )

    demo = [
        {
            "domain": "strong-one.top",
            "score": 90,
            "content_hash": "aaa111",
        },
        {
            "domain": "strong-two.top",
            "score": 85,
            "content_hash": "aaa111",
        },
        {
            "domain": "duplicate.top",
            "score": 95,
            "content_hash": "bbb222",
        },
        {
            "domain": "duplicate.top",
            "score": 99,
            "content_hash": "ccc333",
        },
        {
            "domain": "weak.top",
            "score": 30,
            "content_hash": "ddd444",
        },
    ]

    prepared = prepare_queue(
        demo
    )

    print(
        "Prepared candidates:",
        len(prepared),
    )

    for candidate in prepared:
        print(
            " -",
            get_domain(
                candidate
            ),
            "| score:",
            get_python_score(
                candidate
            ),
            "| hash:",
            get_content_hash(
                candidate
            ),
        )
