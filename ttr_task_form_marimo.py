import marimo

__generated_with = "0.17.8"
app = marimo.App()


@app.cell
def _():
    import pandas as pd
    import config
    import marimo as mo
    return config, mo, pd


@app.cell
def _(config, pd):
    # Load data
    current_tasks = pd.read_csv(config.TASK_MASTER_FILE)
    current_tasks = current_tasks[current_tasks['Improvement_Type'] == "TTR"]
    current_tasks = current_tasks[current_tasks['Program'].isin(["DORADO", "MARLIN", "MARLIN BP", "SUMMIT"])]

    # Add Select column
    if "Select" not in current_tasks.columns:
        current_tasks.insert(0, "Select", False)

    sub_task = pd.read_csv(config.JIRA_FILE_PATH)

    return current_tasks, sub_task


@app.cell
def _(mo):
    mo.md("""
    # Task View
    """)
    return


@app.cell
def _(mo):
    # Filter controls
    program_filter = mo.ui.multiselect(
        options=["DORADO", "MARLIN", "MARLIN BP", "SUMMIT"],
        label="Select Product(s)"
    )

    filter_text = mo.ui.text(
        label="Filter Text Box",
        placeholder="Search in all columns..."
    )

    search_mode = mo.ui.radio(
        options=["OR", "AND"],
        label="Search Mode",
        value="OR"
    )

    return filter_text, program_filter, search_mode


@app.cell
def _(current_tasks, filter_text, program_filter, search_mode):
    # Apply program filter
    if program_filter.value:
        filtered_tasks = current_tasks[current_tasks['Program'].isin(program_filter.value)]
    else:
        filtered_tasks = current_tasks.copy()

    # Apply text filter
    if filter_text.value:
        search_terms = filter_text.value.strip().split()

        if search_mode.value == "OR":
            mask = filtered_tasks.astype(str).apply(
                lambda row: any(
                    row.str.contains(term, case=False, na=False).any() 
                    for term in search_terms
                ), 
                axis=1
            )
        else:  # AND
            mask = filtered_tasks.astype(str).apply(
                lambda row: all(
                    row.str.contains(term, case=False, na=False).any() 
                    for term in search_terms
                ), 
                axis=1
            )

        filtered_tasks = filtered_tasks[mask]

    return (filtered_tasks,)


@app.cell
def _(filtered_tasks, mo):
    # Display editable dataframe
    edited_tasks = mo.ui.dataframe(
        filtered_tasks,
        selection="single-row"
    )

    return (edited_tasks,)


@app.cell
def _(edited_tasks):
    # Get selected row
    selected_rows = edited_tasks.value

    if selected_rows is not None and len(selected_rows) > 0:
        selected_index = selected_rows.index[0]
        selected_task_id = selected_rows.iloc[0]["Task_ID"]
    else:
        selected_task_id = None

    return (selected_task_id,)


@app.cell
def _(selected_task_id, sub_task):
    # Filter sub-tasks based on selected task
    if selected_task_id is not None:
        filtered = sub_task[sub_task["Key"] == selected_task_id]
    else:
        filtered = sub_task

    return (filtered,)


@app.cell
def _(filtered, mo):
    mo.md(f"## Sub Tasks ({len(filtered)} rows)")
    mo.ui.dataframe(filtered)
    return


if __name__ == "__main__":
    app.run()
