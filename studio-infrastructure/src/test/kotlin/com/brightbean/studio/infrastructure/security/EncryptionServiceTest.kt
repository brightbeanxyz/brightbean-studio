package com.brightbean.studio.infrastructure.security

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test

class EncryptionServiceTest {

    private lateinit var encryptionService: EncryptionService

    @BeforeEach
    fun setUp() {
        encryptionService = EncryptionService("test-secret-key", "test-salt-value")
    }

    @Test
    fun `encrypt and decrypt round-trip returns original`() {
        val original = "my-secret-token-12345"
        val encrypted = encryptionService.encrypt(original)
        val decrypted = encryptionService.decrypt(encrypted)
        assertNotEquals(original, encrypted)
        assertEquals(original, decrypted)
    }

    @Test
    fun `encrypted value is base64 encoded`() {
        val encrypted = encryptionService.encrypt("some-value")
        assertTrue(encrypted.matches(Regex("^[A-Za-z0-9+/]+=*$")))
    }

    @Test
    fun `different values produce different ciphertexts`() {
        val enc1 = encryptionService.encrypt("value-1")
        val enc2 = encryptionService.encrypt("value-2")
        assertNotEquals(enc1 as Any?, enc2 as Any?)
    }

    @Test
    fun `same value produces different ciphertexts due to random IV`() {
        val enc1 = encryptionService.encrypt("same-value")
        val enc2 = encryptionService.encrypt("same-value")
        assertNotEquals(enc1 as Any?, enc2 as Any?)
        assertEquals(encryptionService.decrypt(enc1), encryptionService.decrypt(enc2))
    }

    @Test
    fun `handles empty string`() {
        val encrypted = encryptionService.encrypt("")
        assertEquals("", encryptionService.decrypt(encrypted))
    }

    @Test
    fun `handles unicode content`() {
        val original = "Hello, World! 你好世界"
        val encrypted = encryptionService.encrypt(original)
        assertEquals(original, encryptionService.decrypt(encrypted))
    }
}
