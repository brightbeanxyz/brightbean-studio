package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class CSVImportStatus {
    PENDING,
    PROCESSING,
    COMPLETED,
    FAILED,
}

data class CSVImportJob(
    val id: UUID,
    val workspaceId: UUID,
    val uploadedBy: UUID?,
    val fileName: String,
    val columnMapping: String,
    val status: CSVImportStatus,
    val totalRows: Int,
    val processedRows: Int,
    val resultSummary: String,
    val createdAt: Instant,
)
