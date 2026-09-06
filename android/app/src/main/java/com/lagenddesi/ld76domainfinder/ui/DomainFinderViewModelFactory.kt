package com.lagenddesi.ld76domainfinder.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.lagenddesi.ld76domainfinder.data.DomainRepository

class DomainFinderViewModelFactory(
    private val repository: DomainRepository = DomainRepository(),
) : ViewModelProvider.Factory {

    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(
        modelClass: Class<T>,
    ): T {
        if (modelClass.isAssignableFrom(DomainFinderViewModel::class.java)) {
            return DomainFinderViewModel(repository) as T
        }

        throw IllegalArgumentException(
            "Unknown ViewModel class: ${modelClass.name}",
        )
    }
}
