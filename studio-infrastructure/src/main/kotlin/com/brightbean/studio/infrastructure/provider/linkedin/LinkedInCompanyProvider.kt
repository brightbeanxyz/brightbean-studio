package com.brightbean.studio.infrastructure.provider.linkedin

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.types.*
import com.google.gson.JsonParser

class LinkedInCompanyProvider : LinkedInProvider(platformType = PlatformType.LINKEDIN_COMPANY) {

    override val requiredScopes: List<String> = listOf(
        "r_basicprofile",
        "w_member_social",
        "w_organization_social",
        "r_organization_social",
        "rw_organization_admin",
    )

    data class CompanyPage(
        val id: String,
        val name: String,
        val handle: String,
        val logoUrl: String?,
    )

    fun getUserPages(account: SocialAccount): List<CompanyPage> {
        val accessToken = account.metadata["accessToken"] ?: return emptyList()
        val url = "$API_BASE/v2/organizationalEntityAcls" +
            "?q=roleAssignee&role=ADMINISTRATOR" +
            "&projection=(elements*(organizationalTarget~(id,localizedName,vanityName,logoV2(original~:playableStreams))))"

        val builder = java.net.http.HttpRequest.newBuilder()
            .uri(java.net.URI.create(url))
            .timeout(java.time.Duration.ofSeconds(30))
            .header("Authorization", "Bearer $accessToken")
        builder.header("LinkedIn-Version", "202604")
        builder.header("X-Restli-Protocol-Version", "2.0.0")
        val request = builder.GET().build()
        val response = httpClient.send(request, java.net.http.HttpResponse.BodyHandlers.ofString())
        if (response.statusCode() >= 400) {
            throw com.brightbean.studio.infrastructure.provider.exceptions.APIError(
                "LinkedIn getUserPages failed: ${response.body()}",
                platformType.name, response.statusCode(), response.body()
            )
        }
        val data = JsonParser.parseString(response.body()).asJsonObject
        val elements = data.getAsJsonArray("elements") ?: return emptyList()

        return elements.mapNotNull { element ->
            val el = element.asJsonObject
            val orgTarget = el.get("organizationalTarget")?.asString ?: return@mapNotNull null
            val org = el.getAsJsonObject("organizationalTarget~") ?: return@mapNotNull null
            val orgId = orgTarget.split(":").lastOrNull() ?: org.get("id")?.asString ?: return@mapNotNull null

            val logoUrl = runCatching {
                org.getAsJsonObject("logoV2")
                    .getAsJsonObject("original~")
                    .getAsJsonArray("elements")
                    .firstOrNull()?.asJsonObject
                    ?.getAsJsonArray("identifiers")?.firstOrNull()?.asJsonObject
                    ?.get("identifier")?.asString
            }.getOrNull()

            CompanyPage(
                id = orgId,
                name = org.get("localizedName")?.asString.orEmpty(),
                handle = org.get("vanityName")?.asString.orEmpty(),
                logoUrl = logoUrl,
            )
        }
    }
}
