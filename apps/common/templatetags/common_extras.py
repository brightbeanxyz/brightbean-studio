import json

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(is_safe=True)
def json_attr(value):
    """Serialize a Python value as a JSON literal safe to embed inside an
    HTML attribute (e.g. Alpine.js x-data).

    json.dumps produces JSON, then HTML-escape covers &, <, >, ", '. The
    browser HTML-decodes the attribute value before the JS engine parses
    it, so Alpine still sees valid JSON.

    Pass Python values (list/dict/None), NOT pre-serialized JSON strings.
    None and empty-string (Django's `string_if_invalid` fallback when a
    template variable like `post.tags` doesn't resolve) both become `[]`,
    matching the prior `|default:'[]'|safe` idiom.
    """
    if value is None or value == "":
        return mark_safe(escape("[]"))
    return mark_safe(escape(json.dumps(value, ensure_ascii=False, default=str)))
