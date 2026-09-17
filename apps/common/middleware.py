"""
Middleware to allow Fly.io internal health checks through ALLOWED_HOSTS validation.

Fly.io health checks hit the app via internal IPs (172.19.x.x) which are not in
ALLOWED_HOSTS. This middleware adds those IPs to the allowed hosts for health
check requests only.
"""

import re

from django.conf import settings
from django.http import HttpResponseForbidden

FLY_INTERNAL_IP_PATTERN = re.compile(r"^172\.19\.\d+\.\d+$")
HEALTH_CHECK_PATHS = {"/health/", "/healthz/", "/ready/"}


class FlyHealthCheckMiddleware:
    """
    Allow Fly.io internal health checks to bypass ALLOWED_HOSTS restriction.

    Fly.io's internal load balancer sends health checks from internal IPs
    (172.19.x.x) which are not in ALLOWED_HOSTS. This middleware checks if
    the request is a health check from a Fly internal IP and allows it through.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if this is a health check request from Fly internal IP
        # Use META directly to avoid triggering DisallowedHost in get_host()
        host_header = request.META.get("HTTP_HOST", "").split(":")[0]
        path = request.path

        if path in HEALTH_CHECK_PATHS and FLY_INTERNAL_IP_PATTERN.match(host_header):
            # Temporarily add the host to ALLOWED_HOSTS for this request
            # This is safe because it's only for known health check paths
            # from known internal IP range
            original_allowed = settings.ALLOWED_HOSTS
            if host_header not in original_allowed:
                settings.ALLOWED_HOSTS = list(original_allowed) + [host_header]

        response = self.get_response(request)

        # Restore original ALLOWED_HOSTS
        if path in HEALTH_CHECK_PATHS and FLY_INTERNAL_IP_PATTERN.match(host_header):
            settings.ALLOWED_HOSTS = original_allowed

        return response