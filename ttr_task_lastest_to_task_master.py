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
from ttr_task_staging_import import ensure_data_dir
DATA_DIR = config.OUTPUT_RAW_DIR
TASK_STAGING_FILE = config.STAGING_FILE_PATH
TASK_LATEST_FILE = config.LATEST_FILE_PATH
TASK_CURRENT_FILE = config.TASK_CURRENT_FILE_PATH

def sync_task_latest_to_task_master():
    """
    Upsert data from task_latest.csv into task_master.csv.

    - One row per Business_Key in task_master.
    - If Business_Key is new  -> create new Task_ID and insert.
    - If Business_Key exists -> update existing row (status, title, owner, etc.).
    """
    ensure_data_dir()

    if not os.path.exists(TASK_LATEST_FILE):
        print("task_latest.csv not found; run build_task_latest() first.")
        return

    latest = pd.read_csv(TASK_LATEST_FILE)
    if latest.empty:
        print("task_latest.csv is empty; nothing to sync.")
        return

    # load or create task_master
    if os.path.exists(config.TASK_MASTER_FILE):
        tm = pd.read_csv(config.TASK_MASTER_FILE)
    else:
        tm = pd.read_csv(config.TASK_LATEST_FILE)


    tm.to_csv(config.TASK_MASTER_FILE, index=False)
    print(f"Synced task_latest -> task_master ({len(latest)} latest rows, {len(tm)} total tasks).")

def update_product_master_from_task_master():
    """
    Ensure product_master.csv contains at least one row per Program in task_master.

    - Product_Code = Program
    - Product_Name = Program (you can refine later)
    - Config_Code  = "" (no config detail yet)
    """
    ensure_data_dir()

    if not os.path.exists(config.TASK_MASTER_FILE):
        print("task_master.csv not found; run sync_task_latest_to_task_master() first.")
        return

    tm = pd.read_csv(config.TASK_MASTER_FILE)
    if tm.empty:
        print("task_master.csv is empty; no products to update.")
        return

    if os.path.exists(config.PRODUCT_MASTER_FILE):
        pm = pd.read_csv(config.PRODUCT_MASTER_FILE)
    else:
        pm = pd.DataFrame(columns=[
            "Product_Code",
            "Product_Name",
            "Config_Code",
            "Config_Description",
            "Product_Owner",
            "Notes",
        ])

    existing_keys = set(
        (row.get("Product_Code", ""), row.get("Config_Code", ""))
        for _, row in pm.iterrows()
    )

    new_rows = []
    for prog in sorted(tm["Program"].dropna().unique()):
        pcode = str(prog).strip()
        if not pcode:
            continue
        key = (pcode, "")  # no config yet
        if key in existing_keys:
            continue
        existing_keys.add(key)
        new_rows.append({
            "Product_Code":       pcode,
            "Product_Name":       pcode,
            "Config_Code":        "",
            "Config_Description": "",
            "Product_Owner":      "",
            "Notes":              "auto-created from task_master",
        })

    if new_rows:
        pm = pd.concat([pm, pd.DataFrame(new_rows)], ignore_index=True)
        pm.to_csv(config.PRODUCT_MASTER_FILE, index=False)
        print(f"Added {len(new_rows)} new product(s) to product_master.")
    else:
        print("No new products to add to product_master.")

def _generate_new_feature_id(existing_ids):
    """Feature_ID pattern: FT-001, FT-002, ..."""
    nums = []
    for fid in existing_ids:
        if isinstance(fid, str) and fid.startswith("FT-"):
            try:
                nums.append(int(fid.split("-")[1]))
            except Exception:
                pass
    nxt = (max(nums) + 1) if nums else 1
    return f"FT-{nxt:03d}"


