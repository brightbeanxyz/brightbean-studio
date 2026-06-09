package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.CSVImportJob
import com.brightbean.studio.domain.model.CSVImportStatus
import com.brightbean.studio.domain.repository.CSVImportJobRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBICSVImportJobRepository(jdbi: Jdbi) : CSVImportJobRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: CSVImportJobDao by lazy { jdbi.onDemand(CSVImportJobDao::class.java) }

    override fun findById(id: UUID): CSVImportJob? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<CSVImportJob> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun save(job: CSVImportJob): CSVImportJob {
        dao.insert(job.toDto())
        return job
    }

    override fun update(job: CSVImportJob): CSVImportJob {
        dao.update(job.toDto())
        return job
    }

    private fun CSVImportJob.toDto() = CSVImportJobDto(
        id = id, workspaceId = workspaceId, uploadedBy = uploadedBy,
        fileName = fileName, columnMapping = columnMapping, status = status.name,
        totalRows = totalRows, processedRows = processedRows,
        resultSummary = resultSummary, createdAt = createdAt,
    )

    private fun CSVImportJobDto.toDomain() = CSVImportJob(
        id = id, workspaceId = workspaceId, uploadedBy = uploadedBy,
        fileName = fileName, columnMapping = columnMapping,
        status = try { CSVImportStatus.valueOf(status) } catch (_: Exception) { CSVImportStatus.PENDING },
        totalRows = totalRows, processedRows = processedRows,
        resultSummary = resultSummary, createdAt = createdAt,
    )
}
