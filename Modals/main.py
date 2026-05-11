import pandas as pd
import numpy as np
import re
import json
from sklearn.base import BaseEstimator, TransformerMixin


def detect_and_fix_missing(df: pd.DataFrame):
    df = df.copy()

    missing_patterns = [
        "?", " ?", "NA", "N/A", "na",
        "null", "NULL", "-", "--", ""
    ]
    replace_log = []
    for pattern in missing_patterns:
        mask = df.isin([pattern])

        for col in df.columns:
            rows = df.index[mask[col]].tolist()

            if rows:
                replace_log.append({
                    "column": col,
                    "rows": rows,
                    "old_value": pattern,
                    "new_value": np.nan
                })

    df.replace(missing_patterns, np.nan, inplace=True)
    df.replace(r"^\s*$", np.nan, regex=True, inplace=True)

    for col in df.columns:
        if df[col].dtype == "object":

            counts = df[col].value_counts(dropna=True)
            total_rows = len(df)

            for value, count in counts.items():
                ratio = count / total_rows

                if isinstance(value, str):
                    clean_value = value.strip().lower()

                    if ratio > 0.4 and re.fullmatch(r"(.)\1+", clean_value):

                        rows = df.index[df[col] == value].tolist()

                        replace_log.append({
                            "column": col,
                            "rows": rows,
                            "old_value": value,
                            "new_value": np.nan
                        })

                        df[col] = df[col].replace(value, np.nan)

    return df, replace_log


class SmartDataCleaner(BaseEstimator, TransformerMixin):

    def __init__(
        self,
        missing_row_threshold=0.01,
        missing_col_threshold=0.7,
        id_unique_ratio=0.95,
        name_unique_ratio=0.7,
        max_name_length=25
    ):
        self.missing_row_threshold = missing_row_threshold
        self.missing_col_threshold = missing_col_threshold
        self.id_unique_ratio = id_unique_ratio
        self.name_unique_ratio = name_unique_ratio
        self.max_name_length = max_name_length

        self.remove_cols_ = []
        self.report_ = {}
        self.logs_ = []

    def fit(self, df: pd.DataFrame):
        df = df.copy()
        df, _ = detect_and_fix_missing(df)

        remove_cols = []

        for col in df.columns:

            unique_ratio = df[col].nunique() / len(df)

            if df[col].nunique() <= 1:
                remove_cols.append(col)

                self.logs_.append(
                    f"Removed {col} because it has only one value."
                )
                continue

            if df[col].isnull().mean() > self.missing_col_threshold:
                remove_cols.append(col)

                self.logs_.append(
                    f"Removed {col} because missing ratio is too high."
                )
                continue

            if (
                unique_ratio > self.id_unique_ratio
                and df[col].dtype == "object"
            ):
                remove_cols.append(col)

                self.logs_.append(
                    f"Removed {col} because it looks like an ID column."
                )
                continue

            if df[col].dtype == "object":

                avg_len = (
                    df[col]
                    .dropna()
                    .astype(str)
                    .str.len()
                    .mean()
                )

                if (
                    unique_ratio > self.name_unique_ratio
                    and avg_len < self.max_name_length
                ):
                    remove_cols.append(col)

                    self.logs_.append(
                        f"Removed {col} because it looks like a name column."
                    )

        self.remove_cols_ = remove_cols
        return self

    def transform(self, df: pd.DataFrame):
        df = df.copy()

        mem_before = (
            df.memory_usage(deep=True).sum() / 1024**2
        )

        df, replace_log = detect_and_fix_missing(df)

        report = {
            "initial_shape": df.shape,
            "final_shape": None,
            "removed_columns": [],
            "duplicate_rows_removed": [],
            "rows_removed_due_to_missing": {},
            "missing_before": df.isnull().sum().to_dict(),
            "missing_after": {},
            "filled_values": {},
            "replaced_values": replace_log,
            "memory_usage_before_mb": round(mem_before, 2),
            "memory_usage_after_mb": None,
            "column_types": {},
            "outliers": {},
            "logs": self.logs_
        }

        duplicate_rows = df[df.duplicated()].index.tolist()

        report["duplicate_rows_removed"] = duplicate_rows

        df = df.drop_duplicates()

        df.drop(
            columns=self.remove_cols_,
            inplace=True,
            errors="ignore"
        )

        report["removed_columns"] = self.remove_cols_

        for col in df.columns:

            if pd.api.types.is_numeric_dtype(df[col]):
                report["column_types"][col] = "numeric"
            else:
                report["column_types"][col] = "categorical"

        for col in df.columns:

            missing_ratio = df[col].isnull().mean()

            if 0 < missing_ratio < self.missing_row_threshold:

                removed_rows = (
                    df[df[col].isnull()].index.tolist()
                )

                report["rows_removed_due_to_missing"][col] = removed_rows

                df = df.dropna(subset=[col])

                self.logs_.append(
                    f"Removed rows from {col} because missing ratio was very small."
                )

            elif missing_ratio < 0.3:

                if pd.api.types.is_numeric_dtype(df[col]):

                    fill_value = df[col].median()

                    fill_count = df[col].isnull().sum()

                    df[col] = df[col].fillna(fill_value)

                    report["filled_values"][col] = {
                        "method": "median",
                        "count": int(fill_count),
                        "value_used": float(fill_value)
                    }

                    self.logs_.append(
                        f"Filled missing values in {col} using median."
                    )

                else:

                    if not df[col].mode().empty:

                        fill_value = df[col].mode()[0]

                        fill_count = df[col].isnull().sum()

                        df[col] = df[col].fillna(fill_value)

                        report["filled_values"][col] = {
                            "method": "mode",
                            "count": int(fill_count),
                            "value_used": str(fill_value)
                        }

                        self.logs_.append(
                            f"Filled missing values in {col} using mode."
                        )

            elif missing_ratio < self.missing_col_threshold:

                fill_count = df[col].isnull().sum()

                df[col] = df[col].fillna("UNKNOWN")

                report["filled_values"][col] = {
                    "method": "UNKNOWN",
                    "count": int(fill_count),
                    "value_used": "UNKNOWN"
                }

        for col in df.select_dtypes(include=np.number).columns:

            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)

            iqr = q3 - q1

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            outlier_rows = df[
                (df[col] < lower) | (df[col] > upper)
            ].index.tolist()

            if outlier_rows:

                report["outliers"][col] = {
                    "count": len(outlier_rows),
                    "rows": outlier_rows
                }

        for col in df.select_dtypes(include=["int64"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="integer")

        for col in df.select_dtypes(include=["float64"]).columns:
            df[col] = pd.to_numeric(df[col], downcast="float")

        mem_after = (
            df.memory_usage(deep=True).sum() / 1024**2
        )

        report["memory_usage_after_mb"] = round(mem_after, 2)

        report["missing_after"] = (
            df.isnull().sum().to_dict()
        )

        report["final_shape"] = df.shape

        self.report_ = report

        return df

    def fit_transform(self, df: pd.DataFrame):
        return self.fit(df).transform(df)

    def get_report(self):
        return self.report_

    def export_report(self, file_name="cleaning_report.json"):

        with open(file_name, "w") as f:
            json.dump(self.report_, f, indent=4)

        print(f"Report saved as {file_name}")


if __name__ == "__main__":

    data = pd.read_csv("titanic.csv")

    cleaner = SmartDataCleaner()

    clean_data = cleaner.fit_transform(data)

    print("\n===== CLEANED DATA =====\n")
    print(clean_data.head())

    print("\n===== CLEANING REPORT =====\n")
    print(json.dumps(cleaner.get_report(), indent=4))

    cleaner.export_report()