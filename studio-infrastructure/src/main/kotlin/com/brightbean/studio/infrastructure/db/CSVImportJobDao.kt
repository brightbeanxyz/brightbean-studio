package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(CSVImportJobDto::class)
interface CSVImportJobDao {
    @SqlQuery("SELECT * FROM composer_csv_import_job WHERE id = :id")
    fun findById(id: UUID): CSVImportJobDto?

    @SqlQuery("SELECT * FROM composer_csv_import_job WHERE workspace_id = :workspaceId ORDER BY created_at DESC")
    fun findByWorkspaceId(workspaceId: UUID): List<CSVImportJobDto>

    @SqlUpdate("""
        INSERT INTO composer_csv_import_job (id, workspace_id, uploaded_by, file_name, column_mapping, status, total_rows, processed_rows, result_summary, created_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.uploadedBy, :dto.fileName, :dto.columnMapping, :dto.status, :dto.totalRows, :dto.processedRows, :dto.resultSummary, :dto.createdAt)
    """)
    fun insert(dto: CSVImportJobDto)

    @SqlUpdate("""
        UPDATE composer_csv_import_job SET
            status = :dto.status,
            total_rows = :dto.totalRows,
            processed_rows = :dto.processedRows,
            result_summary = :dto.resultSummary
        WHERE id = :dto.id
    """)
    fun update(dto: CSVImportJobDto)
}

data class CSVImportJobDto(
    val id: UUID,
    val workspaceId: UUID,
    val uploadedBy: UUID?,
    val fileName: String,
    val columnMapping: String,
    val status: String,
    val totalRows: Int,
    val processedRows: Int,
    val resultSummary: String,
    val createdAt: java.time.Instant,
)
