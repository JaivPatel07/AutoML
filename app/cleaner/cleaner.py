import pandas as pd
import numpy as np
import re
import json

def fix_missing_values(df):
    df = df.copy()
    missing_values = ["?", "NA", "N/A", "na","null", "NULL", "-", "--", ""]
    df.replace(missing_values, np.nan, inplace=True)
    df.replace(r"^\s*$", np.nan, regex=True, inplace=True)
    replaced_data = []
    for col in df.select_dtypes(include="object").columns:
        value_counts = df[col].value_counts(dropna=True)
        for value, count in value_counts.items():
            ratio = count / len(df)
            if (isinstance(value, str) and ratio > 0.4 and re.fullmatch(r"(.)\1+", value.strip().lower())):
                rows = df.index[df[col] == value].tolist()
                replaced_data.append({"column": col, "rows": rows, "old_value": value, "new_value": "NaN"})

                df[col] = df[col].replace(value, np.nan)

    return df, replaced_data


class SmartDataCleaner:

    def __init__(
        self,
        row_missing_limit=0.01,
        col_missing_limit=0.7,
        id_limit=0.95,
        name_limit=0.7,
        drop_cols=None,
        use_outliers=True,
        max_name_size=25,
        num_fill="median",
        cat_fill="mode",
        categorical_constant="UNKNOWN",
        outlier_thresh=3.0
    ):

        self.row_missing_limit = row_missing_limit
        self.col_missing_limit = col_missing_limit
        self.id_limit = id_limit
        self.name_limit = name_limit
        self.max_name_size = max_name_size
        self.drop_cols = drop_cols if drop_cols is not None else []
        self.use_outliers = use_outliers
        self.num_fill = num_fill
        self.cat_fill = cat_fill
        self.categorical_constant = categorical_constant
        self.outlier_thresh = outlier_thresh

        self.remove_columns = []
        self.flagged_reasons = {}
        self.outlier_bounds = {}
        self.logs = []

    def fit(self, df):
        df, _ = fix_missing_values(df)

        for col in df.columns:
            n_unique = df[col].nunique(dropna=True)
            unique_ratio = n_unique / len(df)
            
            if n_unique <= 1:
                self.remove_columns.append(col)
                self.flagged_reasons[col] = "Constant Value"
                self.logs.append(f"Dropped constant column: {col}")
            elif df[col].isnull().mean() > self.col_missing_limit:
                self.remove_columns.append(col)
                self.flagged_reasons[col] = f"High Nulls (>{self.col_missing_limit*100}%)"
                self.logs.append(f"Dropped high-null column: {col}")
            elif (df[col].dtype == "object" and unique_ratio > self.id_limit):
                self.remove_columns.append(col)
                self.flagged_reasons[col] = "Unique ID"
                self.logs.append(f"Dropped ID-like column: {col}")
            elif df[col].dtype == "object":
                avg_length = df[col].dropna().astype(str).str.len().mean()
                if (unique_ratio > self.name_limit and avg_length < self.max_name_size):
                    self.remove_columns.append(col)
                    self.flagged_reasons[col] = "Names/Text"
                    self.logs.append(f"Dropped text-heavy column: {col}")
        
        # Calculate outlier bounds for all numeric columns
        self.outlier_bounds = {}
        for col in df.select_dtypes(include=np.number).columns:
            if col not in self.remove_columns:
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                self.outlier_bounds[col] = (
                    q1 - self.outlier_thresh * iqr,
                    q3 + self.outlier_thresh * iqr
                )

        for col in self.drop_cols:
            if col in df.columns and col not in self.remove_columns:
                self.remove_columns.append(col)
                self.logs.append(f"User requested removal of column: {col}")
        return self
    def transform(self, df):
        memory_before = (df.memory_usage(deep=True).sum() / 1024**2)
        df, replaced_data = fix_missing_values(df)
        report = {
            "initial_shape": df.shape,
            "final_shape": None,
            "removed_columns": [],
            "duplicate_rows_removed": df[df.duplicated()].index.tolist(),
            "missing_value_rows_removed": [],
            "missing_before": df.isnull().sum().to_dict(),
            "missing_after": {},
            "filled_values": {},
            "replaced_values": replaced_data,
            "flagged_reasons": self.flagged_reasons,
            "outlier_removal_enabled": self.use_outliers,
            "outliers": {},
            "memory_before_mb": round(memory_before, 2) if np.isfinite(memory_before) else 0.0,
            "memory_after_mb": None,
            "logs": self.logs
        }
        df = df.drop_duplicates()
        df.drop(
            columns=self.remove_columns,
            inplace=True,
            errors="ignore"
        )

        report["removed_columns"] = self.remove_columns

        for col in df.columns:
            missing_ratio = df[col].isnull().mean()
            if 0 < missing_ratio < self.row_missing_limit:
                dropped_indices = df[df[col].isnull()].index.tolist()
                report["missing_value_rows_removed"].append({"column": col, "rows": dropped_indices})
                df = df.dropna(subset=[col])
                self.logs.append(f"Rows removed from {col} due to low missing value ratio")

            elif pd.api.types.is_numeric_dtype(df[col]):
                if self.num_fill == "mean":
                    fill_value = df[col].mean()
                    method_name = "mean"
                elif self.num_fill == "zero":
                    fill_value = 0
                    method_name = "zero"
                else:
                    fill_value = df[col].median()
                    method_name = "median"
                
                fill_count = df[col].isnull().sum()
                df[col] = df[col].fillna(fill_value)
                report["filled_values"][col] = {
                    "method": method_name,
                    "count": int(fill_count)
                }

            else:
                if self.cat_fill == "constant":
                    fill_value = self.categorical_constant if self.categorical_constant else "UNKNOWN"
                    method_name = "constant"
                else:
                    if not df[col].mode().empty:
                        fill_value = df[col].mode()[0]
                    else:
                        fill_value = "UNKNOWN"
                    method_name = "mode"

                fill_count = df[col].isnull().sum()
                df[col] = df[col].fillna(fill_value)
                report["filled_values"][col] = {
                    "method": method_name,
                    "count": int(fill_count)
                }

        if self.use_outliers:
            all_outlier_indices = set()
            for col, bounds in self.outlier_bounds.items():
                if col not in df.columns:
                    continue
                
                lower, upper = bounds
                mask = (df[col] < lower) | (df[col] > upper)
                outlier_rows = df.index[mask].tolist()

                if outlier_rows:
                    report["outliers"][col] = {
                        "count": len(outlier_rows),
                        "rows": outlier_rows
                    }
                    all_outlier_indices.update(outlier_rows)
                    self.logs.append(f"Outliers detected and flagged in column: {col} (count: {len(outlier_rows)})")
            
            if all_outlier_indices:
                df = df.drop(index=list(all_outlier_indices), errors='ignore')

        for col in df.select_dtypes(include=["int64"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="integer")

        for col in df.select_dtypes(include=["float64"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="float")

        memory_after = (
            df.memory_usage(deep=True).sum() / 1024**2
        )

        report["memory_after_mb"] = round(memory_after, 2) if np.isfinite(memory_after) else 0.0

        report["missing_after"] = (
            df.isnull().sum().to_dict()
        )

        report["final_shape"] = df.shape

        self.report = report

        return df

    def fit_transform(self, df):
        return self.fit(df).transform(df)

    def get_report(self):
        return self.report

    def export_report(self, file_name="cleaning_report.json"):
        with open(file_name, "w") as file:
            json.dump(self.report, file, indent=4)