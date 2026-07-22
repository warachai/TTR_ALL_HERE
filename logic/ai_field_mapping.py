from pathlib import Path
from datetime import datetime
import os
import pandas as pd

from config import AI_MAPPING_FILE_NAME


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAPPING_FILE =AI_MAPPING_FILE_NAME

MAPPING_COLUMNS = [
    "section",
    "ai_name",
    "user_define_name",
    "status",
    "last_seen",
    "sample_value"
]


DEFAULT_MAPPING = [
    # section, ai_name, user_define_name, status, sample_value

    # anomalies
    ["anomalies", "operation", "operation", "active", "PRE2"],
    ["anomalies", "op", "operation", "active", "PRE2"],
    ["anomalies", "process", "operation", "active", "PRE2"],

    ["anomalies", "state", "state", "active", "PCBA_SCRN"],
    ["anomalies", "state_name", "state", "active", "PCBA_SCRN"],
    ["anomalies", "test", "state", "active", "PCBA_SCRN"],
    ["anomalies", "test_name", "state", "active", "PCBA_SCRN"],
    ["anomalies", "step", "state", "active", "PCBA_SCRN"],

    ["anomalies", "issue", "message", "active", "Large TT Difference"],
    ["anomalies", "note", "message", "active", "Large TT Difference"],
    ["anomalies", "message", "message", "active", "Large TT Difference"],
    ["anomalies", "comment", "message", "active", "Large TT Difference"],
    ["anomalies", "description", "message", "active", "Large TT Difference"],
    ["anomalies", "observation", "message", "active", "Large TT Difference"],

    ["anomalies", "difference", "difference", "active", "1.39"],
    ["anomalies", "diff", "difference", "active", "1.39"],
    ["anomalies", "delta", "difference", "active", "1.39"],
    ["anomalies", "change", "difference", "active", "1.39"],
    ["anomalies", "diff_TestTime(hrs)", "difference", "active", "1.39"],
    ["anomalies", "test_time_diff", "difference", "active", "1.39"],

    # findings
    ["findings", "operation", "operation", "active", "FNC2"],
    ["findings", "op", "operation", "active", "FNC2"],
    ["findings", "process", "operation", "active", "FNC2"],

    ["findings", "state", "state", "active", "ZAP"],
    ["findings", "state_name", "state", "active", "ZAP"],
    ["findings", "test", "state", "active", "ZAP"],
    ["findings", "test_name", "state", "active", "ZAP"],

    ["findings", "issue", "message", "active", "Significant reduction"],
    ["findings", "note", "message", "active", "Significant reduction"],
    ["findings", "message", "message", "active", "Significant reduction"],
    ["findings", "comment", "message", "active", "Significant reduction"],
    ["findings", "description", "message", "active", "Significant reduction"],

    ["findings", "difference", "difference", "active", "1.86"],
    ["findings", "diff", "difference", "active", "1.86"],
    ["findings", "delta", "difference", "active", "1.86"],
    ["findings", "change", "difference", "active", "1.86"],
]


def today_text():
    return datetime.now().strftime("%Y-%m-%d")


def init_mapping_file(mapping_file: str = MAPPING_FILE):
    """
    Create mapping CSV if it does not exist.
    """

    if os.path.exists(mapping_file):
        return

    rows = []
    today = today_text()

    for section, ai_name, user_define_name, status, sample_value in DEFAULT_MAPPING:
        rows.append({
            "section": section,
            "ai_name": ai_name,
            "user_define_name": user_define_name,
            "status": status,
            "last_seen": today,
            "sample_value": sample_value
        })

    df = pd.DataFrame(rows, columns=MAPPING_COLUMNS)

    df.to_csv(
        mapping_file,
        index=False,
        encoding="utf-8-sig"
    )


def load_mapping(mapping_file: str = MAPPING_FILE) -> pd.DataFrame:
    """
    Load mapping CSV.
    """

    init_mapping_file(mapping_file)

    df = pd.read_csv(
        mapping_file,
        encoding="utf-8-sig"
    )

    # Ensure all required columns exist
    for col in MAPPING_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[MAPPING_COLUMNS]


