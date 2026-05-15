from fastapi import APIRouter, UploadFile, File
import pandas as pd
import os

from app.cleaner.cleaner import SmartDataCleaner

router = APIRouter()

@router.post("/clean")
async def clean_file(file: UploadFile = File(...)):
    os.makedirs("app/uploads", exist_ok=True)
    os.makedirs("app/reports", exist_ok=True)
    file_path = f"app/uploads/{file.filename}"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    df = pd.read_csv(file_path)
    cleaner = SmartDataCleaner()
    clean_df = cleaner.fit_transform(df)
    cleaned_file = f"app/uploads/cleaned_{file.filename}"
    clean_df.to_csv(cleaned_file, index=False)
    report_file = f"app/reports/{file.filename}_report.json"
    cleaner.export_report(report_file)
    
    return {
        "message": "Cleaning completed",
        "cleaned_file": cleaned_file,
        "report_file": report_file
    }