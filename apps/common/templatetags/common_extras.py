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


@register.inclusion_tag("components/ui_select.html")
def ui_select(
    *,
    model,
    options,
    multiple=False,
    onchange="",
    placeholder="Select",
    value_field="id",
    label_field="",
    icon_field="",
):
    """A styled single/multi select dropdown (Alpine + checkbox/click list).

    A drop-in upgrade for a plain ``<select>`` in an Alpine/HTMX toolbar. The
    panel is ``position: fixed`` (anchored on open) so an ``overflow`` filter
    row can't clip it. Bind it to a property in the enclosing ``x-data`` scope:
    an **array** when ``multiple`` (empty = "all"), otherwise a **string**.

    Params:
      model        Alpine expression holding the selection, e.g. "filters.status".
      options      iterable of model instances, or ``{"value","label","icon"}`` dicts.
      multiple     checkbox multi-select (True) vs single-select (False).
      onchange     Alpine expression run after a change, e.g. "reloadTab()".
      placeholder  trigger label shown when nothing is selected.
      value_field / label_field / icon_field
                   attribute names read off model instances (ignored for dicts).
                   ``icon`` is treated as a platform code and rendered as a badge.
    """
    norm = []
    for o in options:
        if isinstance(o, dict):
            value, label, icon = o.get("value"), o.get("label"), o.get("icon")
        elif isinstance(o, (tuple, list)) and len(o) >= 2:
            # (value, label) pairs, e.g. Django `choices`.
            value, label, icon = o[0], o[1], None
        elif isinstance(o, str):
            value = label = o
            icon = None
        else:
            value = getattr(o, value_field, None)
            label = getattr(o, label_field) if label_field else str(o)
            icon = getattr(o, icon_field, None) if icon_field else None
        norm.append({"value": str(value) if value is not None else "", "label": label, "icon": icon})

    return {
        "model": model,
        "options": norm,
        # value+label only, for the Alpine trigger-label lookup in single mode.
        "options_js": [{"value": o["value"], "label": str(o["label"])} for o in norm],
        "multiple": bool(multiple),
        "onchange": onchange,
        "placeholder": placeholder,
    }
