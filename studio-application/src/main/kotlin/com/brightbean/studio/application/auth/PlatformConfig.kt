package com.brightbean.studio.application.auth

object PlatformConfig {
    data class FieldConfig(
        val supportsAltText: Boolean = false,
        val supportsFirstComment: Boolean = false,
        val supportsLink: Boolean = false,
        val supportsTagging: Boolean = false,
        val supportsLocation: Boolean = false,
    )

    val CHAR_LIMITS: Map<String, Int> = mapOf(
        "TWITTER" to 280,
        "THREADS" to 500,
        "MASTODON" to 500,
        "BLUESKY" to 300,
        "LINKEDIN_PERSONAL" to 3000,
        "LINKEDIN_COMPANY" to 3000,
        "FACEBOOK" to 63206,
        "INSTAGRAM" to 2200,
        "INSTAGRAM_PERSONAL" to 2200,
        "TIKTOK" to 2200,
        "YOUTUBE" to 5000,
        "PINTEREST" to 500,
        "GOOGLE_BUSINESS" to 1500,
    )

    val FIELD_CONFIG: Map<String, FieldConfig> = mapOf(
        "TWITTER" to FieldConfig(supportsLink = true),
        "THREADS" to FieldConfig(supportsAltText = true),
        "FACEBOOK" to FieldConfig(supportsAltText = true, supportsFirstComment = true, supportsLink = true, supportsTagging = true, supportsLocation = true),
        "INSTAGRAM" to FieldConfig(supportsAltText = true, supportsFirstComment = true, supportsLocation = true, supportsTagging = true),
        "INSTAGRAM_PERSONAL" to FieldConfig(supportsAltText = true),
        "LINKEDIN_PERSONAL" to FieldConfig(supportsLink = true),
        "LINKEDIN_COMPANY" to FieldConfig(supportsLink = true),
        "TIKTOK" to FieldConfig(supportsLink = true, supportsTagging = true),
        "YOUTUBE" to FieldConfig(supportsLink = true),
        "PINTEREST" to FieldConfig(supportsLink = true, supportsAltText = true),
        "BLUESKY" to FieldConfig(supportsAltText = true, supportsLink = true),
        "MASTODON" to FieldConfig(supportsAltText = true, supportsLink = true),
        "GOOGLE_BUSINESS" to FieldConfig(supportsLink = true, supportsLocation = true),
    )

    fun getCharLimit(platform: String): Int = CHAR_LIMITS[platform] ?: 2200

    fun getFieldConfig(platform: String): FieldConfig = FIELD_CONFIG[platform] ?: FieldConfig()

    fun supportsFirstComment(platform: String): Boolean = getFieldConfig(platform).supportsFirstComment
}
