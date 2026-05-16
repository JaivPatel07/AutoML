from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np
import os
import json

from app.cleaner.cleaner import SmartDataCleaner

router = APIRouter()

# Store the last uploaded file info
last_upload = {}

# Ensure directories exist once
os.makedirs("app/uploads", exist_ok=True)
os.makedirs("app/reports", exist_ok=True)

def read_df(file_path):
    """Load DataFrame from CSV or Excel"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        return pd.read_csv(file_path)
    elif ext in ['.xlsx', '.xls']:
        return pd.read_excel(file_path)
    raise ValueError(f"Unsupported file format: {ext}")

def to_json(df, limit=100):
    """Convert DF to JSON-safe list of records"""
    subset = df.head(limit).replace([np.inf, -np.inf], np.nan)
    # Using pandas' to_json is the most robust way to handle NaN/Inf for JSON compliance
    return json.loads(subset.to_json(orient="records"))

@router.post("/preview")
async def preview_file(file: UploadFile = File(...)):
    """Get a preview of the CSV file before cleaning"""
    file_path = f"app/uploads/{file.filename}"

    try:
        # Save the file to disk so it can be previewed and later cleaned
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        df = read_df(file_path)
        cleaner = SmartDataCleaner()
        cleaner.fit(df)
        last_upload["original_file"] = file_path
        last_upload["filename"] = file.filename

        # Identify outliers in preview data (row index 0-9)
        outliers_found = {}
        preview_df = df.head(10)
        for col, bounds in cleaner.outlier_bounds.items():
            lower, upper = bounds
            for i in range(len(preview_df)):
                val = preview_df.iloc[i][col]
                if pd.notnull(val) and (val < lower or val > upper):
                    idx_str = str(i)
                    if idx_str not in outliers_found:
                        outliers_found[idx_str] = []
                    outliers_found[idx_str].append(col)
        return {
            "filename": file.filename,
            "data": to_json(df, limit=10),
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "total_rows": len(df),
            "auto_flagged": cleaner.flagged_reasons,
            "outliers_found": outliers_found
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")

@router.post("/clean")
async def clean_file(
    file: UploadFile = File(...),
    drop_cols: str = Form(None),
    use_outliers: bool = Form(True),
    num_fill: str = Form("median"),
    cat_fill: str = Form("mode"),
    categorical_constant: str = Form("UNKNOWN"),
    outlier_thresh: float = Form(3.0)
):
    file_path = f"app/uploads/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    drop_list = []
    if drop_cols:
        drop_list = [c.strip() for c in drop_cols.split(',') if c.strip()]

    df = read_df(file_path)
    cleaner = SmartDataCleaner(
        drop_cols=drop_list,
        use_outliers=use_outliers,
        num_fill=num_fill,
        cat_fill=cat_fill,
        categorical_constant=categorical_constant,
        outlier_thresh=outlier_thresh
    )
    clean_df = cleaner.fit_transform(df)
    base_name = os.path.splitext(file.filename)[0]
    cleaned_file = f"app/uploads/cleaned_{base_name}.csv"
    clean_df.to_csv(cleaned_file, index=False)
    report_file = f"app/reports/{file.filename}_report.json"
    cleaner.export_report(report_file)
    
    last_upload["original_file"] = file_path
    last_upload["cleaned_file"] = cleaned_file
    last_upload["report_file"] = report_file
    last_upload["filename"] = file.filename
    
    return {
        "message": "Cleaning completed",
        "cleaned_file": cleaned_file,
        "report_file": report_file,
        "filename": file.filename
    }

@router.get("/view/original")
async def view_original():
    """Get original CSV data as JSON"""
    if "original_file" not in last_upload:
        raise HTTPException(status_code=404, detail="No file uploaded yet")
    
    try:
        df = read_df(last_upload["original_file"])

        outliers_found = {}
        if "report_file" in last_upload and os.path.exists(last_upload["report_file"]):
            with open(last_upload["report_file"], "r") as f:
                report = json.load(f)
            
            subset_df = df.head(100)
            outlier_info = report.get("outliers", {})
            for i in range(len(subset_df)):
                orig_idx = subset_df.index[i]
                for col, info in outlier_info.items():
                    if orig_idx in info.get("rows", []):
                        idx_str = str(i)
                        if idx_str not in outliers_found:
                            outliers_found[idx_str] = []
                        outliers_found[idx_str].append(col)

        return {
            "filename": last_upload["filename"],
            "data": to_json(df, limit=100),
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "total_rows": len(df),
            "outliers_found": outliers_found
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/view/cleaned")
async def view_cleaned():
    """Get cleaned CSV data as JSON"""
    if "cleaned_file" not in last_upload:
        raise HTTPException(status_code=404, detail="No cleaned file available")
    
    try:
        df = read_df(last_upload["cleaned_file"])

        return {
            "filename": last_upload["filename"],
            "data": to_json(df, limit=100),
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "total_rows": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/view/removed")
async def view_removed():
    """Get rows that were removed during cleaning (duplicates and outliers)"""
    if "original_file" not in last_upload or "report_file" not in last_upload:
        raise HTTPException(status_code=404, detail="No cleaning task performed yet")
    
    try:
        df_orig = read_df(last_upload["original_file"])
        
        # Load report to get indices
        with open(last_upload["report_file"], "r") as f:
            report = json.load(f)
        
        # Map indices to removal reasons
        reasons_map = {}
        
        for idx in report.get("duplicate_rows_removed", []):
            reasons_map[idx] = "Duplicate Row"
            
        for item in report.get("missing_value_rows_removed", []):
            col = item["column"]
            for idx in item["rows"]:
                msg = f"Missing value in {col}"
                reasons_map[idx] = f"{reasons_map[idx]}, {msg}" if idx in reasons_map else msg

        for col, outlier_info in report.get("outliers", {}).items():
            for idx in outlier_info.get("rows", []):
                msg = f"Outlier in {col}"
                reasons_map[idx] = f"{reasons_map[idx]}, {msg}" if idx in reasons_map else msg
            
        indices = list(reasons_map.keys())
        if not indices:
            return {"filename": last_upload["filename"], "data": [], "shape": [0, 0], "columns": [], "total_rows": 0}
            
        removed_df = df_orig.loc[indices].copy()
        # Prepend the Reason column
        removed_df.insert(0, "Removal Reason", [reasons_map[idx] for idx in indices])
        return {
            "filename": last_upload["filename"],
            "data": to_json(removed_df, limit=100),
            "shape": removed_df.shape,
            "columns": removed_df.columns.tolist(),
            "total_rows": len(removed_df)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/report")
async def get_report():
    """Get cleaning report"""
    if "report_file" not in last_upload:
        raise HTTPException(status_code=404, detail="No report available")
    
    try:
        with open(last_upload["report_file"], "r") as f:
            report = json.load(f)
        return report
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/download")
async def download_file():
    """Download the cleaned CSV file"""
    if "cleaned_file" not in last_upload:
        raise HTTPException(status_code=404, detail="No cleaned file available")
    
    try:
        return FileResponse(
            last_upload["cleaned_file"],
            media_type='text/csv',
            filename=f"cleaned_{os.path.splitext(last_upload['filename'])[0]}.csv"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))