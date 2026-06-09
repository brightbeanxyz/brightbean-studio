package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.web.api.dto.AuthResponse
import com.brightbean.studio.web.api.dto.LoginRequest
import com.brightbean.studio.web.api.dto.RegisterRequest
import com.brightbean.studio.web.api.dto.UserResponse
import com.google.gson.Gson
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader

class AuthApi(
    private val authUseCases: AuthUseCases,
    private val gson: Gson = Gson(),
) : HttpHandler {

    override fun handle(exchange: HttpExchange) {
        val response = when (exchange.requestMethod) {
            "POST" -> handlePost(exchange)
            else -> Response(405, """{"error":"Method not allowed"}""")
        }
        sendJson(exchange, response)
    }

    private fun handlePost(exchange: HttpExchange): Response {
        val path = exchange.requestURI.path
        return when {
            path.endsWith("/register") -> handleRegister(exchange)
            path.endsWith("/login") -> handleLogin(exchange)
            else -> Response(404, """{"error":"Not found"}""")
        }
    }

    private fun handleRegister(exchange: HttpExchange): Response {
        val request = parseBody(exchange, RegisterRequest::class.java)
            ?: return Response(400, """{"error":"Invalid request body"}""")
        val result = authUseCases.register(request.email, request.name, request.password)
        return if (result.isSuccess) {
            val user = result.getOrThrow()
            Response(201, gson.toJson(mapOf("user" to user.toResponse())))
        } else {
            Response(409, gson.toJson(mapOf("error" to (result.exceptionOrNull()?.message ?: "Registration failed"))))
        }
    }

    private fun handleLogin(exchange: HttpExchange): Response {
        val request = parseBody(exchange, LoginRequest::class.java)
            ?: return Response(400, """{"error":"Invalid request body"}""")
        val result = authUseCases.login(request.email, request.password)
        return if (result.isSuccess) {
            val token = result.getOrThrow()
            val user = authUseCases.verifySession(token)
            Response(200, gson.toJson(AuthResponse(token, user!!.toResponse())))
        } else {
            Response(401, gson.toJson(mapOf("error" to "Invalid credentials")))
        }
    }

    private fun <T> parseBody(exchange: HttpExchange, clazz: Class<T>): T? {
        return try {
            val reader = InputStreamReader(exchange.requestBody, Charsets.UTF_8)
            gson.fromJson(reader, clazz)
        } catch (_: Exception) {
            null
        }
    }

    private fun sendJson(exchange: HttpExchange, response: Response) {
        val bytes = response.body.toByteArray(Charsets.UTF_8)
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(response.statusCode, bytes.size.toLong())
        exchange.responseBody.use { os -> os.write(bytes) }
    }

    private fun com.brightbean.studio.domain.model.User.toResponse() = UserResponse(
        id = id, email = email, name = name, avatar = avatar,
    )

    private data class Response(val statusCode: Int, val body: String)
}
