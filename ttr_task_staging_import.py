"""
Task Staging + Latest View

Workflow:
1) task_current (Excel/CSV snapshot) -> append into task_staging.csv (history, no duplicates)
2) Derive task_latest.csv = latest row per task (Business_Key)

Business_Key = Source | Program | Task_ID

Rules when importing from task_current into task_staging:
- If no existing row for Business_Key -> NEW -> append.
- If existing row and new Date_Time <= existing Date_Time -> STALE -> skip.
- If existing row and new Date_Time > existing Date_Time:
    * If Status/User_Name/Task_Name/Improvement_Type all same -> DUPLICATE -> skip.
    * Else -> MODIFIED -> append.

Result:
- task_staging keeps only meaningful NEW/MODIFIED snapshots (history).
- task_latest is always the most recent state per task.
"""

import os
from datetime import datetime
import pandas as pd
import config
DATA_DIR = config.OUTPUT_RAW_DIR
TASK_STAGING_FILE = config.STAGING_FILE_PATH
TASK_LATEST_FILE = config.LATEST_FILE_PATH
TASK_CURRENT_FILE = config.TASK_CURRENT_FILE_PATH


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def normalize_string(s):
    """Normalize for comparison (case & extra spaces)."""
    if not isinstance(s, str):
        s = "" if pd.isna(s) else str(s)
    return " ".join(s.strip().lower().split())


def build_business_key(source, program, task_id):
    return f"{normalize_string(source)}|{normalize_string(program)}|{normalize_string(task_id)}"


# -----------------------------------------------------------
# 1) Initialize empty staging file (only once)
# -----------------------------------------------------------

def init_task_staging():
    """Create an empty task_staging.csv with header, if not exists."""
    ensure_data_dir()
    if os.path.exists(TASK_STAGING_FILE):
        print(f"{TASK_STAGING_FILE} already exists, not overwriting.")
        return

    cols = [
        "Source",
        "Program",
        "Task_ID",
        "Status",
        "User_Name",
        "Date_Time",
        "Task_Name",
        "Improvement_Type",
        # control / metadata
        "Business_Key",
        "Import_Batch_ID",
        "Import_TS",
        "Change_Type",        # NEW / MODIFIED
        "Snapshot_Signature", # optional, for debug
        "Notes",
        "Reviewed_Flag",      # <-- user editable, e.g. "Y" when reviewed
    ]
    df = pd.DataFrame(columns=cols)
    df.to_csv(TASK_STAGING_FILE, index=False)
    print(f"Created empty staging file: {TASK_STAGING_FILE}")


# -----------------------------------------------------------
# 2) Import task_current -> task_staging (history)
# -----------------------------------------------------------

