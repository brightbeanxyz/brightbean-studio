package com.brightbean.studio.web.ui.pages

import com.brightbean.studio.web.ui.components.BlogCard
import com.brightbean.studio.web.ui.components.BlogCardData
import com.brightbean.studio.web.ui.components.Footer
import com.brightbean.studio.web.ui.components.Header
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class BlogPageTest {

    @Test
    fun `header renders`() {
        val html = Header().render()
        assertTrue(html.contains("<header"))
        assertTrue(html.contains("</header>"))
    }

    @Test
    fun `footer renders`() {
        val html = Footer().render()
        assertTrue(html.contains("<footer"))
        assertTrue(html.contains("</footer>"))
    }

    @Test
    fun `blog card renders with data`() {
        val data = BlogCardData(
            title = "My Blog Post",
            excerpt = "This is the excerpt",
            slug = "my-blog-post",
            publishedAt = "2026-04-14",
        )
        val html = BlogCard(data).render()
        assertTrue(html.contains("My Blog Post"))
        assertTrue(html.contains("This is the excerpt"))
        assertTrue(html.contains("my-blog-post"))
        assertTrue(html.contains("2026-04-14"))
    }

    @Test
    fun `blog list page renders`() {
        val html = BlogListPage().render()
        assertTrue(html.contains("Blog"))
        assertTrue(html.contains("<div"))
    }

    @Test
    fun `blog post page renders with content`() {
        val data = BlogPostPageData(
            title = "Test Post",
            content = "<p>Hello world</p>",
            slug = "test-post",
            publishedAt = "2026-04-14",
        )
        val html = BlogPostPage(data).render()
        assertTrue(html.contains("Test Post"))
        assertTrue(html.contains("Hello world"))
    }

    @Test
    fun `static page renders`() {
        val data = StaticPageData(
            title = "About Us",
            content = "<p>About content</p>",
            slug = "about-us",
        )
        val html = StaticPage(data).render()
        assertTrue(html.contains("About Us"))
        assertTrue(html.contains("About content"))
        assertTrue(html.contains("about-us"))
    }

    @Test
    fun `blog list page contains blog cards`() {
        val posts = listOf(
            BlogCardData("Post 1", "Excerpt 1", "post-1", "2026-04-01"),
            BlogCardData("Post 2", "Excerpt 2", "post-2", "2026-04-02"),
        )
        val html = BlogListPage(posts).render()
        assertTrue(html.contains("Post 1"))
        assertTrue(html.contains("Post 2"))
    }
}
