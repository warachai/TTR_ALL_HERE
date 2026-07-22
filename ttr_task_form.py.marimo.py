import marimo

__generated_with = "0.1.0"
app = marimo.App()


@app.cell
def __():
    import pandas as pd
    import config
    return pd, config


@app.cell
def __(pd, config):
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
def __(mo):
    mo.md("# Task View")


@app.cell
def __(mo):
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
    
    return program_filter, filter_text, search_mode


@app.cell
def __(current_tasks, program_filter, filter_text, search_mode):
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
    
    return filtered_tasks


@app.cell
def __(mo, filtered_tasks):
    # Display editable dataframe
    edited_tasks = mo.ui.dataframe(
        filtered_tasks,
        selection="single-row"
    )
    
    return edited_tasks


@app.cell
def __(edited_tasks):
    # Get selected row
    selected_rows = edited_tasks.value
    
    if selected_rows is not None and len(selected_rows) > 0:
        selected_index = selected_rows.index[0]
        selected_task_id = selected_rows.iloc[0]["Task_ID"]
    else:
        selected_task_id = None
    
    return selected_task_id, selected_rows


@app.cell
def __(sub_task, selected_task_id):
    # Filter sub-tasks based on selected task
    if selected_task_id is not None:
        filtered = sub_task[sub_task["Key"] == selected_task_id]
    else:
        filtered = sub_task
    
    return filtered


@app.cell
def __(mo, filtered):
    mo.md(f"## Sub Tasks ({len(filtered)} rows)")
    mo.ui.dataframe(filtered)


if __name__ == "__main__":
    app.run()
