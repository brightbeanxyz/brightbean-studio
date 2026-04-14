package com.brightbean.studio.web.ui.pages

import com.brightbean.studio.web.ui.components.BlogCard
import com.brightbean.studio.web.ui.components.BlogCardData
import com.brightbean.studio.web.ui.components.Footer
import com.brightbean.studio.web.ui.components.Header

data class StaticPageData(
    val title: String,
    val content: String,
    val slug: String,
)

class StaticPage(private val data: StaticPageData) {
    fun render(): String = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>${data.title}</title>
            <meta name="slug" content="${data.slug}">
        </head>
        <body>
            ${Header().render()}
            <main>
                <article>
                    <h1>${data.title}</h1>
                    <div class="content">${data.content}</div>
                </article>
            </main>
            ${Footer().render()}
        </body>
        </html>
    """.trimIndent()
}
