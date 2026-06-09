package com.brightbean.studio.infrastructure.media

import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.util.UUID

class LocalMediaStorage(private val basePath: Path) : MediaStorage {
    constructor(baseDir: String) : this(Paths.get(baseDir))

    init {
        Files.createDirectories(basePath)
    }

    override fun upload(id: UUID, data: ByteArray, mimeType: String): MediaHandle {
        val filePath = basePath.resolve(id.toString())
        Files.write(filePath, data)
        return MediaHandle(
            id = id,
            url = filePath.toUri().toString(),
            mimeType = mimeType,
            size = data.size.toLong()
        )
    }

    override fun download(id: UUID): ByteArray? {
        val filePath = basePath.resolve(id.toString())
        return if (Files.exists(filePath)) Files.readAllBytes(filePath) else null
    }

    override fun delete(id: UUID) {
        val filePath = basePath.resolve(id.toString())
        Files.deleteIfExists(filePath)
    }

    override fun getUrl(id: UUID): String {
        return basePath.resolve(id.toString()).toUri().toString()
    }
}