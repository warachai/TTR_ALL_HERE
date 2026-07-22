"""Utility for logging site/page accesses.

Writes a CSV (defined by config.ACCESS_LOG_FILE) with columns:
timestamp,page,user,session_id,query_params,ip

Functions:
  log_access(page_name): append a single access record.
  read_access_log(): return DataFrame of log (empty if none).
  summarize_access(by="user"): grouped counts.
"""

from __future__ import annotations

import os
import csv
import uuid
from datetime import datetime
from typing import Dict

import pandas as pd
import streamlit as st

import config

# Explicit module exports
__all__ = ["log_access", "read_access_log", "summarize_access"]

LOG_COLUMNS = ["timestamp", "page", "user", "session_id", "query_params", "ip"]

def _get_user() -> str:
    # Prefer explicit query param ?user=NAME
    params = st.query_params
    raw = params.get("user", [])
    if raw:
        if isinstance(raw, list):
            return str(raw[0])
        return str(raw)
    # Fallback to OS user env
    for k in ("USERNAME", "USER", "LOGNAME"):
        v = os.getenv(k)
        if v:
            return v
    return "anonymous"

def _get_session_id() -> str:
    if "_access_session_id" not in st.session_state:
        st.session_state["_access_session_id"] = str(uuid.uuid4())
    return st.session_state["_access_session_id"]

def _serialize_params(params: Dict[str, str]) -> str:
    try:
        return "&".join(f"{k}={v}" for k, v in params.items())
    except Exception:
        return ""

def log_access(page_name: str) -> None:
    """Append an access record for the current page.

    Safe no-op if file write fails.
    """
    ts = datetime.utcnow().isoformat(timespec="seconds")
    user = _get_user()
    sess = _get_session_id()
    params = st.query_params
    q_serialized = _serialize_params(params)
    ip = ""  # Streamlit cloud / local - IP not directly exposed; left blank for now.

    row = [ts, page_name, user, sess, q_serialized, ip]
    path = config.ACCESS_LOG_FILE
    try:
        new_file = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(LOG_COLUMNS)
            writer.writerow(row)
    except Exception as e:
        # Avoid breaking the UI due to logging issues
        st.debug(f"Access log write failed: {e}")

def read_access_log() -> pd.DataFrame:
    path = config.ACCESS_LOG_FILE
    if not os.path.exists(path):
        return pd.DataFrame(columns=LOG_COLUMNS)
    try:
        df = pd.read_csv(path)
        # If required columns missing, attempt recovery
        if not set(LOG_COLUMNS).issubset(df.columns):
            try:
                df2 = pd.read_csv(path, header=None)
                if len(df2.columns) == len(LOG_COLUMNS):
                    df2.columns = LOG_COLUMNS
                    # remove accidental header row duplication
                    df2 = df2[df2['timestamp'] != 'timestamp']
                    return df2
            except Exception:
                pass
            # Add any missing columns with blank values
            for col in LOG_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            df = df[LOG_COLUMNS]
        # Clean any duplicated header rows present as data
        df = df[df['timestamp'] != 'timestamp']
        return df
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=LOG_COLUMNS)
    except Exception:
        return pd.DataFrame(columns=LOG_COLUMNS)

def summarize_access(by: str = "user") -> pd.DataFrame:
    df = read_access_log()
    if df.empty:
        return pd.DataFrame(columns=[by, "count"])
    if by not in df.columns:
        raise ValueError(f"Invalid summarize key: {by}")
    return (df.groupby(by).size().reset_index(name="count").sort_values("count", ascending=False))
