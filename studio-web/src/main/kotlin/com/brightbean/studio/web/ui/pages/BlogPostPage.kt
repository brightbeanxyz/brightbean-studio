package com.brightbean.studio.web.ui.pages

import com.brightbean.studio.web.ui.components.Footer
import com.brightbean.studio.web.ui.components.Header

data class BlogPostPageData(
    val title: String,
    val content: String,
    val slug: String,
    val publishedAt: String,
)

class BlogPostPage(private val data: BlogPostPageData) {
    fun render(): String = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>${data.title}</title>
        </head>
        <body>
            ${Header().render()}
            <main>
                <article>
                    <header>
                        <h1>${data.title}</h1>
                        <time>${data.publishedAt}</time>
                    </header>
                    <div class="content">${data.content}</div>
                </article>
            </main>
            ${Footer().render()}
        </body>
        </html>
    """.trimIndent()
}
