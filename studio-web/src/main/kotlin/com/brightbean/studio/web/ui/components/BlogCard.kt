package com.brightbean.studio.web.ui.components

data class BlogCardData(
    val title: String,
    val excerpt: String,
    val slug: String,
    val publishedAt: String,
)

class BlogCard(private val data: BlogCardData) {
    fun render(): String = """
        <div class="blog-card">
            <h3><a href="/blog/${data.slug}">${data.title}</a></h3>
            <p class="excerpt">${data.excerpt}</p>
            <span class="published-at">${data.publishedAt}</span>
        </div>
    """.trimIndent()
}
