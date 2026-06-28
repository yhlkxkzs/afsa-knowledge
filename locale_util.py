# -*- coding: utf-8 -*-
"""Resolve API locale from query params or Accept-Language."""

from __future__ import annotations

from flask import Request

import i18n


def resolve_locale(request: Request) -> str:
    for key in ("locale", "lang", "language"):
        val = request.args.get(key)
        if val:
            return i18n.normalize_locale(val)
    header = request.headers.get("Accept-Language", "")
    if header:
        first = header.split(",")[0].strip()
        return i18n.normalize_locale(first)
    return i18n.DEFAULT_LOCALE