def import_task_current_to_staging(
    task_current_path: str,
    import_batch_id: str = None,
    file_type: str = "excel",
):
    """
    Import 'task_current' snapshot into task_staging.csv.

    task_current must have columns:
      Source, Program, Task_ID, Status, User_Name, Date_Time, Task_Name, Improvement_Type

    Args:
      task_current_path: path to Excel or CSV file.
      import_batch_id: optional ID for this batch (e.g. '2025-11-16-01').
                       If None, we generate one from current timestamp.
      file_type: 'excel' or 'csv'.
    """
    ensure_data_dir()

    # ---- load existing staging ----
    if os.path.exists(TASK_STAGING_FILE):
        staging = pd.read_csv(TASK_STAGING_FILE)
    else:
        init_task_staging()
        staging = pd.read_csv(TASK_STAGING_FILE)

    # build dict of latest existing row per Business_Key
    if staging.empty:
        latest_by_key = {}
    else:
        # convert Date_Time to comparable type
        staging["_DateTimeSort"] = pd.to_datetime(staging["Date_Time"], errors="coerce")
        staging_sorted = staging.sort_values("_DateTimeSort")
        latest_rows = staging_sorted.drop_duplicates(subset=["Business_Key"], keep="last")
        latest_by_key = {
            row["Business_Key"]: row
            for _, row in latest_rows.iterrows()
        }

    # ---- load task_current snapshot ----
    if file_type.lower() == "excel":
        cur = pd.read_excel(task_current_path)
    else:
        cur = pd.read_csv(task_current_path)

    required_cols = [
        "Source", "Program", "Task_ID",
        "Status", "User_Name", "Date_Time",
        "Task_Name", "Improvement_Type"
    ]
    missing = [c for c in required_cols if c not in cur.columns]
    if missing:
        raise ValueError(f"task_current missing columns: {missing}")

    if import_batch_id is None:
        import_batch_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    import_ts = datetime.utcnow().isoformat(timespec="seconds")

    new_rows = []
    cnt_new = 0
    cnt_mod = 0
    cnt_stale = 0
    cnt_dup = 0

    for _, row in cur.iterrows():
        src = row["Source"]
        prog = row["Program"]
        tid = row["Task_ID"]
        status = row["Status"]
        user = row["User_Name"]
        dt_raw = row["Date_Time"]
        tname = row["Task_Name"]
        itype = row["Improvement_Type"]

        # build Business_Key
        bkey = build_business_key(src, prog, tid)

        # parse Date_Time for ordering
        try:
            dt_new = pd.to_datetime(dt_raw)
        except Exception:
            # if can't parse, treat as "now" (or decide other rule)
            dt_new = pd.to_datetime("now")

        # snapshot signature for quick content comparison
        sig = "|".join([
            normalize_string(status),
            normalize_string(user),
            normalize_string(tname),
            normalize_string(itype),
        ])

        existing = latest_by_key.get(bkey)

        change_type = None
        notes = ""

        if existing is None:
            # no history for this task yet
            change_type = "NEW"
            cnt_new += 1
        else:
            # we have an existing latest snapshot
            try:
                dt_old = pd.to_datetime(existing["Date_Time"])
            except Exception:
                dt_old = pd.to_datetime("1970-01-01")

            if dt_new <= dt_old:
                # older or equal timestamp -> stale
                cnt_stale += 1
                continue  # skip

            # compare content (status, user, task_name, improvement_type)
            sig_old = existing.get("Snapshot_Signature", "")
            if not isinstance(sig_old, str):
                sig_old = str(sig_old)

            if sig == sig_old:
                # nothing truly changed
                cnt_dup += 1
                continue  # skip
            else:
                change_type = "MODIFIED"
                cnt_mod += 1

        # append new snapshot into staging
        new_rows.append({
            "Source": src,
            "Program": prog,
            "Task_ID": tid,
            "Status": status,
            "User_Name": user,
            "Date_Time": dt_new.isoformat(),
            "Task_Name": tname,
            "Improvement_Type": itype,
            "Business_Key": bkey,
            "Import_Batch_ID": import_batch_id,
            "Import_TS": import_ts,
            "Change_Type": change_type,
            "Snapshot_Signature": sig,
            "Notes": notes,
            "Reviewed_Flag": "",   # default blank; user can change later   
        })

    if new_rows:
        df_new = pd.DataFrame(new_rows)
        staging_updated = pd.concat([staging, df_new], ignore_index=True)
        staging_updated.to_csv(TASK_STAGING_FILE, index=False)
        print(f"Imported from {task_current_path}: "
              f"{cnt_new} NEW, {cnt_mod} MODIFIED, "
              f"{cnt_stale} STALE skipped, {cnt_dup} DUPLICATE skipped.")
    else:
        print(f"No NEW or MODIFIED rows to import from {task_current_path}.")

    return


