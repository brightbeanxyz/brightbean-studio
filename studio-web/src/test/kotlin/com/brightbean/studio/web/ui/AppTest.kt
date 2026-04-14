package com.brightbean.studio.web.ui

import com.brightbean.studio.web.ui.components.Navigation
import com.brightbean.studio.web.ui.fragments.PostCard
import com.brightbean.studio.web.ui.fragments.PostCardData
import com.brightbean.studio.web.ui.pages.ComposerPage
import com.brightbean.studio.web.ui.pages.DashboardPage
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class AppTest {

    @Test
    fun `app renders html document`() {
        val html = BrightBeanApp().render()
        assertTrue(html.contains("<!DOCTYPE html>"))
        assertTrue(html.contains("<html"))
        assertTrue(html.contains("BrightBean Studio"))
    }

    @Test
    fun `app renders navigation`() {
        val html = BrightBeanApp().render()
        assertTrue(html.contains("<nav>"))
        assertTrue(html.contains("Dashboard"))
        assertTrue(html.contains("Composer"))
    }

    @Test
    fun `app renders dashboard by default`() {
        val html = BrightBeanApp().render()
        assertTrue(html.contains("dashboard"))
    }

    @Test
    fun `navigation renders all links`() {
        val html = Navigation().render()
        assertTrue(html.contains("/dashboard"))
        assertTrue(html.contains("/composer"))
        assertTrue(html.contains("/calendar"))
        assertTrue(html.contains("/inbox"))
        assertTrue(html.contains("/settings"))
    }

    @Test
    fun `dashboard page renders`() {
        val html = DashboardPage().render()
        assertTrue(html.contains("Dashboard"))
    }

    @Test
    fun `composer page renders`() {
        val html = ComposerPage().render()
        assertTrue(html.contains("Composer"))
    }

    @Test
    fun `post card renders with data`() {
        val data = PostCardData(
            title = "My Post",
            content = "Hello world",
            platform = "Twitter",
        )
        val html = PostCard(data).render()
        assertTrue(html.contains("My Post"))
        assertTrue(html.contains("Hello world"))
        assertTrue(html.contains("Twitter"))
    }

    @Test
    fun `post card renders scheduled time when provided`() {
        val data = PostCardData(
            title = "Scheduled Post",
            content = "Coming soon",
            platform = "Instagram",
            scheduledAt = "2026-04-20T10:00:00",
        )
        val html = PostCard(data).render()
        assertTrue(html.contains("2026-04-20T10:00:00"))
    }
}
