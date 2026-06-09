package com.brightbean.studio.web.ui.fragments

data class PostCardData(
    val title: String,
    val content: String,
    val platform: String,
    val scheduledAt: String? = null,
)

class PostCard(private val data: PostCardData) {
    fun render(): String = """
        <div class="post-card">
            <h3>${data.title}</h3>
            <p>${data.content}</p>
            <span class="platform">${data.platform}</span>
            ${if (data.scheduledAt != null) "<span class=\"scheduled-at\">${data.scheduledAt}</span>" else ""}
        </div>
    """.trimIndent()
}
