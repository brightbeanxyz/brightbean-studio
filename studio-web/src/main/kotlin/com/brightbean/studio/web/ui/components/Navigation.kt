package com.brightbean.studio.web.ui.components

class Navigation {
    fun render(): String = """
        <nav>
            <ul>
                <li><a href="/dashboard">Dashboard</a></li>
                <li><a href="/composer">Composer</a></li>
                <li><a href="/calendar">Calendar</a></li>
                <li><a href="/inbox">Inbox</a></li>
                <li><a href="/settings">Settings</a></li>
            </ul>
        </nav>
    """.trimIndent()
}
