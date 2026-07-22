"""
Feature / Task Tracking Pipeline (CSV + Python only)

Directory layout created by this script:

data/
  task_master.csv
  task_feature.csv
  feature_master.csv
  feature_target.csv
  product_master.csv
  task_annotation.csv
  validation_log.csv

summary/
  task_status_view_detail.csv
  task_status_aggregated.csv
  summary_tasks_by_date_product_config.csv
  summary_task_status_by_date_product_config.csv
  summary_task_status_pivot.csv
  summary_features_by_product_config.csv
  summary_validation.csv
  summary_feature_stage.csv
  summary_owner_workload.csv
  summary_blockers.csv
  summary_feature_coverage.csv

Workflows implemented (skeletons ready to extend):

1) Initialize blank CSVs with headers.
2) Import tasks from Excel into task_master (append-only).
3) Deduplicate tasks to latest per Task_ID.
4) Placeholder for mapping Tasks → Features (task_feature).
5) Compute Task status from feature_master + feature_target.
6) Generate summary CSVs (by date/product/config, coverage, etc.).

NOTE:
- Mapping logic is left as a placeholder (you will customize it).
- Validation runner is not implemented here, but CSV structure supports it.
"""

import os
from datetime import datetime
import pandas as pd

DATA_DIR = "data"
SUMMARY_DIR = "summary"


# ============================================================
# 0. Utilities
# ============================================================

