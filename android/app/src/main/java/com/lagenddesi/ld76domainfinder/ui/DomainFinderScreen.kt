package com.lagenddesi.ld76domainfinder.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.lagenddesi.ld76domainfinder.data.DomainResult

@Composable
fun DomainFinderScreen(
    viewModel: DomainFinderViewModel,
    onDomainClick: (DomainResult) -> Unit,
) {
    val uiState by viewModel.uiState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
    ) {
        Text(
            text = "LD76 Domain Finder",
            style = MaterialTheme.typography.headlineMedium,
        )

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedTextField(
            value = uiState.searchQuery,
            onValueChange = viewModel::updateSearchQuery,
            modifier = Modifier.fillMaxWidth(),
            label = {
                Text("Search domain")
            },
            singleLine = true,
        )

        Spacer(modifier = Modifier.height(12.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Button(
                onClick = viewModel::startScan,
                enabled = !uiState.isStartingScan &&
                    uiState.scanStatus?.status != "running",
            ) {
                Text(
                    text = if (uiState.isStartingScan) {
                        "Starting..."
                    } else {
                        "Start Scan"
                    },
                )
            }

            TextButton(
                onClick = viewModel::refreshResults,
            ) {
                Text("Refresh")
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        uiState.scanStatus?.let { status ->
            Card(
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(
                    modifier = Modifier.padding(12.dp),
                ) {
                    Text(
                        text = "Scan status: ${status.status}",
                        style = MaterialTheme.typography.titleMedium,
                    )

                    if (status.status == "running") {
                        Spacer(modifier = Modifier.height(8.dp))
                        CircularProgressIndicator()
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        text = "Discovered: ${status.domains_discovered}",
                    )

                    Text(
                        text = "Scanned: ${status.domains_scanned}",
                    )

                    Text(
                        text = "Candidates: ${status.candidates_found}",
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        uiState.errorMessage?.let { message ->
            Text(
                text = message,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium,
            )

            Spacer(modifier = Modifier.height(8.dp))
        }

        if (uiState.isLoading) {
            Column(
                modifier = Modifier.fillMaxWidth(),
            ) {
                CircularProgressIndicator()
            }
        } else if (uiState.results.isEmpty()) {
            Text(
                text = "No domain results found.",
                style = MaterialTheme.typography.bodyLarge,
            )
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(
                    items = uiState.results,
                    key = { result ->
                        result.domain
                    },
                ) { result ->
                    DomainResultCard(
                        result = result,
                        onClick = {
                            viewModel.selectDomain(result)
                            onDomainClick(result)
                        },
                    )
                }
            }
        }
    }
}

@Composable
private fun DomainResultCard(
    result: DomainResult,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
        ) {
            Text(
                text = result.domain,
                style = MaterialTheme.typography.titleMedium,
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "Python score: ${
                    result.python_score?.toInt() ?: 0
                }",
            )

            Text(
                text = "Gemini score: ${
                    result.gemini_score?.toInt() ?: 0
                }",
            )

            Text(
                text = "Classification: ${
                    result.classification ?: "Unknown"
                }",
            )

            Text(
                text = if (result.gemini_analyzed) {
                    "Gemini: Analyzed"
                } else {
                    "Gemini: Not analyzed"
                },
            )

            result.title
                ?.takeIf { it.isNotBlank() }
                ?.let { title ->
                    Spacer(modifier = Modifier.height(4.dp))

                    Text(
                        text = title,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
        }
    }
}