# -----------------------------------------------------------
# 3) Build task_latest view from task_staging
# -----------------------------------------------------------
def build_task_latest(mode: str = "all"):
    """
    Create task_latest.csv = latest row per Business_Key from task_staging.csv.

    mode:
      - "all"      : ignore Reviewed_Flag, use all rows
      - "later"    : only rows where Reviewed_Flag is "" (blank) or "Later"
      - "reviewed" : only rows where Reviewed_Flag indicates reviewed 
                     (Y / DONE / OK / REVIEWED, case-insensitive)

    Output columns:
      Business_Key, Source, Program, Task_ID, Status, User_Name,
      Date_Time, Task_Name, Improvement_Type, Change_Type,
      Import_Batch_ID, Import_TS, Reviewed_Flag
    """
    ensure_data_dir()

    if not os.path.exists(TASK_STAGING_FILE):
        print("No task_staging.csv found. Run import_task_current_to_staging() first.")
        return

    staging = pd.read_csv(TASK_STAGING_FILE)
    if staging.empty:
        print("task_staging.csv is empty, nothing to build.")
        return

    if "Reviewed_Flag" not in staging.columns:
        # For "all" we can still work; for others we can't filter.
        if mode in ("later", "reviewed"):
            print("Reviewed_Flag column not found in staging; cannot filter for mode =", mode)
            return
        else:
            print("Reviewed_Flag not found; mode='all' will proceed without filter.")

    staging = staging[staging["Improvement_Type"].isin(["", "TTR"])] #Filter only TTR
    before = len(staging)

    # ---------- Apply mode filter ----------
    if "Reviewed_Flag" in staging.columns:
        staging["Reviewed_Flag"] = staging["Reviewed_Flag"].fillna("").astype(str)
        rf_upper = staging["Reviewed_Flag"].str.upper()
    else:
        rf_upper = None  # not used in 'all' mode when column missing

    if mode == "all":
        # no filtering
        pass

    elif mode == "later":
        # keep only blank or "Later"
        staging = staging[
            staging["Reviewed_Flag"].isin(["", "Later"])
        ]

    elif mode == "reviewed":
        # define what counts as reviewed (you can extend this set)
        reviewed_values = {"Y", "DONE", "OK", "REVIEWED"}
        staging = staging[rf_upper.isin(reviewed_values)]

    else:
        print(f"Unknown mode '{mode}'. Use 'all', 'later', or 'reviewed'.")
        return

    after = len(staging)
    print(f"build_task_latest(mode='{mode}'): {before} → {after} rows after filter")

    if staging.empty:
        print("No rows match filter; task_latest.csv not written.")
        return

    # ---------- Build latest by Business_Key ----------
    staging["_DateTimeSort"] = pd.to_datetime(staging["Date_Time"], errors="coerce")
    staging["_ImportSort"] = pd.to_datetime(staging["Import_TS"], errors="coerce")

    staging_sorted = staging.sort_values(["_DateTimeSort", "_ImportSort"])
    latest = staging_sorted.drop_duplicates(subset=["Business_Key"], keep="last")

    cols_out = [
        "Business_Key",
        "Source",
        "Program",
        "Task_ID",
        "Status",
        "User_Name",
        "Date_Time",
        "Task_Name",
        "Improvement_Type",
        "Change_Type",
        "Import_Batch_ID",
        "Import_TS",
        "Reviewed_Flag",
    ]
    cols_out = [c for c in cols_out if c in latest.columns]

    latest_out = latest[cols_out].reset_index(drop=True)
    latest_out.to_csv(TASK_LATEST_FILE, index=False)

    print(f"Created task_latest.csv (mode='{mode}', rows={len(latest_out)}): {TASK_LATEST_FILE}")

# -----------------------------------------------------------
# 4) Example usage
# -----------------------------------------------------------

if __name__ == "__main__":
    # 1) Ensure staging exists
    init_task_staging()

    # 2) Import from a current snapshot file
    #    Change this path and file_type to match your actual file.

    # Example for CSV:
    import_task_current_to_staging(TASK_CURRENT_FILE, file_type="csv")
    #


    # 3) Build latest view
    build_task_latest()

    print("Done. Edit __main__ section to run your actual imports.")