def ensure_dirs():
    """Ensure data/ and summary/ directories exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SUMMARY_DIR, exist_ok=True)


def write_blank_csv_if_missing(path: str, columns):
    """
    Create a blank CSV with only a header row if it does not exist yet.
    If it exists, do nothing (we do NOT overwrite existing data).
    """
    if not os.path.exists(path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(path, index=False)
        print(f"Created blank CSV: {path}")
    else:
        print(f"CSV already exists, not touching: {path}")


# ============================================================
# 1. Initialize all CSV files with headers only
# ============================================================

def init_all_blank_csvs():
    """Initialize all core / optional / summary CSVs with header only."""
    ensure_dirs()

    # --- Core storage tables ---
    write_blank_csv_if_missing(
        os.path.join(DATA_DIR, "task_master.csv"),
        [
            "Task_ID",
            "Task_ID_Source",
            "Source",
            "Source_Unique_Key",
            "Import_Batch_TS",
            "Title",
            "Description",
            "Feature_Name_Raw",
            "Product_Code_Raw",
            "Config_Code_Raw",
            "Status_Raw",
            "Owner_Raw",
            "Updated_TS_Raw",
            "Signature",
            "Notes",
        ],
    )

    write_blank_csv_if_missing(
        os.path.join(DATA_DIR, "task_feature.csv"),
        [
            "Task_ID",
            "Feature_ID",
            "Mapping_Rule",      # e.g. "keyword", "dictionary", "manual", "new_feature", "needs_review"
            "Confidence_Score",
            "Mapping_TS",
            "Notes",
        ],
    )

    write_blank_csv_if_missing(
        os.path.join(DATA_DIR, "feature_master.csv"),
        [
            "Feature_ID",
            "Canonical_Name",
            "Parent_Feature_ID",
            "Version",
            "Stage",             # CANDIDATE / PLANNED / IN_DEV / IN_VALID / PRODUCTION / DEPRECATED
            "Owner",
            "Impact_Area",
            "Validation_Rule",   # base/common validation criteria
            "Notes",
        ],
    )

    write_blank_csv_if_missing(
        os.path.join(DATA_DIR, "feature_target.csv"),
        [
            "Feature_ID",
            "Product_Code",
            "Config_Code",
            "Is_Enabled",             # True / False
            "Stage_Override",         # optional per product/config
            "Rollout_Mode",           # e.g. "none", "pilot", "canary_10", "full"
            "Validation_Script",      # script name/path
            "Validation_Arguments",   # arguments for script
            "Validation_Expect",      # expectation used by script
            "Validation_Rule_Override",  # product-specific rule, optional
            "Feature_ON",             # detected from code/log (True/False)
            "Validation_Outcome",
            "Validation_TS",
            "Validation_Status",      # PASS / FAIL / SKIPPED / NO_DATA / UNKNOWN
            "Notes",
        ],
    )

    write_blank_csv_if_missing(
        os.path.join(DATA_DIR, "product_master.csv"),
        [
            "Product_Code",
            "Product_Name",
            "Config_Code",
            "Config_Description",
            "Product_Owner",
            "Notes",
        ],
    )

    # --- Optional manual/enrichment / history tables ---
    write_blank_csv_if_missing(
        os.path.join(DATA_DIR, "task_annotation.csv"),
        [
            "Task_ID",
            "Priority",
            "Comment",
            "Owner_Override",
            "Tags",
        ],
    )

    write_blank_csv_if_missing(
        os.path.join(DATA_DIR, "validation_log.csv"),
        [
            "Validation_Run_ID",
            "Feature_ID",
            "Product_Code",
            "Config_Code",
            "Script",
            "Arguments",
            "Outcome",
            "Status",
            "Timestamp",
            "Notes",
        ],
    )

    # --- Summary output tables (headers only) ---
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "task_status_view_detail.csv"),
        [],
    )
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "task_status_aggregated.csv"),
        [],
    )
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "summary_tasks_by_date_product_config.csv"),
        [],
    )
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "summary_task_status_by_date_product_config.csv"),
        [],
    )
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "summary_task_status_pivot.csv"),
        [],
    )
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "summary_features_by_product_config.csv"),
        [],
    )
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "summary_validation.csv"),
        [],
    )
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "summary_feature_stage.csv"),
        [],
    )
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "summary_owner_workload.csv"),
        [],
    )
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "summary_blockers.csv"),
        [],
    )
    write_blank_csv_if_missing(
        os.path.join(SUMMARY_DIR, "summary_feature_coverage.csv"),
        [],
    )


# ============================================================
# 2. Import tasks from Excel into task_master (append-only)
# ============================================================

def normalize_string(s: str) -> str:
    """Basic string normalization used for Signature and mapping."""
    if not isinstance(s, str):
        return ""
    return " ".join(s.strip().lower().split())


def import_tasks_from_excel(
    excel_path: str,
    source_name: str,
    id_col: str,
    title_col: str,
    desc_col: str = None,
    product_col: str = None,
    config_col: str = None,
    status_col: str = None,
    owner_col: str = None,
    updated_ts_col: str = None,
):
    """
    Import tasks from one Excel file and append to task_master.csv.

    - excel_path: path to the Excel file.
    - source_name: e.g. "JIRA", "SHEET1", "TRELLO".
    - id_col: column name in Excel that contains the source task ID (Task_ID_Source).
    - title_col: column name for task title.
    - desc_col: optional description column.
    - product_col, config_col, status_col, owner_col, updated_ts_col: optional.

    The function:
      - builds Source_Unique_Key = f"{source_name}|{Task_ID_Source}"
      - generates an internal Task_ID for new tasks (if not seen before)
      - appends rows to data/task_master.csv
    """
    ensure_dirs()
    task_master_path = os.path.join(DATA_DIR, "task_master.csv")
    if os.path.exists(task_master_path):
        task_master = pd.read_csv(task_master_path)
    else:
        task_master = pd.DataFrame(columns=[
            "Task_ID",
            "Task_ID_Source",
            "Source",
            "Source_Unique_Key",
            "Import_Batch_TS",
            "Title",
            "Description",
            "Feature_Name_Raw",
            "Product_Code_Raw",
            "Config_Code_Raw",
            "Status_Raw",
            "Owner_Raw",
            "Updated_TS_Raw",
            "Signature",
            "Notes",
        ])

    df = pd.read_excel(excel_path)

    # Build index from existing tasks: Source_Unique_Key -> Task_ID
    key_to_taskid = {}
    if not task_master.empty:
        for _, row in task_master.iterrows():
            suk = row.get("Source_Unique_Key")
            tid = row.get("Task_ID")
            if isinstance(suk, str) and isinstance(tid, str):
                key_to_taskid[suk] = tid

    def generate_new_task_id(existing_task_ids):
        # Task_ID pattern: T-000001, T-000002, ...
        nums = []
        for tid in existing_task_ids:
            if isinstance(tid, str) and tid.startswith("T-"):
                try:
                    nums.append(int(tid.split("-")[1]))
                except Exception:
                    pass
        nxt = (max(nums) + 1) if nums else 1
        return f"T-{nxt:06d}"

    existing_task_ids = set(task_master["Task_ID"]) if not task_master.empty else set()

    now_str = datetime.utcnow().isoformat(timespec="seconds")

    new_rows = []

    for _, row in df.iterrows():
        src_id = str(row[id_col]) if id_col in df.columns else ""
        if not src_id or src_id == "nan":
            # If no ID from source, we treat each row as its own "anonymous" task
            # You can customize this behavior.
            src_id = f"NOID-{_}"

        source_unique_key = f"{source_name}|{src_id}"

        if source_unique_key in key_to_taskid:
            task_id = key_to_taskid[source_unique_key]
        else:
            task_id = generate_new_task_id(existing_task_ids)
            existing_task_ids.add(task_id)
            key_to_taskid[source_unique_key] = task_id

        title = str(row[title_col]) if title_col in df.columns else ""
        desc = str(row[desc_col]) if desc_col and desc_col in df.columns else ""

        product_raw = str(row[product_col]) if product_col and product_col in df.columns else ""
        config_raw = str(row[config_col]) if config_col and config_col in df.columns else ""
        status_raw = str(row[status_col]) if status_col and status_col in df.columns else ""
        owner_raw = str(row[owner_col]) if owner_col and owner_col in df.columns else ""

        updated_ts_raw = ""
        if updated_ts_col and updated_ts_col in df.columns:
            val = row[updated_ts_col]
            if pd.notna(val):
                updated_ts_raw = str(val)

        signature = normalize_string(f"{title} {desc}")

        new_rows.append({
            "Task_ID": task_id,
            "Task_ID_Source": src_id,
            "Source": source_name,
            "Source_Unique_Key": source_unique_key,
            "Import_Batch_TS": now_str,
            "Title": title,
            "Description": desc,
            "Feature_Name_Raw": "",       # will be filled by mapping logic, or from Excel if you have such column
            "Product_Code_Raw": product_raw,
            "Config_Code_Raw": config_raw,
            "Status_Raw": status_raw,
            "Owner_Raw": owner_raw,
            "Updated_TS_Raw": updated_ts_raw,
            "Signature": signature,
            "Notes": "",
        })

    if new_rows:
        df_new = pd.DataFrame(new_rows)
        task_master = pd.concat([task_master, df_new], ignore_index=True)
        task_master.to_csv(task_master_path, index=False)
        print(f"Imported {len(new_rows)} rows from {excel_path} into task_master.csv")
    else:
        print("No new rows to import.")


# ============================================================
# 3. Dedup tasks to get latest version by Task_ID
# ============================================================

def get_latest_tasks():
    """Return latest row per Task_ID from task_master.csv."""
    task_master_path = os.path.join(DATA_DIR, "task_master.csv")
    if not os.path.exists(task_master_path):
        print("task_master.csv not found, returning empty DataFrame")
        return pd.DataFrame()

    df = pd.read_csv(task_master_path)
    if df.empty:
        return df

    # Sort by Import_Batch_TS so last row per Task_ID is the newest
    df_sorted = df.sort_values("Import_Batch_TS")
    latest = df_sorted.drop_duplicates(subset=["Task_ID"], keep="last").reset_index(drop=True)
    return latest


# ============================================================
# 4. Placeholder: mapping tasks → features (task_feature)
# ============================================================

def map_tasks_to_features():
    """
    Placeholder mapping logic.

    This function shows the structure only. You MUST customize how you:
      - decide which Feature_ID(s) each Task_ID should map to
      - create new Feature_IDs for new features
      - mark Mapping_Rule (e.g., "keyword", "manual", "new_feature", "needs_review").

    Current implementation does NOTHING (no auto mapping), just keeps existing task_feature.csv.
    """
    print("map_tasks_to_features(): placeholder – customize this with your real mapping logic")
    # In the future, you might:
    #   - load feature_master
    #   - for each task in latest tasks, inspect Title/Description
    #   - do fuzzy matching to Canonical_Name
    #   - create new Feature_ID if needed with Stage=CANDIDATE
    #   - write/append mapping rows into task_feature.csv
    # For now, we leave it as a manual process.


# ============================================================
# 5. Compute Task Status from features & targets
# ============================================================

def compute_task_status_views():
    """
    Build:
      - summary/task_status_view_detail.csv (Task × Feature × Product × Config)
      - summary/task_status_aggregated.csv  (Task aggregated status)

    Status is derived from:
      - feature_master.Stage
      - feature_target.Stage_Override, Is_Enabled, Validation_Status
      - mapping in task_feature
      - latest view of task_master
    """
    ensure_dirs()

    latest_tasks = get_latest_tasks()
    if latest_tasks.empty:
        print("No tasks in task_master; skipping status computation.")
        return

    # Load mapping and master tables
    task_feature_path = os.path.join(DATA_DIR, "task_feature.csv")
    feature_target_path = os.path.join(DATA_DIR, "feature_target.csv")
    feature_master_path = os.path.join(DATA_DIR, "feature_master.csv")
    task_annotation_path = os.path.join(DATA_DIR, "task_annotation.csv")

    task_feature = pd.read_csv(task_feature_path) if os.path.exists(task_feature_path) else pd.DataFrame()
    feature_target = pd.read_csv(feature_target_path) if os.path.exists(feature_target_path) else pd.DataFrame()
    feature_master = pd.read_csv(feature_master_path) if os.path.exists(feature_master_path) else pd.DataFrame()
    task_annotation = pd.read_csv(task_annotation_path) if os.path.exists(task_annotation_path) else pd.DataFrame()

    # Ensure Product_Code and Config_Code columns exist in latest_tasks
    # (you may map from Product_Code_Raw/Config_Code_Raw if needed)
    if "Product_Code" not in latest_tasks.columns:
        latest_tasks["Product_Code"] = latest_tasks.get("Product_Code_Raw", "")
    if "Config_Code" not in latest_tasks.columns:
        latest_tasks["Config_Code"] = latest_tasks.get("Config_Code_Raw", "")

    # 1) Join Task → Feature (task_feature)
    if not task_feature.empty:
        df = latest_tasks.merge(task_feature, on="Task_ID", how="left")
    else:
        # If no mapping, we still keep tasks
        df = latest_tasks.copy()
        df["Feature_ID"] = pd.NA
        df["Mapping_Rule"] = pd.NA
        df["Confidence_Score"] = pd.NA
        df["Mapping_TS"] = pd.NA

    # 2) Join Feature_Target on (Feature_ID, Product_Code, Config_Code)
    if not feature_target.empty:
        df = df.merge(
            feature_target,
            on=["Feature_ID", "Product_Code", "Config_Code"],
            how="left",
            suffixes=("", "_FT"),
        )

    # 3) Join global Stage from feature_master
    if not feature_master.empty:
        df = df.merge(
            feature_master[["Feature_ID", "Stage", "Owner", "Impact_Area"]],
            on="Feature_ID",
            how="left",
            suffixes=("", "_Feature"),
        )

    # 4) Join task_annotation (optional)
    if not task_annotation.empty:
        df = df.merge(task_annotation, on="Task_ID", how="left", suffixes=("", "_Annot"))

    # 5) Compute Effective Feature Stage
    def effective_stage(row):
        so = row.get("Stage_Override", "")
        global_stage = row.get("Stage", "")
        if isinstance(so, str) and so.strip():
            return so
        return global_stage

    df["Feature_Stage_Effective"] = df.apply(effective_stage, axis=1)

    # 6) Compute Task Status
    def compute_task_status(row):
        fid = row.get("Feature_ID")
        if pd.isna(fid) or (isinstance(fid, float) and pd.isna(fid)) or fid == "":
            return "UNMAPPED"

        stage = row.get("Feature_Stage_Effective")
        val_status = row.get("Validation_Status", "")
        is_enabled = row.get("Is_Enabled")

        # convert is_enabled to bool
        if isinstance(is_enabled, str):
            is_enabled = is_enabled.strip().lower() in ("true", "1", "yes")
        elif pd.isna(is_enabled):
            is_enabled = False

        # Feature-level state
        if stage == "DEPRECATED":
            return "DEPRECATED"

        # Validation-level
        if val_status == "FAIL":
            return "BLOCKED"
        if val_status == "PASS" and is_enabled:
            return "DONE"

        # Otherwise, mirror stage
        if isinstance(stage, str) and stage.strip():
            return stage

        return "UNKNOWN"

    df["Task_Status_Effective"] = df.apply(compute_task_status, axis=1)

    # Save detail view
    detail_path = os.path.join(SUMMARY_DIR, "task_status_view_detail.csv")
    df.to_csv(detail_path, index=False)
    print(f"Wrote detailed task status view: {detail_path}")

    # 7) Aggregate to one status per Task_ID
    priority = {
        "BLOCKED": 1,
        "IN_VALID": 2,
        "IN_DEV": 3,
        "PLANNED": 4,
        "CANDIDATE": 5,
        "PRODUCTION": 6,
        "DONE": 7,
        "DEPRECATED": 8,
        "UNMAPPED": 9,
        "UNKNOWN": 10,
    }
    df["Status_Priority"] = df["Task_Status_Effective"].map(priority).fillna(99)

    agg = (
        df.sort_values("Status_Priority")
          .groupby("Task_ID", as_index=False)
          .first()   # best status (lowest priority number)
    )

    task_status_agg = agg[["Task_ID", "Task_Status_Effective"]]
    agg_path = os.path.join(SUMMARY_DIR, "task_status_aggregated.csv")
    task_status_agg.to_csv(agg_path, index=False)
    print(f"Wrote aggregated task status view: {agg_path}")


# ============================================================
# 6. Generate summary CSVs (by date / product / config / coverage)
# ============================================================

def generate_summaries():
    """Generate all summary CSVs from the detailed task status view + master tables."""
    ensure_dirs()

    detail_path = os.path.join(SUMMARY_DIR, "task_status_view_detail.csv")
    if not os.path.exists(detail_path):
        print("No task_status_view_detail.csv found; run compute_task_status_views() first.")
        return

    df = pd.read_csv(detail_path)
    if df.empty:
        print("task_status_view_detail.csv is empty; skipping summaries.")
        return

    # Ensure Date column from Import_Batch_TS
    if "Date" not in df.columns:
        if "Import_Batch_TS" in df.columns:
            df["Date"] = pd.to_datetime(df["Import_Batch_TS"]).dt.date
        else:
            df["Date"] = pd.NaT

    # --- summary_tasks_by_date_product_config.csv ---
    g1 = (
        df.groupby(["Date", "Product_Code", "Config_Code"], dropna=False)
          .agg(
              Task_Count=("Task_ID", "nunique"),
              Feature_Count=("Feature_ID", "nunique"),
          )
          .reset_index()
    )
    g1_path = os.path.join(SUMMARY_DIR, "summary_tasks_by_date_product_config.csv")
    g1.to_csv(g1_path, index=False)
    print(f"Wrote {g1_path}")

    # --- summary_task_status_by_date_product_config.csv ---
    g2 = (
        df.groupby(
            ["Date", "Product_Code", "Config_Code", "Task_Status_Effective"],
            dropna=False,
        )
          .agg(Task_Count=("Task_ID", "nunique"))
          .reset_index()
    )
    g2_path = os.path.join(SUMMARY_DIR, "summary_task_status_by_date_product_config.csv")
    g2.to_csv(g2_path, index=False)
    print(f"Wrote {g2_path}")

    # Pivot version
    pivot = g2.pivot_table(
        index=["Date", "Product_Code", "Config_Code"],
        columns="Task_Status_Effective",
        values="Task_Count",
        fill_value=0,
    ).reset_index()
    pivot_path = os.path.join(SUMMARY_DIR, "summary_task_status_pivot.csv")
    pivot.to_csv(pivot_path, index=False)
    print(f"Wrote {pivot_path}")

    # --- summary_features_by_product_config.csv ---
    g3 = (
        df.groupby(["Product_Code", "Config_Code", "Feature_Stage_Effective"], dropna=False)
          .agg(Feature_Count=("Feature_ID", "nunique"))
          .reset_index()
    )
    g3_path = os.path.join(SUMMARY_DIR, "summary_features_by_product_config.csv")
    g3.to_csv(g3_path, index=False)
    print(f"Wrote {g3_path}")

    # --- summary_validation.csv ---
    if "Validation_Status" in df.columns:
        g4 = (
            df.groupby(["Feature_ID", "Product_Code", "Config_Code", "Validation_Status"], dropna=False)
              .agg(Count=("Task_ID", "nunique"))
              .reset_index()
        )
        g4_path = os.path.join(SUMMARY_DIR, "summary_validation.csv")
        g4.to_csv(g4_path, index=False)
        print(f"Wrote {g4_path}")

    # --- summary_feature_stage.csv ---
    if "Feature_Stage_Effective" in df.columns:
        g5 = (
            df.groupby(["Feature_Stage_Effective"], dropna=False)
              .agg(Feature_Count=("Feature_ID", "nunique"))
              .reset_index()
        )
        g5_path = os.path.join(SUMMARY_DIR, "summary_feature_stage.csv")
        g5.to_csv(g5_path, index=False)
        print(f"Wrote {g5_path}")

    # --- summary_owner_workload.csv ---
    # Use Owner from feature_master if available, else Owner_Raw
    owner_col = "Owner"
    if owner_col not in df.columns:
        owner_col = "Owner_Raw"
    g6 = (
        df.groupby([owner_col], dropna=False)
          .agg(
              Task_Count=("Task_ID", "nunique"),
              Feature_Count=("Feature_ID", "nunique"),
          )
          .reset_index()
    )
    g6_path = os.path.join(SUMMARY_DIR, "summary_owner_workload.csv")
    g6.to_csv(g6_path, index=False)
    print(f"Wrote {g6_path}")

    # --- summary_blockers.csv ---
    if "Task_Status_Effective" in df.columns:
        blockers = df[df["Task_Status_Effective"] == "BLOCKED"]
        if not blockers.empty:
            b = (
                blockers.groupby(
                    ["Product_Code", "Config_Code", "Feature_ID", "Validation_Status"],
                    dropna=False,
                )
                .agg(Task_Count=("Task_ID", "nunique"))
                .reset_index()
            )
            b_path = os.path.join(SUMMARY_DIR, "summary_blockers.csv")
            b.to_csv(b_path, index=False)
            print(f"Wrote {b_path}")
        else:
            print("No BLOCKED tasks; summary_blockers.csv not updated.")

    # --- summary_feature_coverage.csv ---
    generate_feature_coverage_summary()


# ============================================================
# 7. Feature coverage summary (applied vs not applied)
# ============================================================

def generate_feature_coverage_summary():
    """
    Build summary_feature_coverage.csv for all features:

    For each Feature_ID × Product_Code × Config_Code:
      - Coverage_Status : FULL / PLANNED / BLOCKED / NOT_PLANNED / UNKNOWN
    """
    product_master_path = os.path.join(DATA_DIR, "product_master.csv")
    feature_target_path = os.path.join(DATA_DIR, "feature_target.csv")
    feature_master_path = os.path.join(DATA_DIR, "feature_master.csv")

    if not (os.path.exists(product_master_path)
            and os.path.exists(feature_target_path)
            and os.path.exists(feature_master_path)):
        print("Missing product_master/feature_target/feature_master; skip coverage summary.")
        return

    pm = pd.read_csv(product_master_path)
    ft = pd.read_csv(feature_target_path)
    fm = pd.read_csv(feature_master_path)

    if pm.empty or ft.empty or fm.empty:
        print("product_master or feature_target or feature_master is empty; skip coverage summary.")
        return

    # Build all possible combos for all features:
    # Cross join: Feature_ID × (Product_Code, Config_Code)
    pm_small = pm[["Product_Code", "Config_Code"]].drop_duplicates()
    fm_small = fm[["Feature_ID"]].drop_duplicates()

    fm_small["key"] = 1
    pm_small["key"] = 1
    all_combos = fm_small.merge(pm_small, on="key").drop("key", axis=1)

    # Join with feature_target to see what's present
    ft_small = ft[
        [
            "Feature_ID",
            "Product_Code",
            "Config_Code",
            "Is_Enabled",
            "Stage_Override",
            "Validation_Status",
        ]
    ]
    merged = all_combos.merge(
        ft_small,
        on=["Feature_ID", "Product_Code", "Config_Code"],
        how="left",
        indicator=True,
    )

    def classify(row):
        if row["_merge"] == "left_only":
            return "NOT_PLANNED"
        # row exists in ft
        val_status = row.get("Validation_Status", "")
        is_enabled = row.get("Is_Enabled")
        stage_override = row.get("Stage_Override", "")

        # bool conversion
        if isinstance(is_enabled, str):
            is_enabled = is_enabled.strip().lower() in ("true", "1", "yes")
        elif pd.isna(is_enabled):
            is_enabled = False

        if val_status == "FAIL":
            return "BLOCKED"
        if is_enabled:
            return "FULL"
        if isinstance(stage_override, str) and stage_override.strip():
            return "PLANNED"
        return "UNKNOWN"

    merged["Coverage_Status"] = merged.apply(classify, axis=1)

    out_path = os.path.join(SUMMARY_DIR, "summary_feature_coverage.csv")
    merged[
        [
            "Feature_ID",
            "Product_Code",
            "Config_Code",
            "Coverage_Status",
        ]
    ].to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


# ============================================================
# 8. Example main entry
# ============================================================

if __name__ == "__main__":
    # 1) Create blank CSVs with headers if they don't exist
    init_all_blank_csvs()

    # 2) Example: import tasks from an Excel file (CUSTOMIZE OR COMMENT OUT)
    #    You can duplicate this call for multiple sources/files.
    #    Uncomment and edit columns according to your Excel structure.
    #
    # import_tasks_from_excel(
    #     excel_path="input_tasks.xlsx",
    #     source_name="SHEET1",
    #     id_col="ID",
    #     title_col="Title",
    #     desc_col="Description",
    #     product_col="Product",
    #     config_col="Config",
    #     status_col="Status",
    #     owner_col="Owner",
    #     updated_ts_col="Updated",
    # )

    # 3) Placeholder: task → feature mapping (you must implement)
    map_tasks_to_features()

    # 4) Compute task status detail + aggregated
    compute_task_status_views()

    # 5) Generate all summaries (by date/product/config, feature coverage, etc.)
    generate_summaries()

    print("Pipeline run completed.")
