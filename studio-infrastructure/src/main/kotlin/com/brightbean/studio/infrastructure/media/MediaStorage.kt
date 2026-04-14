package com.brightbean.studio.infrastructure.media

import java.util.UUID

data class MediaHandle(
    val id: UUID,
    val url: String,
    val mimeType: String,
    val size: Long
)

interface MediaStorage {
    fun upload(id: UUID, data: ByteArray, mimeType: String): MediaHandle
    fun download(id: UUID): ByteArray?
    fun delete(id: UUID)
    fun getUrl(id: UUID): String
}