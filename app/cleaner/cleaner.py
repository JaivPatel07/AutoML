import pandas as pd
import numpy as np
import re
import json
from sklearn.base import BaseEstimator, TransformerMixin


def fix_missing_values(df):
    df = df.copy()

    missing_values = [
        "?", "NA", "N/A", "na",
        "null", "NULL", "-", "--", ""
    ]

    df.replace(missing_values, np.nan, inplace=True)
    df.replace(r"^\s*$", np.nan, regex=True, inplace=True)

    replaced_data = []

    for col in df.select_dtypes(include="object").columns:

        value_counts = df[col].value_counts(dropna=True)

        for value, count in value_counts.items():

            ratio = count / len(df)

            if (
                isinstance(value, str)
                and ratio > 0.4
                and re.fullmatch(r"(.)\1+", value.strip().lower())
            ):

                rows = df.index[df[col] == value].tolist()

                replaced_data.append({
                    "column": col,
                    "rows": rows,
                    "old_value": value,
                    "new_value": "NaN"
                })

                df[col] = df[col].replace(value, np.nan)

    return df, replaced_data


class SmartDataCleaner(BaseEstimator, TransformerMixin):

    def __init__(
        self,
        row_missing_limit=0.01,
        col_missing_limit=0.7,
        id_limit=0.95,
        name_limit=0.7,
        max_name_size=25
    ):

        self.row_missing_limit = row_missing_limit
        self.col_missing_limit = col_missing_limit
        self.id_limit = id_limit
        self.name_limit = name_limit
        self.max_name_size = max_name_size

        self.remove_columns = []
        self.logs = []
        self.report = {}

    def fit(self, df):

        df = df.copy()

        df, _ = fix_missing_values(df)

        for col in df.columns:

            unique_ratio = df[col].nunique(dropna=True) / len(df)

            if df[col].nunique(dropna=True) <= 1:

                self.remove_columns.append(col)

                self.logs.append(
                    f"{col} removed because it has one value"
                )

                continue

            if df[col].isnull().mean() > self.col_missing_limit:

                self.remove_columns.append(col)

                self.logs.append(
                    f"{col} removed because missing values are high"
                )

                continue

            if (
                df[col].dtype == "object"
                and unique_ratio > self.id_limit
            ):

                self.remove_columns.append(col)

                self.logs.append(
                    f"{col} removed because it looks like ID"
                )

                continue

            if df[col].dtype == "object":

                avg_length = (
                    df[col]
                    .dropna()
                    .astype(str)
                    .str.len()
                    .mean()
                )

                if (
                    unique_ratio > self.name_limit
                    and avg_length < self.max_name_size
                ):

                    self.remove_columns.append(col)

                    self.logs.append(
                        f"{col} removed because it looks like name"
                    )

        return self

    def transform(self, df):

        df = df.copy()

        memory_before = (
            df.memory_usage(deep=True).sum() / 1024**2
        )

        df, replaced_data = fix_missing_values(df)

        report = {
            "initial_shape": df.shape,
            "final_shape": None,
            "removed_columns": [],
            "duplicate_rows_removed": [],
            "missing_before": df.isnull().sum().to_dict(),
            "missing_after": {},
            "filled_values": {},
            "replaced_values": replaced_data,
            "outliers": {},
            "memory_before_mb": round(memory_before, 2),
            "memory_after_mb": None,
            "logs": self.logs
        }

        duplicate_rows = df[df.duplicated()].index.tolist()

        report["duplicate_rows_removed"] = duplicate_rows

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

                df = df.dropna(subset=[col])

                self.logs.append(
                    f"Rows removed from {col}"
                )

            elif pd.api.types.is_numeric_dtype(df[col]):

                fill_value = df[col].median()

                fill_count = df[col].isnull().sum()

                df[col] = df[col].fillna(fill_value)

                report["filled_values"][col] = {
                    "method": "median",
                    "count": int(fill_count)
                }

            else:

                if not df[col].mode().empty:
                    fill_value = df[col].mode()[0]
                else:
                    fill_value = "UNKNOWN"

                fill_count = df[col].isnull().sum()

                df[col] = df[col].fillna(fill_value)

                report["filled_values"][col] = {
                    "method": "mode",
                    "count": int(fill_count)
                }

        for col in df.select_dtypes(include=np.number).columns:

            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)

            iqr = q3 - q1

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            outlier_rows = df[
                (df[col] < lower) |
                (df[col] > upper)
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

        memory_after = (
            df.memory_usage(deep=True).sum() / 1024**2
        )

        report["memory_after_mb"] = round(memory_after, 2)

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

        print(f"Report saved as {file_name}")