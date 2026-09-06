package com.lagenddesi.ld76domainfinder.data

data class DomainResult(
    val id: Int? = null,
    val domain: String,
    val first_seen: String? = null,
    val last_seen: String? = null,
    val last_scan: String? = null,
    val status: String? = null,
    val python_score: Double? = null,
    val gemini_score: Double? = null,
    val gemini_analyzed: Boolean = false,
    val content_hash: String? = null,
    val title: String? = null,
    val url: String? = null,
    val classification: String? = null,
    val reason: String? = null,
    val evidence_json: String? = null,
    val signals_json: String? = null,
)

data class ScanHistory(
    val id: Int? = null,
    val started_at: String? = null,
    val finished_at: String? = null,
    val status: String,
    val domains_discovered: Int = 0,
    val domains_scanned: Int = 0,
    val candidates_found: Int = 0,
    val error_message: String? = null,
)

data class ScanStartResponse(
    val scan_id: Int,
    val status: String,
    val message: String? = null,
)

data class ScanStatusResponse(
    val scan_id: Int? = null,
    val status: String,
    val started_at: String? = null,
    val finished_at: String? = null,
    val domains_discovered: Int = 0,
    val domains_scanned: Int = 0,
    val candidates_found: Int = 0,
    val error_message: String? = null,
)

data class RescanResponse(
    val domain: String,
    val status: String,
    val message: String? = null,
)
