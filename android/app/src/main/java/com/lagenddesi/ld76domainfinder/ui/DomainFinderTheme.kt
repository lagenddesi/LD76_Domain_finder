package com.lagenddesi.ld76domainfinder.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LD76ColorScheme = lightColorScheme(
    primary = Color(0xFF1565C0),
    onPrimary = Color.White,
    secondary = Color(0xFF455A64),
    onSecondary = Color.White,
    background = Color(0xFFF7F9FC),
    onBackground = Color(0xFF17202A),
    surface = Color.White,
    onSurface = Color(0xFF17202A),
    error = Color(0xFFB3261E),
    onError = Color.White,
)

@Composable
fun LD76DomainFinderTheme(
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = LD76ColorScheme,
        content = content,
    )
}
