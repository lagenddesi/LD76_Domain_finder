package com.lagenddesi.ld76domainfinder.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.lagenddesi.ld76domainfinder.data.ScanHistory

@Composable
fun HistoryScreen(
    history: List<ScanHistory>,
    isLoading: Boolean = false,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
    ) {
        Text(
            text = "Scan History",
            style = MaterialTheme.typography.headlineMedium,
        )

        if (isLoading) {
            CircularProgressIndicator(
                modifier = Modifier.padding(top = 16.dp),
            )
        } else if (history.isEmpty()) {
            Text(
                text = "No scan history available.",
                modifier = Modifier.padding(top = 16.dp),
                style = MaterialTheme.typography.bodyLarge,
            )
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(
                    items = history,
                    key = { item ->
                        item.id
                    },
                ) { item ->
                    HistoryCard(item)
                }
            }
        }
    }
}

@Composable
private fun HistoryCard(
    item: ScanHistory,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
        ) {
            Text(
                text = "Scan #${item.id}",
                style = MaterialTheme.typography.titleMedium,
            )

            Text(
                text = "Status: ${item.status}",
            )

            Text(
                text = "Discovered: ${item.domains_discovered}",
            )

            Text(
                text = "Scanned: ${item.domains_scanned}",
            )

            Text(
                text = "Candidates: ${item.candidates_found}",
            )

            item.started_at?.let { started ->
                Text(
                    text = "Started: $started",
                )
            }

            item.finished_at?.let { finished ->
                Text(
                    text = "Finished: $finished",
                )
            }

            item.error_message
                ?.takeIf { it.isNotBlank() }
                ?.let { error ->
                    Text(
                        text = "Error: $error",
                        color = MaterialTheme.colorScheme.error,
                    )
                }
        }
    }
}
