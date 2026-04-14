package com.brightbean.studio.infrastructure.media

import java.util.UUID

class S3MediaStorage(
    private val bucket: String,
    private val region: String,
    private val accessKey: String,
    private val secretKey: String
) : MediaStorage {

    override fun upload(id: UUID, data: ByteArray, mimeType: String): MediaHandle {
        TODO("S3 integration not yet implemented")
    }

    override fun download(id: UUID): ByteArray? {
        TODO("S3 integration not yet implemented")
    }

    override fun delete(id: UUID) {
        TODO("S3 integration not yet implemented")
    }

    override fun getUrl(id: UUID): String {
        TODO("S3 integration not yet implemented")
    }
}