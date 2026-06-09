package com.brightbean.studio.domain.model

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class PostTest {

    @Test
    fun `PlatformPostStatus DRAFT can transition to PENDING_REVIEW, SCHEDULED, PUBLISHING`() {
        assertTrue(PlatformPostStatus.DRAFT.canTransitionTo(PlatformPostStatus.PENDING_REVIEW))
        assertTrue(PlatformPostStatus.DRAFT.canTransitionTo(PlatformPostStatus.SCHEDULED))
        assertTrue(PlatformPostStatus.DRAFT.canTransitionTo(PlatformPostStatus.PUBLISHING))
        assertFalse(PlatformPostStatus.DRAFT.canTransitionTo(PlatformPostStatus.PUBLISHED))
    }

    @Test
    fun `PlatformPostStatus PUBLISHED cannot transition to anything`() {
        assertFalse(PlatformPostStatus.PUBLISHED.canTransitionTo(PlatformPostStatus.DRAFT))
        assertFalse(PlatformPostStatus.PUBLISHED.canTransitionTo(PlatformPostStatus.FAILED))
    }

    @Test
    fun `derivePostStatus returns DRAFT for empty collection`() {
        assertEquals(PlatformPostStatus.DRAFT, derivePostStatus(emptyList()))
    }

    @Test
    fun `derivePostStatus returns single status when all agree`() {
        assertEquals(PlatformPostStatus.SCHEDULED, derivePostStatus(listOf(PlatformPostStatus.SCHEDULED, PlatformPostStatus.SCHEDULED)))
    }

    @Test
    fun `derivePostStatus returns PARTIALLY_PUBLISHED for mixed PUBLISHED and FAILED`() {
        assertEquals(PlatformPostStatus.PARTIALLY_PUBLISHED, derivePostStatus(listOf(PlatformPostStatus.PUBLISHED, PlatformPostStatus.FAILED)))
    }
}
