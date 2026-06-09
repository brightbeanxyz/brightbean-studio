package com.brightbean.studio.infrastructure.config

data class StudioConfig(
    val jdbcUrl: String,
    val secretKey: String,
    val encryptionKeySalt: String,
    val serverPort: Int = 8080,
    val corsOrigins: List<String> = listOf("*"),
    val debug: Boolean = false,
) {
    companion object {
        fun fromEnv(env: Map<String, String>): StudioConfig {
            val databaseUrl = env["DATABASE_URL"]
                ?: throw IllegalArgumentException("DATABASE_URL environment variable is required")
            val secretKey = env["SECRET_KEY"]
                ?: throw IllegalArgumentException("SECRET_KEY environment variable is required")
            val encryptionKeySalt = env["ENCRYPTION_KEY_SALT"]
                ?: throw IllegalArgumentException("ENCRYPTION_KEY_SALT environment variable is required")

            return StudioConfig(
                jdbcUrl = parseDatabaseUrl(databaseUrl),
                secretKey = secretKey,
                encryptionKeySalt = encryptionKeySalt,
                serverPort = env["SERVER_PORT"]?.toIntOrNull() ?: 8080,
                corsOrigins = env["CORS_ORIGINS"]?.split(",")?.map { it.trim() } ?: listOf("*"),
                debug = env["DEBUG"]?.toBooleanStrictOrNull() ?: false,
            )
        }

        private fun parseDatabaseUrl(databaseUrl: String): String {
            val regex = Regex("^postgres(?:ql)?://([^:]+):([^@]+)@([^:/]+)(?::(\\d+))?/(.+)$")
            val match = regex.find(databaseUrl)
                ?: throw IllegalArgumentException("Invalid DATABASE_URL format: $databaseUrl")

            val (user, password, host, port, dbName) = match.destructured
            val portPart = if (port.isNotEmpty()) ":$port" else ""
            return "jdbc:postgresql://$host$portPart/$dbName?user=$user&password=$password"
        }

        fun fromSystemEnv(): StudioConfig = fromEnv(System.getenv())
    }
}
