package com.brightbean.studio.infrastructure.config

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class StudioConfigTest {

    @Test
    fun `reads config from environment variables`() {
        val env = mapOf(
            "DATABASE_URL" to "postgres://user:pass@localhost:5432/studio",
            "SECRET_KEY" to "test-secret-key",
            "ENCRYPTION_KEY_SALT" to "test-salt",
            "SERVER_PORT" to "9090",
            "CORS_ORIGINS" to "http://localhost:3000,http://localhost:4000",
        )
        val config = StudioConfig.fromEnv(env)

        assertEquals("jdbc:postgresql://localhost:5432/studio?user=user&password=pass", config.jdbcUrl)
        assertEquals("test-secret-key", config.secretKey)
        assertEquals("test-salt", config.encryptionKeySalt)
        assertEquals(9090, config.serverPort)
        assertEquals(2, config.corsOrigins.size)
        assertTrue(config.corsOrigins.contains("http://localhost:3000"))
    }

    @Test
    fun `uses defaults when env vars missing`() {
        val env = mapOf(
            "DATABASE_URL" to "postgres://user:pass@localhost:5432/studio",
            "SECRET_KEY" to "test-secret",
            "ENCRYPTION_KEY_SALT" to "test-salt",
        )
        val config = StudioConfig.fromEnv(env)

        assertEquals(8080, config.serverPort)
        assertEquals(listOf("*"), config.corsOrigins)
        assertFalse(config.debug)
    }

    @Test
    fun `parses DATABASE_URL into JDBC URL`() {
        val env = mapOf(
            "DATABASE_URL" to "postgres://myuser:mypass@db.example.com:5432/mydb?sslmode=require",
            "SECRET_KEY" to "secret",
            "ENCRYPTION_KEY_SALT" to "salt",
        )
        val config = StudioConfig.fromEnv(env)

        assertTrue(config.jdbcUrl.contains("db.example.com"))
        assertTrue(config.jdbcUrl.contains("mydb"))
        assertTrue(config.jdbcUrl.contains("myuser"))
        assertTrue(config.jdbcUrl.contains("mypass"))
    }
}
