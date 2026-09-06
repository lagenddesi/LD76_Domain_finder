package com.lagenddesi.ld76domainfinder.data

import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {

    @GET("api/results")
    suspend fun getResults(
        @Query("limit") limit: Int = 100,
        @Query("min_score") minScore: Int? = null,
        @Query("min_gemini_score") minGeminiScore: Int? = null,
        @Query("classification") classification: String? = null,
        @Query("search") search: String? = null,
    ): List<DomainResult>

    @GET("api/results/{domain}")
    suspend fun getResult(
        @Path("domain") domain: String,
    ): DomainResult

    @GET("api/history")
    suspend fun getHistory(
        @Query("limit") limit: Int = 50,
    ): List<ScanHistory>

    @POST("api/scan/start")
    suspend fun startScan(): ScanStartResponse

    @GET("api/scan/status")
    suspend fun getScanStatus(): ScanStatusResponse

    @GET("api/scan/status/{scanId}")
    suspend fun getScanStatus(
        @Path("scanId") scanId: Int,
    ): ScanStatusResponse

    @POST("api/rescan/{domain}")
    suspend fun rescanDomain(
        @Path("domain") domain: String,
    ): RescanResponse
}
