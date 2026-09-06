package com.lagenddesi.ld76domainfinder

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.lagenddesi.ld76domainfinder.data.DomainResult
import com.lagenddesi.ld76domainfinder.ui.DomainDetailsScreen
import com.lagenddesi.ld76domainfinder.ui.DomainFinderScreen
import com.lagenddesi.ld76domainfinder.ui.DomainFinderViewModel
import com.lagenddesi.ld76domainfinder.ui.DomainFinderViewModelFactory
import com.lagenddesi.ld76domainfinder.ui.HistoryScreen
import com.lagenddesi.ld76domainfinder.ui.LD76DomainFinderTheme

class MainActivity : ComponentActivity() {

    private val viewModel: DomainFinderViewModel by viewModels {
        DomainFinderViewModelFactory()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            LD76DomainFinderTheme {
                var currentScreen by remember {
                    mutableStateOf("home")
                }

                var selectedDomain by remember {
                    mutableStateOf<DomainResult?>(null)
                }

                when (currentScreen) {
                    "history" -> {
                        HistoryScreen(
                            history = viewModel.uiState.value.history,
                            isLoading = viewModel.uiState.value.isLoading,
                        )
                    }

                    "details" -> {
                        selectedDomain?.let { domain ->
                            DomainDetailsScreen(
                                result = domain,
                                onBack = {
                                    currentScreen = "home"
                                    selectedDomain = null
                                },
                                onRescan = {
    viewModel.rescanDomain(domain.domain)
},
                            )
                        }
                    }

                    else -> {
                        DomainFinderScreen(
                            viewModel = viewModel,
                            onDomainClick = { domain ->
                                selectedDomain = domain
                                currentScreen = "details"
                            },
                        )
                    }
                }

                if (currentScreen != "details") {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(
                                horizontal = 16.dp,
                                vertical = 8.dp,
                            ),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Button(
                            onClick = {
                                currentScreen = "home"
                            },
                            enabled = currentScreen != "home",
                        ) {
                            Text("Home")
                        }

                        Button(
                            onClick = {
                                currentScreen = "history"
                            },
                            enabled = currentScreen != "history",
                        ) {
                            Text("History")
                        }
                    }
                }
            }
        }
    }
}