def save_mapping(df: pd.DataFrame, mapping_file: str = MAPPING_FILE):
    """
    Save mapping CSV.
    """
    os.makedirs(os.path.dirname(mapping_file), exist_ok=True)

    df[MAPPING_COLUMNS].to_csv(
        mapping_file,
        index=False,
        encoding="utf-8-sig"
    )


def register_ai_fields(
    section: str,
    item: dict,
    mapping_file: str = MAPPING_FILE
):
    """
    Check AI returned fields.
    If field not found in CSV, append as pending.

    Example:
        item = {
            "operation": "PRE2",
            "state_name": "PCBA_SCRN",
            "severity": "high"
        }

    If severity not found, append:
        anomalies,severity,,pending,2026-07-11,high
    """

    if not isinstance(item, dict):
        return

    df = load_mapping(mapping_file)
    today = today_text()

    updated = False

    for ai_name, value in item.items():

        mask = (
            (df["section"].astype(str) == section)
            &
            (df["ai_name"].astype(str) == ai_name)
        )

        if mask.any():
            df.loc[mask, "last_seen"] = today
            df.loc[mask, "sample_value"] = str(value)[:300]
            continue

        new_row = {
            "section": section,
            "ai_name": ai_name,
            "user_define_name": "",
            "status": "pending",
            "last_seen": today,
            "sample_value": str(value)[:300]
        }

        df = pd.concat(
            [df, pd.DataFrame([new_row])],
            ignore_index=True
        )

        updated = True

    if updated:
        save_mapping(df, mapping_file)
    else:
        save_mapping(df, mapping_file)


def get_user_defined_value(
    section: str,
    item: dict,
    user_define_name: str,
    default=None,
    mapping_file: str = MAPPING_FILE
):
    """
    Get value from AI item using mapping CSV.

    Example:
        CSV:
            anomalies,state_name,state,active

        item:
            {"state_name": "PCBA_SCRN"}

        get_user_defined_value(item, "anomalies", "state")
        => "PCBA_SCRN"
    """

    if not isinstance(item, dict):
        return default

    df = load_mapping(mapping_file)

    active_mapping = df[
        (df["section"].astype(str) == section)
        &
        (df["user_define_name"].astype(str) == user_define_name)
        &
        (df["status"].astype(str) == "active")
    ]

    ai_names = active_mapping["ai_name"].dropna().astype(str).tolist()

    for ai_name in ai_names:
        if ai_name in item and item[ai_name] not in [None, ""]:
            return item[ai_name]

    return default


def normalize_item(
    section: str,
    item: dict,
    fields=None,
    mapping_file: str = MAPPING_FILE
) -> dict:
    """
    Normalize one AI object to user-defined fields.

    Default output:
        operation
        state
        message
        difference

    Unknown fields will be appended into CSV as pending.
    """

    if fields is None:
        fields = [
            "operation",
            "state",
            "message",
            "difference"
        ]

    register_ai_fields(
        section=section,
        item=item,
        mapping_file=mapping_file
    )

    normalized = {}

    for field in fields:
        normalized[field] = get_user_defined_value(
            section=section,
            item=item,
            user_define_name=field,
            default=None,
            mapping_file=mapping_file
        )

    normalized["raw"] = item

    return normalized


def normalize_list(
    section: str,
    items,
    fields=None,
    mapping_file: str = MAPPING_FILE
) -> list:
    """
    Normalize list of AI dictionaries.
    """

    if not isinstance(items, list):
        return []

    normalized_rows = []

    for item in items:

        if isinstance(item, dict):
            normalized_rows.append(
                normalize_item(
                    section=section,
                    item=item,
                    fields=fields,
                    mapping_file=mapping_file
                )
            )

        else:
            normalized_rows.append({
                "message": str(item),
                "raw": item
            })

    return normalized_rows