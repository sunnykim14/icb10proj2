import ast
import sys
import os

def validate_streamlit_script(file_path):
    if not os.path.exists(file_path):
        return {"error": f"File {file_path} not found."}

    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    checks = {
        "has_streamlit_import": False,
        "has_sidebar": False,
        "has_caching": False,
        "has_kpi_metrics": False,
        "has_charts": False,
        "has_error_handling": False,
        "has_title": False
    }

    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "streamlit":
                    checks["has_streamlit_import"] = True
        if isinstance(node, ast.ImportFrom):
            if node.module == "streamlit":
                checks["has_streamlit_import"] = True

        # Check function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id in ["st", "streamlit"]:
                    func_name = node.func.attr
                    if func_name == "sidebar":
                        checks["has_sidebar"] = True
                    if func_name in ["cache_data", "cache_resource"]:
                        checks["has_caching"] = True
                    if func_name == "metric":
                        checks["has_kpi_metrics"] = True
                    if func_name in ["line_chart", "area_chart", "bar_chart", "plotly_chart", "pyplot", "altair_chart", "vega_lite_chart"]:
                        checks["has_charts"] = True
                    if func_name == "title":
                        checks["has_title"] = True
                    if func_name in ["error", "warning", "exception"]:
                        checks["has_error_handling"] = True
            
            # Check decorators for caching
            if hasattr(node, "decorator_list"):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Attribute):
                        if dec.attr in ["cache_data", "cache_resource"]:
                            checks["has_caching"] = True

    return checks

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_dashboard.py <script_path>")
        sys.exit(1)
    
    result = validate_streamlit_script(sys.argv[1])
    print(result)
