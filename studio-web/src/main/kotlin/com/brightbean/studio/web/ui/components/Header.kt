package com.brightbean.studio.web.ui.components

class Header {
    fun render(): String = """
        <header>
            <nav>
                <ul>
                    <li><a href="/">Home</a></li>
                    <li><a href="/blog">Blog</a></li>
                    <li><a href="/about">About</a></li>
                    <li><a href="/contact">Contact</a></li>
                </ul>
            </nav>
        </header>
    """.trimIndent()
}
