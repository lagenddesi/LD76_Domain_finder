"""
LD76 Domain Finder
Single-Domain Rescan Runner

Existing scanner logic ko reuse karta hai:
    normalize_domain()
    create_session()
    analyze_site()
    run_gemini_analysis()
    merge_results()
    load_existing_results()
    load_history()
    update_history()
    save_json()

Usage:
    python scanner/rescan.py example.top
"""

import sys


from scanner import (
    DOMAIN_TLD,
    RESULTS_FILE,
    HISTORY_FILE,
    create_session,
    normalize_domain,
    analyze_site,
    run_gemini_analysis,
    merge_results,
    load_existing_results,
    load_history,
    update_history,
    save_json,
    utc_now,
)


def run_rescan(domain):
    normalized_domain = normalize_domain(domain)

    if not normalized_domain:
        raise ValueError(
            f"Invalid domain. Expected a .{DOMAIN_TLD} domain."
        )

    print(
        "=========================================="
    )
    print(
        "LD76 Domain Finder - Targeted Rescan"
    )
    print(
        "=========================================="
    )
    print(
        f"[*] Domain: {normalized_domain}"
    )

    started_at = utc_now()

    session = create_session()

    try:
        result = analyze_site(
            session,
            normalized_domain,
        )
    finally:
        session.close()

    if not result:
        raise RuntimeError(
            "Scanner returned no result."
        )

    analyzed_results = run_gemini_analysis(
        [result]
    )

    if analyzed_results:
        result = analyzed_results[0]

    existing_results = load_existing_results()

    merged_results = merge_results(
        existing_results,
        [result],
    )

    save_json(
        RESULTS_FILE,
        merged_results,
    )

    history = load_history()

    update_history(
        history,
        result,
    )

    history["last_scan"] = {
        "started_at": started_at,
        "finished_at": utc_now(),
        "mode": "targeted",
        "domains_discovered": 1,
        "domains_scanned": 1,
        "candidates_found": (
            1
            if result.get("python_score", 0) >= 60
            else 0
        ),
    }

    save_json(
        HISTORY_FILE,
        history,
    )

    print(
        f"[*] Status: {result.get('status', 'unknown')}"
    )
    print(
        f"[*] Python score: "
        f"{result.get('python_score', 0)}"
    )
    print(
        f"[*] Gemini analyzed: "
        f"{result.get('gemini_analyzed', False)}"
    )
    print(
        "[+] Targeted rescan completed."
    )

    return result


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python scanner/rescan.py <domain>"
        )
        return 2

    try:
        result = run_rescan(
            sys.argv[1]
        )

        print(
            "[Result]"
        )
        print(
            result
        )

        return 0

    except Exception as exc:
        print(
            f"[!] Rescan failed: {exc}"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
