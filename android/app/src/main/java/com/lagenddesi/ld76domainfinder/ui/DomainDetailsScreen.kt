package com.lagenddesi.ld76domainfinder.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.lagenddesi.ld76domainfinder.data.DomainResult

@Composable
fun DomainDetailsScreen(
    result: DomainResult,
    onBack: () -> Unit,
    onRescan: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        TextButton(
            onClick = onBack,
        ) {
            Text("Back")
        }

        Text(
            text = result.domain,
            style = MaterialTheme.typography.headlineMedium,
        )

        result.title
            ?.takeIf { it.isNotBlank() }
            ?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.titleMedium,
                )
            }

        InfoCard(
            title = "Analysis",
            lines = listOf(
                "Status: ${result.status ?: "Unknown"}",
                "Python score: ${result.python_score?.toInt() ?: 0}",
                "Gemini score: ${result.gemini_score?.toInt() ?: 0}",
                "Classification: ${result.classification ?: "Unknown"}",
                "Gemini analyzed: ${
                    if (result.gemini_analyzed) "Yes" else "No"
                }",
            ),
        )

        result.reason
            ?.takeIf { it.isNotBlank() }
            ?.let {
                InfoCard(
                    title = "Reason",
                    lines = listOf(it),
                )
            }

        result.url
            ?.takeIf { it.isNotBlank() }
            ?.let {
                InfoCard(
                    title = "URL",
                    lines = listOf(it),
                )
            }

        result.evidence_json
            ?.takeIf { it.isNotBlank() }
            ?.let {
                InfoCard(
                    title = "Evidence",
                    lines = listOf(it),
                )
            }

        result.signals_json
            ?.takeIf { it.isNotBlank() }
            ?.let {
                InfoCard(
                    title = "Signals",
                    lines = listOf(it),
                )
            }

        result.content_hash
            ?.takeIf { it.isNotBlank() }
            ?.let {
                InfoCard(
                    title = "Content hash",
                    lines = listOf(it),
                )
            }

        Spacer(modifier = Modifier.height(4.dp))

        Button(
            onClick = onRescan,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Rescan Domain")
        }
    }
}

@Composable
private fun InfoCard(
    title: String,
    lines: List<String>,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
            )

            lines.forEach { line ->
                Text(
                    text = line,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}
