package com.brightbean.studio.web.ui

import com.brightbean.studio.web.ui.components.Navigation
import com.brightbean.studio.web.ui.pages.DashboardPage

class BrightBeanApp {
    fun render(page: String = "dashboard"): String {
        val nav = Navigation().render()
        val content = when (page) {
            "dashboard" -> DashboardPage().render()
            else -> DashboardPage().render()
        }
        return """
            <!DOCTYPE html>
            <html lang="en">
            <head><meta charset="UTF-8"><title>BrightBean Studio</title></head>
            <body>
            $nav
            <main>$content</main>
            </body>
            </html>
        """.trimIndent()
    }
}
