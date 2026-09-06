package com.lagenddesi.ld76domainfinder.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lagenddesi.ld76domainfinder.data.DomainRepository
import com.lagenddesi.ld76domainfinder.data.DomainResult
import com.lagenddesi.ld76domainfinder.data.ScanHistory
import com.lagenddesi.ld76domainfinder.data.ScanStatusResponse
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class DomainFinderUiState(
    val results: List<DomainResult> = emptyList(),
    val history: List<ScanHistory> = emptyList(),
    val scanStatus: ScanStatusResponse? = null,
    val selectedDomain: DomainResult? = null,
    val isLoading: Boolean = false,
    val isStartingScan: Boolean = false,
    val errorMessage: String? = null,
    val searchQuery: String = "",
    val minScore: Int? = null,
    val classification: String? = null,
)

class DomainFinderViewModel(
    private val repository: DomainRepository = DomainRepository(),
) : ViewModel() {

    private val _uiState = MutableStateFlow(DomainFinderUiState())
    val uiState: StateFlow<DomainFinderUiState> = _uiState.asStateFlow()

    private var statusPollingJob: Job? = null

    init {
        loadInitialData()
    }

    fun loadInitialData() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                errorMessage = null,
            )

            val resultsResult = repository.getResults()
            val historyResult = repository.getHistory()
            val statusResult = repository.getScanStatus()

            val currentState = _uiState.value

            _uiState.value = currentState.copy(
                results = resultsResult.getOrDefault(emptyList()),
                history = historyResult.getOrDefault(emptyList()),
                scanStatus = statusResult.getOrNull(),
                isLoading = false,
                errorMessage = firstError(
                    resultsResult.exceptionOrNull(),
                    historyResult.exceptionOrNull(),
                    statusResult.exceptionOrNull(),
                ),
            )

            if (statusResult.getOrNull()?.status == "running") {
                startStatusPolling()
            }
        }
    }

    fun refreshResults() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                errorMessage = null,
            )

            val result = repository.getResults(
                limit = 100,
                minScore = _uiState.value.minScore,
                classification = _uiState.value.classification,
                search = _uiState.value.searchQuery
                    .trim()
                    .takeIf { it.isNotEmpty() },
            )

            _uiState.value = _uiState.value.copy(
                results = result.getOrDefault(emptyList()),
                isLoading = false,
                errorMessage = result.exceptionOrNull()?.message,
            )
        }
    }

    fun updateSearchQuery(query: String) {
        _uiState.value = _uiState.value.copy(
            searchQuery = query,
        )
    }

    fun applyFilters(
        minScore: Int?,
        classification: String?,
    ) {
        _uiState.value = _uiState.value.copy(
            minScore = minScore,
            classification = classification,
        )

        refreshResults()
    }

    fun clearFilters() {
        _uiState.value = _uiState.value.copy(
            searchQuery = "",
            minScore = null,
            classification = null,
        )

        refreshResults()
    }

    fun selectDomain(domain: DomainResult?) {
        _uiState.value = _uiState.value.copy(
            selectedDomain = domain,
        )
    }

    fun startScan() {
        if (_uiState.value.isStartingScan) {
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isStartingScan = true,
                errorMessage = null,
            )

            val result = repository.startScan()

            if (result.isSuccess) {
                val response = result.getOrThrow()

                _uiState.value = _uiState.value.copy(
                    isStartingScan = false,
                    scanStatus = ScanStatusResponse(
                        scan_id = response.scan_id,
                        status = response.status,
                    ),
                )

                startStatusPolling()
            } else {
                _uiState.value = _uiState.value.copy(
                    isStartingScan = false,
                    errorMessage = result.exceptionOrNull()?.message
                        ?: "Unable to start scan.",
                )
            }
        }
    }

    fun rescanDomain(domain: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                errorMessage = null,
            )

            val result = repository.rescanDomain(domain)

            if (result.isFailure) {
                _uiState.value = _uiState.value.copy(
                    errorMessage = result.exceptionOrNull()?.message
                        ?: "Unable to rescan domain.",
                )
            }
        }
    }

    private fun startStatusPolling() {
        if (statusPollingJob?.isActive == true) {
            return
        }

        statusPollingJob = viewModelScope.launch {
            while (true) {
                val result = repository.getScanStatus()

                val status = result.getOrNull()

                if (status != null) {
                    _uiState.value = _uiState.value.copy(
                        scanStatus = status,
                    )

                    if (
                        status.status == "completed" ||
                        status.status == "failed" ||
                        status.status == "idle"
                    ) {
                        refreshResults()
                        break
                    }
                }

                delay(2000)
            }
        }
    }

    private fun firstError(vararg errors: Throwable?): String? {
        return errors
            .firstOrNull { it != null }
            ?.message
            ?.takeIf { it.isNotBlank() }
            ?: if (errors.any { it != null }) {
                "Unable to load backend data."
            } else {
                null
            }
    }

    override fun onCleared() {
        statusPollingJob?.cancel()
        super.onCleared()
    }
}
