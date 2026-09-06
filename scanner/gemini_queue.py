"""
LD76 Domain Finder
Gemini Queue - Phase 2

Purpose:
    Gemini analyzer ke liye controlled request queue.

Design:
    - Har domain ko Gemini nahi bhejna.
    - Sirf Python-filtered strong candidates.
    - Concurrent Gemini requests ko limit karna.
    - Daily budget enforce karna.
    - Same content hash ko dobara analyze na karna.
    - Failed candidate se poori scan process crash na ho.
"""

import os
import time
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

PYTHON_GEMINI_THRESHOLD = int(
    os.getenv(
        "PYTHON_GEMINI_THRESHOLD",
        "80",
    )
)


# ============================================================
# CANDIDATE FILTER
# ============================================================

def is_gemini_candidate(scanner_result):
    """
    Decide karta hai ke Python scanner result Gemini ko
    bhejne ke qabil hai ya nahi.
    """

    if not isinstance(
        scanner_result,
        dict,
    ):
        return False

    score = scanner_result.get(
        "score",
        scanner_result.get(
            "python_score",
            0,
        ),
    )

    try:
        score = int(score)
    except (
        TypeError,
        ValueError,
    ):
        return False

    if score < PYTHON_GEMINI_THRESHOLD:
        return False

    if not scanner_result.get(
        "domain"
    ):
        return False

    return True


# ============================================================
# CANDIDATE DEDUPLICATION
# ============================================================

def deduplicate_candidates(candidates):
    """
    Domain aur content_hash dono levels par duplicates
    remove karta hai.

    Same domain ke same content ko ek hi request milegi.
    """

    if not candidates:
        return []

    seen_domains = set()
    seen_hashes = set()

    unique = []

    for candidate in candidates:
        if not isinstance(
            candidate,
            dict,
        ):
            continue

        domain = str(
            candidate.get(
                "domain",
                "",
            )
        ).strip().lower()

        if not domain:
            continue

        content_hash = str(
            candidate.get(
                "content_hash",
                "",
            )
        ).strip()

        domain_key = domain

        if domain_key in seen_domains:
            continue

        if content_hash:
            if content_hash in seen_hashes:
                continue

            seen_hashes.add(
                content_hash
            )

        seen_domains.add(
            domain_key
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
    Python scanner ke results mein se sirf strong candidates
    queue ke liye select karta hai.
    """

    if not isinstance(
        scanner_results,
        list,
    ):
        return []

    candidates = []

    for result in scanner_results:
        if is_gemini_candidate(result):
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

    Import yahan intentionally kiya gaya hai taake queue module
    standalone import ho sake.
    """

    try:
        from gemini_analyzer import analyze_candidate
    except ImportError:
        try:
            from scanner.gemini_analyzer import (
                analyze_candidate
            )
        except ImportError as exc:
            return {
                "success": False,
                "status": "import_error",
                "domain": candidate.get(
                    "domain",
                    "",
                ),
                "error": str(exc),
            }

    try:
        return analyze_candidate(
            candidate,
            force=force,
        )

    except Exception as exc:
        return {
            "success": False,
            "status": "candidate_error",
            "domain": candidate.get(
                "domain",
                "",
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
    Strong Python candidates ko controlled concurrency ke
    saath Gemini analyzer tak bhejta hai.

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

    # ThreadPool sirf network-bound Gemini requests ko
    # efficiently handle karta hai.
    with ThreadPoolExecutor(
        max_workers=GEMINI_CONCURRENCY
    ) as executor:

        future_map = {
            executor.submit(
                process_candidate,
                candidate,
                force=force,
            ): candidate
            for candidate in queue
        }

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
                    "domain": candidate.get(
                        "domain",
                        "",
                    ),
                    "error": str(exc),
                }

            results.append(
                result
            )

    successful = sum(
        1
        for result in results
        if result.get(
            "success"
        )
    )

    return {
        "queued": len(queue),
        "processed": len(results),
        "successful": successful,
        "failed": len(results) - successful,
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
    Gemini classification ko original Python scanner
    results ke saath merge karta hai.

    Original Python evidence preserve rehti hai.
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

    for item in gemini_results:
        if not isinstance(
            item,
            dict,
        ):
            continue

        domain = str(
            item.get(
                "domain",
                "",
            )
        ).strip().lower()

        if domain:
            by_domain[
                domain
            ] = item

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

        domain = str(
            item.get(
                "domain",
                "",
            )
        ).strip().lower()

        gemini = by_domain.get(
            domain
        )

        if gemini:
            item[
                "gemini_analyzed"
            ] = bool(
                gemini.get(
                    "success"
                )
            )

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
                "",
            )

            if gemini.get(
                "analysis"
            ):
                item[
                    "gemini"
                ] = gemini[
                    "analysis"
                ]

        merged.append(
            item
        )

    return merged


# ============================================================
# SUMMARY
# ============================================================

def print_queue_summary(
    queue_result
):
    """
    Console-friendly summary.
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
# TEST
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
            "domain": "example.top",
            "score": 90,
            "content_hash": "abc123",
        },
        {
            "domain": "weak.top",
            "score": 30,
            "content_hash": "def456",
        },
    ]

    prepared = prepare_queue(
        demo
    )

    print(
        "Demo candidates:",
        len(prepared),
      )
