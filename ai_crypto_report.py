# ai_crypto_report.py
# -*- coding: utf-8 -*-
"""
AI Crypto Report — ежедневный отчёт по криптовалютам (упрощённо, без tenacity).
Зависимости: requests, openai (praw — опционально).
"""

import os
import time
import math
import textwrap
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

# ---- OpenAI (новый клиент) ----
try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    _openai_client = None

# ---- Reddit (опционально) ----
REDDIT_ENABLED = False
try:
    import praw  # optional
    REDDIT_ENABLED = True
except Exception:
    REDDIT_ENABLED = False

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
HEADERS = {"Accept": "application/json"}

# ---------------------------
# Простой HTTP с повторами
# ---------------------------
def _get(url: str, params: Optional[Dict[str, Any]] = None, retries: int = 3, timeout: int = 12) -> Any:
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, par
