package com.lagenddesi.ld76domainfinder

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.lagenddesi.ld76domainfinder.data.DomainResult
import com.lagenddesi.ld76domainfinder.ui.DomainDetailsScreen
import com.lagenddesi.ld76domainfinder.ui.DomainFinderScreen
import com.lagenddesi.ld76domainfinder.ui.DomainFinderViewModel
import com.lagenddesi.ld76domainfinder.ui.DomainFinderViewModelFactory
import com.lagenddesi.ld76domainfinder.ui.LD76DomainFinderTheme

class MainActivity : ComponentActivity() {

    private val viewModel: DomainFinderViewModel by viewModels {
        DomainFinderViewModelFactory()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            LD76DomainFinderTheme {
                var selectedDomain by remember {
                    mutableStateOf<DomainResult?>(null)
                }

                if (selectedDomain == null) {
                    DomainFinderScreen(
                        viewModel = viewModel,
                        onDomainClick = { domain ->
                            selectedDomain = domain
                        },
                    )
                } else {
                    DomainDetailsScreen(
                        result = selectedDomain!!,
                        onBack = {
                            selectedDomain = null
                        },
                        onRescan = { domain ->
                            viewModel.rescanDomain(domain)
                        },
                    )
                }
            }
        }
    }
}
