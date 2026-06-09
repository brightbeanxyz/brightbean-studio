package com.brightbean.studio.infrastructure.media

import org.junit.jupiter.api.Test
import java.nio.file.Files
import java.nio.file.Path
import java.util.UUID
import org.junit.jupiter.api.Assertions.*

class MediaStorageTest {

    private fun createTempDir(): Path {
        return Files.createTempDirectory("media-test")
    }

    @Test
    fun `LocalMediaStorage uploads and downloads data`() {
        val dir = createTempDir()
        val storage = LocalMediaStorage(dir)
        val id = UUID.randomUUID()
        val data = "Hello World".toByteArray()

        val handle = storage.upload(id, data, "text/plain")
        assertEquals(id, handle.id)
        assertEquals("text/plain", handle.mimeType)
        assertEquals(11L, handle.size)
        assertNotNull(handle.url)

        val downloaded = storage.download(id)
        assertEquals(data.toList(), downloaded?.toList())

        assertEquals(handle.url, storage.getUrl(id))
    }

    @Test
    fun `LocalMediaStorage returns null for missing files`() {
        val dir = createTempDir()
        val storage = LocalMediaStorage(dir)
        val id = UUID.randomUUID()

        assertNull(storage.download(id))
    }

    @Test
    fun `LocalMediaStorage deletes files`() {
        val dir = createTempDir()
        val storage = LocalMediaStorage(dir)
        val id = UUID.randomUUID()
        val data = "Test data".toByteArray()

        storage.upload(id, data, "application/octet-stream")
        assertNotNull(storage.download(id))

        storage.delete(id)
        assertNull(storage.download(id))
    }
}