package com.lagenddesi.ld76domainfinder.data

class DomainRepository(
    private val apiService: ApiService = ApiClient.service,
) {

    suspend fun getResults(
        limit: Int = 100,
        minScore: Int? = null,
        minGeminiScore: Int? = null,
        classification: String? = null,
        search: String? = null,
    ): Result<List<DomainResult>> {
        return runCatching {
            apiService.getResults(
                limit = limit,
                minScore = minScore,
                minGeminiScore = minGeminiScore,
                classification = classification,
                search = search,
            )
        }
    }

    suspend fun getResult(
        domain: String,
    ): Result<DomainResult> {
        return runCatching {
            apiService.getResult(domain)
        }
    }

    suspend fun getHistory(
        limit: Int = 50,
    ): Result<List<ScanHistory>> {
        return runCatching {
            apiService.getHistory(limit)
        }
    }

    suspend fun startScan(): Result<ScanStartResponse> {
        return runCatching {
            apiService.startScan()
        }
    }

    suspend fun getScanStatus(): Result<ScanStatusResponse> {
        return runCatching {
            apiService.getScanStatus()
        }
    }

    suspend fun getScanStatus(
        scanId: Int,
    ): Result<ScanStatusResponse> {
        return runCatching {
            apiService.getScanStatus(scanId)
        }
    }

    suspend fun rescanDomain(
        domain: String,
    ): Result<RescanResponse> {
        return runCatching {
            apiService.rescanDomain(domain)
        }
    }
}
