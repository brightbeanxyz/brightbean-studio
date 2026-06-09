package com.brightbean.studio.web.ui.pages

import com.brightbean.studio.web.ui.components.BlogCard
import com.brightbean.studio.web.ui.components.BlogCardData
import com.brightbean.studio.web.ui.components.Footer
import com.brightbean.studio.web.ui.components.Header

class BlogListPage(private val posts: List<BlogCardData> = emptyList()) {
    fun render(): String {
        val postsHtml = posts.joinToString("\n") { BlogCard(it).render() }
        return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Blog</title>
            </head>
            <body>
                ${Header().render()}
                <main>
                    <h1>Blog</h1>
                    <div class="blog-list">
                        ${if (posts.isEmpty()) "<p>No posts yet.</p>" else postsHtml}
                    </div>
                </main>
                ${Footer().render()}
            </body>
            </html>
        """.trimIndent()
    }
}
