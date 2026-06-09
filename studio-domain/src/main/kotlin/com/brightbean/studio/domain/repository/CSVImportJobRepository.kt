package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.CSVImportJob
import java.util.UUID

interface CSVImportJobRepository {
    fun findById(id: UUID): CSVImportJob?
    fun findByWorkspaceId(workspaceId: UUID): List<CSVImportJob>
    fun save(job: CSVImportJob): CSVImportJob
    fun update(job: CSVImportJob): CSVImportJob
}
