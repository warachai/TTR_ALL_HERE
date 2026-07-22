import sys
import os
import ast
import pandas as pd

def get_dict_from_cmd():
    """
    Parse command line arguments for filter parameters.
    Example usage:
        python filter_csv.py "{'INPUT': 'input.csv', 'OUTPUT': 'output.csv', 'FILTER': 'column_name == \"value\"'}"
    """
    initial_dict = {'INPUT': '', 'OUTPUT': 'filtered_output.csv', 'FILTER': ''}
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        try:
            params = ast.literal_eval(arg)
            if isinstance(params, dict):
                return params
        except Exception as e:
            print(f"[filter_csv] Error parsing arguments: {e}")
            return initial_dict
    return initial_dict

def filter_csv(input_file, output_file, filter_condition):
    """
    Read a CSV file, apply a filter condition, and write the result to a new CSV file.
    
    Args:
        input_file (str): Path to the input CSV file.
        output_file (str): Path to the output CSV file.
        filter_condition (str): Pandas query string for filtering (e.g., "column_name == 'value'")
    
    Returns:
        int: Number of rows in the filtered result.
    """
    if not os.path.exists(input_file):
        print(f"[filter_csv] Error: Input file not found: {input_file}")
        return 0
    
    # Read the CSV file
    print(f"[filter_csv] Reading input file: {input_file}")
    df = pd.read_csv(input_file)
    print(f"[filter_csv] Total rows before filtering: {len(df)}")
    
    # Apply filter if provided
    if filter_condition:
        print(f"[filter_csv] Applying filter: {filter_condition}")
        try:
            df_filtered = df.query(filter_condition)
        except Exception as e:
            print(f"[filter_csv] Error applying filter: {e}")
            print(f"[filter_csv] Available columns: {', '.join(df.columns.tolist())}")
            return 0
    else:
        df_filtered = df
        print(f"[filter_csv] No filter condition provided, using all rows")
    
    print(f"[filter_csv] Total rows after filtering: {len(df_filtered)}")
    
    # Write to output CSV
    print(f"[filter_csv] Writing output file: {output_file}")
    df_filtered.to_csv(output_file, index=False)
    
    print(f"[filter_csv] Successfully filtered and saved data")
    print(f"[filter_csv] Columns: {', '.join(df_filtered.columns.tolist())}")
    
    return len(df_filtered)

if __name__ == "__main__":
    # Get parameters from command line or use defaults
    params = get_dict_from_cmd()
    
    # Example default parameters for testing
    if not params.get('INPUT'):
        params = {
            'INPUT': 'input.csv',
            'OUTPUT': 'filtered_output.csv',
            'FILTER': ''  # Example: "column_name > 100" or "status == 'active'"
        }
        print(f"[filter_csv] Using default parameters (modify as needed)")
    
    # Validate input file parameter
    if not params.get('INPUT'):
        print("[filter_csv] Error: INPUT file parameter is required")
        print("[filter_csv] Usage: python filter_csv.py \"{'INPUT': 'input.csv', 'OUTPUT': 'output.csv', 'FILTER': 'condition'}\"")
        sys.exit(1)
    
    # Run the filter operation
    result_count = filter_csv(
        input_file=params['INPUT'],
        output_file=params['OUTPUT'],
        filter_condition=params.get('FILTER', '')
    )
    
    if result_count > 0:
        print(f"[filter_csv] Operation completed successfully: {result_count} rows")
    else:
        print(f"[filter_csv] No rows matched the filter or an error occurred")
