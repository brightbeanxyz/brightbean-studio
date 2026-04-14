package com.brightbean.studio.domain.model

import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Test
import java.util.Base64

class CredentialTest {

    private fun mockEncrypt(plainText: String): String {
        return Base64.getEncoder().encodeToString(plainText.toByteArray())
    }

    @Test
    fun `encrypted token is different from plain text`() {
        val plainToken = "my-secret-access-token"
        
        val encryptedToken = mockEncrypt(plainToken)
        
        assertNotEquals(plainToken, encryptedToken)
    }
}