def update_feature_master_and_task_feature():
    """
    Use task_master to:
      - ensure feature_master has entries for all Improvement_Type values
      - map each Task_ID to its Feature_ID in task_feature.csv

    Rules:
      - Canonical_Name from Improvement_Type (fallback: Title).
      - If Canonical_Name not in feature_master -> new Feature_ID with Stage=CANDIDATE.
      - task_feature row per (Task_ID, Feature_ID) with Mapping_Rule="improvement_type".
    """
    ensure_data_dir()

    if not os.path.exists(config.TASK_MASTER_FILE):
        print("task_master.csv not found; run sync_task_latest_to_task_master() first.")
        return

    tm = pd.read_csv(config.TASK_MASTER_FILE)
    if tm.empty:
        print("task_master.csv is empty; nothing to map.")
        return

    # Load feature_master
    if os.path.exists(config.FEATURE_MASTER_FILE):
        df_featureMaster = pd.read_csv(config.FEATURE_MASTER_FILE)
    else:
        df_featureMaster = pd.DataFrame(columns=[
            "Feature_ID",
            "Canonical_Name",
            "Parent_Feature_ID",
            "Version",
            "Stage",
            "Owner",
            "Impact_Area",
            "Validation_Rule",
            "Notes",
        ])

    # Load task_feature mapping
    if os.path.exists(config.TASK_FEATURE_FILE):
        tf = pd.read_csv(config.TASK_FEATURE_FILE)
    else:
        tf = pd.DataFrame(columns=[
            "Task_ID",
            "Feature_ID",
            "Mapping_Rule",
            "Confidence_Score",
            "Mapping_TS",
            "Notes",
        ])


    existing_feature_ids = set(df_featureMaster["Feature_ID"]) if not df_featureMaster.empty else set()

    # For task_feature, we avoid duplicate mapping
    existing_tf_keys = set(
        (row.get("Task_ID", ""), row.get("Feature_ID", ""))
        for _, row in tf.iterrows()
    )

    now_str = datetime.utcnow().isoformat(timespec="seconds")

    new_fm_rows = []
    new_tf_rows = []

    for _, row in tm.iterrows():
        task_id = row.get("Task_ID")
        if not isinstance(task_id, str):
            continue

        raw_ft = str(row.get("Improvement_Type", "") or "").strip()
        if not raw_ft:
            raw_ft = str(row.get("Title", "") or "").strip()
        if not raw_ft:
            continue

        cname_norm = raw_ft.lower()

        # Ensure feature exists
        if cname_norm in cname_to_fid:
            fid = cname_to_fid[cname_norm]
        else:
            fid = _generate_new_feature_id(existing_feature_ids)
            existing_feature_ids.add(fid)
            cname_to_fid[cname_norm] = fid
            new_fm_rows.append({
                "Feature_ID":        fid,
                "Canonical_Name":    raw_ft,
                "Parent_Feature_ID": "",
                "Version":           "v1",
                "Stage":             "CANDIDATE",
                "Owner":             "",
                "Impact_Area":       "",
                "Validation_Rule":   "",
                "Notes":             "auto-created from Improvement_Type in task_master",
            })

        # Create task_feature mapping if not exists
        tf_key = (task_id, fid)
        if tf_key in existing_tf_keys:
            continue
        existing_tf_keys.add(tf_key)
        new_tf_rows.append({
            "Task_ID":          task_id,
            "Feature_ID":       fid,
            "Mapping_Rule":     "improvement_type",
            "Confidence_Score": "",
            "Mapping_TS":       now_str,
            "Notes":            "",
        })

    # Append new feature_master rows
    if new_fm_rows:
        df_featureMaster = pd.concat([df_featureMaster, pd.DataFrame(new_fm_rows)], ignore_index=True)
        # remove helper column if exists
        if "Canonical_Name_norm" in df_featureMaster.columns:
            df_featureMaster = df_featureMaster.drop(columns=["Canonical_Name_norm"])
        df_featureMaster.to_csv(config.FEATURE_MASTER_FILE, index=False)
        print(f"Added {len(new_fm_rows)} features to feature_master.")
    else:
        # remove helper if no changes but we added earlier
        if "Canonical_Name_norm" in df_featureMaster.columns:
            df_featureMaster = df_featureMaster.drop(columns=["Canonical_Name_norm"])
            df_featureMaster.to_csv(config.FEATURE_MASTER_FILE, index=False)
        print("No new features to add to feature_master.")

    # Append new task_feature rows
    if new_tf_rows:
        tf = pd.concat([tf, pd.DataFrame(new_tf_rows)], ignore_index=True)
        tf.to_csv(config.TASK_FEATURE_FILE, index=False)
        print(f"Added {len(new_tf_rows)} task-feature mappings.")
    else:
        print("No new task-feature mappings to add.")

if __name__ == "__main__":


    # 3) Sync into master-level tables
    sync_task_latest_to_task_master()
    update_product_master_from_task_master()
    update_feature_master_and_task_feature()

    # print("Sync from task_latest to task_master/product_master/feature_master completed.")
