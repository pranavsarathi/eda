#!/usr/bin/env python3
"""
Bundle EDA Python sources and example library for client-side Pyodide WASM execution.
"""
import os
import json
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
EDA_DIR = os.path.join(BASE_DIR, "eda")

sys.path.insert(0, BASE_DIR)
from examples.library import EXAMPLES

def main():
    print("Bundling EDA workstation for static / GitHub Pages deployment...")
    
    # 1. Export static/examples.json and static/js/examples_data.js
    examples_json_path = os.path.join(STATIC_DIR, "examples.json")
    with open(examples_json_path, "w", encoding="utf-8") as f:
        json.dump(EXAMPLES, f, indent=2)
    print(f"  [+] Wrote {examples_json_path}")
    
    examples_js_path = os.path.join(STATIC_DIR, "js", "examples_data.js")
    with open(examples_js_path, "w", encoding="utf-8") as f:
        f.write("// Canonical EDA Example Library for zero-backend static hosting\n")
        f.write("window.EDA_EXAMPLES = " + json.dumps(EXAMPLES, indent=2) + ";\n")
    print(f"  [+] Wrote {examples_js_path}")

    # 2. Bundle eda/ modules into static/js/eda_bundle.js
    eda_files = {}
    for root, dirs, files in os.walk(EDA_DIR):
        for file in files:
            if file.endswith(".py"):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, BASE_DIR).replace("\\", "/")
                with open(abs_path, "r", encoding="utf-8") as fp:
                    eda_files[rel_path] = fp.read()

    # Ensure __init__.py exists for each directory
    for root, dirs, files in os.walk(EDA_DIR):
        rel_dir = os.path.relpath(root, BASE_DIR).replace("\\", "/")
        init_path = f"{rel_dir}/__init__.py"
        if init_path not in eda_files:
            eda_files[init_path] = "# package init\n"

    eda_bundle_path = os.path.join(STATIC_DIR, "js", "eda_bundle.js")
    with open(eda_bundle_path, "w", encoding="utf-8") as f:
        f.write("// Auto-generated in-browser EDA Python source bundle for Pyodide\n")
        f.write("window.EDA_PYTHON_FILES = " + json.dumps(eda_files, indent=2) + ";\n")
    print(f"  [+] Wrote {len(eda_files)} files to {eda_bundle_path}")

    # 3. Synchronize with root directory for GitHub Pages root deployment
    import shutil
    shutil.copy(os.path.join(STATIC_DIR, "index.html"), os.path.join(BASE_DIR, "index.html"))
    shutil.copy(examples_json_path, os.path.join(BASE_DIR, "examples.json"))
    
    root_css = os.path.join(BASE_DIR, "css")
    if os.path.exists(root_css): shutil.rmtree(root_css)
    shutil.copytree(os.path.join(STATIC_DIR, "css"), root_css)
    
    root_js = os.path.join(BASE_DIR, "js")
    if os.path.exists(root_js): shutil.rmtree(root_js)
    shutil.copytree(os.path.join(STATIC_DIR, "js"), root_js)

    with open(os.path.join(BASE_DIR, ".nojekyll"), "w") as f:
        f.write("")
    print("  [+] Synchronized static assets and .nojekyll to project root")

    print("Bundling completed successfully.")

if __name__ == "__main__":
    main()
