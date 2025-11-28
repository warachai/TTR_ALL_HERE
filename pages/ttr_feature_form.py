import streamlit as st
import pandas as pd
import numpy as np

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

st.set_page_config(page_title="Operation / Stage / Task Hierarchy", layout="wide")

st.title("ตัวอย่าง Hierarchical Table: Operation > Stage > Task")

# -----------------------------
# 1) สร้างตัวอย่างข้อมูลหลายแถว
# -----------------------------
np.random.seed(1)

operations = ["OP_A", "OP_B", "OP_C"]

stages_by_op = {
    "OP_A": ["A1_Load", "A2_Process", "A3_Unload"],
    "OP_B": ["B1_Load", "B2_Process"],
    "OP_C": ["C1_Inspect", "C2_Pack"],
}

tasks_by_stage = {
    "A1_Load":   ["T001_LoadTray", "T002_ScanBarcode", "T003_CheckPosition"],
    "A2_Process":["T004_Align", "T005_Write", "T006_Verify"],
    "A3_Unload": ["T007_UnloadTray", "T008_BufferStore"],

    "B1_Load":   ["T101_Load", "T102_PreCheck"],
    "B2_Process":["T103_Test", "T104_Record", "T105_SaveResult"],

    "C1_Inspect":["T201_VisualCheck", "T202_Measure"],
    "C2_Pack":   ["T203_Pack", "T204_Label", "T205_Box"],
}

rows = []

for op in operations:
    # ค่าเฉพาะของ Operation (เช่น OEE, Yield, Score ฯลฯ) ไม่ใช่ผลรวม Stage
    op_kpi = np.random.randint(80, 101)  # 80–100

    for stg in stages_by_op[op]:
        # ค่าเฉพาะของ Stage ไม่ใช่ผลรวม Task
        stage_kpi = np.random.randint(70, 101)  # 70–100

        for task in tasks_by_stage[stg]:
            # ค่าระดับ Task (อันนี้จะต่างกันทุกแถว)
            task_kpi = np.random.randint(50, 101)
            qty = np.random.randint(10, 200)

            rows.append(
                {
                    "Operation": op,
                    "Stage": stg,
                    "Task": task,
                    "Op_KPI": op_kpi,        # ซ้ำกันทุกแถวใน Operation เดียวกัน
                    "Stage_KPI": stage_kpi,  # ซ้ำกันทุกแถวใน Stage เดียวกัน
                    "Task_KPI": task_kpi,    # เฉพาะ Task
                    "Qty": qty,              # ปริมาณ (เอาไว้ sum ได้)
                }
            )

df = pd.DataFrame(rows)

st.subheader("Raw Data (ตัวอย่าง)")
st.dataframe(df, use_container_width=True, height=250)

# -----------------------------
# 2) สร้าง GridOptions สำหรับ Hierarchical แสดงใน AgGrid
# -----------------------------
gb = GridOptionsBuilder.from_dataframe(df)

# default column config
gb.configure_default_column(
    resizable=True,
    sortable=True,
    filter=True,
)

# จัด Hierarchy: Operation > Stage > (แล้วคอลัมน์ Task เป็น leaf)
gb.configure_column("Operation", rowGroup=True, hide=False)
gb.configure_column("Stage", rowGroup=True, hide=False)

# ค่าเฉพาะของแต่ละระดับ -> ใช้ aggFunc = "first" เพื่อไม่ให้มันเอามาบวก
gb.configure_column(
    "Op_KPI",
    header_name="Op KPI (ไม่ใช่ผลรวม)",
    type=["numericColumn", "numberColumnFilter"],
    aggFunc="first",
    valueFormatter="x != null ? x.toFixed(0) : ''",
)

gb.configure_column(
    "Stage_KPI",
    header_name="Stage KPI (ไม่ใช่ผลรวม)",
    type=["numericColumn", "numberColumnFilter"],
    aggFunc="first",
    valueFormatter="x != null ? x.toFixed(0) : ''",
)

# ค่า Task_KPI อาจจะดูเป็นค่าเฉลี่ยเวลาระดับบน (แล้วแต่โจทย์)
gb.configure_column(
    "Task_KPI",
    header_name="Task KPI",
    type=["numericColumn", "numberColumnFilter"],
    aggFunc="avg",
    valueFormatter="x != null ? x.toFixed(1) : ''",
)

# Qty = ปริมาณ สามารถ sum ได้ปกติ
gb.configure_column(
    "Qty",
    header_name="Qty (Sum)",
    type=["numericColumn", "numberColumnFilter"],
    aggFunc="sum",
    valueFormatter="x != null ? x.toFixed(0) : ''",
)

# ตั้งค่า column สำหรับ group แสดงเป็น Hierarchy เดียว
grid_options = gb.build()
grid_options["autoGroupColumnDef"] = {
    "headerName": "Hierarchy",
    "minWidth": 280,
    "cellRendererParams": {
        "suppressCount": False,  # ถ้าไม่อยากโชว์จำนวนแถวใน group ให้เปลี่ยนเป็น True
    },
}

gb.configure_grid_options(
                groupDisplayType="multipleColumns",  # show group columns instead of hiding
                groupDefaultExpanded=0,              # 0 = collapsed, -1 = fully expanded
                animateRows=True,
                suppressAggFuncInHeader=False,
            )

st.subheader("Ag-Grid Hierarchical View")
auto_size_js = JsCode("""
function(e) {
    let gridApi = e.api;
    gridApi.sizeColumnsToFit();
}
""")
grid_response = AgGrid(
    df,
    gridOptions=grid_options,
    enable_enterprise_modules=True,
    update_mode=GridUpdateMode.NO_UPDATE,
    fit_columns_on_grid_load=False,
    height=19*32,

    allow_unsafe_jscode=True,
    custom_js=[
        JsCode("""
        function(e) {
            e.api.sizeColumnsToFit();
            e.api.gridOptions.api.gridOptionsWrapper.gridOptions.enableRangeSelection = true;
            e.api.gridOptions.api.gridOptionsWrapper.gridOptions.enableClipboard = true;
        }
        """)
    ],
    enableRangeSelection=True,
    enableRowSelection=True,
    rowSelection='multiple',
    suppressRowClickSelection=False,

)