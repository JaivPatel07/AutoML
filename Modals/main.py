import pandas as pd
import numpy as np
import re


# --------------------------
# SMART MISSING DETECTOR
# --------------------------
def detect_and_fix_missing(df):
    df = df.copy()

    # common missing patterns
    df.replace(
        ["?", " ?", "NA", "N/A", "na", "null", "NULL", "-", "--", ""],
        np.nan,
        inplace=True
    )

    # whitespace-only values
    df.replace(r"^\s*$", np.nan, regex=True, inplace=True)

    # detect repeated garbage patterns
    for col in df.columns:

        if df[col].dtype == "object":

            counts = df[col].value_counts(dropna=True)
            total = len(df)

            for val, count in counts.items():

                ratio = count / total

                if isinstance(val, str):
                    clean_val = val.strip().lower()

                    # repeated junk like hhh, aaa, etc.
                    if ratio > 0.4 and re.fullmatch(r"(.)\1+", clean_val):
                        df[col] = df[col].replace(val, np.nan)

                    # known garbage tokens
                    elif clean_val in ["?", "na", "n/a", "null", "-", "--"]:
                        df[col] = df[col].replace(val, np.nan)

    return df


# --------------------------
# SMART DATA CLEANER CLASS
# --------------------------
class SmartDataCleaner:

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

    # --------------------------
    # FIT (learn rules)
    # --------------------------
    def fit(self, df: pd.DataFrame):
        df = df.copy()

        # clean missing first
        df = detect_and_fix_missing(df)

        remove_cols = []

        for col in df.columns:

            unique_ratio = df[col].nunique() / len(df)

            # constant column
            if df[col].nunique() <= 1:
                remove_cols.append(col)
                continue

            # too many missing
            if df[col].isnull().mean() > self.missing_col_threshold:
                remove_cols.append(col)
                continue

            # ID-like column
            if unique_ratio > self.id_unique_ratio and df[col].dtype == "object":
                remove_cols.append(col)
                continue

            # name-like column
            if df[col].dtype == "object":
                avg_len = df[col].dropna().astype(str).str.len().mean()

                if unique_ratio > self.name_unique_ratio and avg_len < self.max_name_length:
                    remove_cols.append(col)

        self.remove_cols_ = remove_cols
        return self

    # --------------------------
    # TRANSFORM (clean data)
    # --------------------------
    def transform(self, df: pd.DataFrame):
        df = df.copy()

        # clean missing patterns
        df = detect_and_fix_missing(df)

        report = {
            "initial_shape": df.shape,
            "removed_columns": [],
            "rows_dropped": 0,
            "missing_before": df.isnull().sum().to_dict(),
        }

        # remove duplicates
        before_rows = len(df)
        df = df.drop_duplicates()
        report["rows_dropped"] = before_rows - len(df)

        # drop useless columns
        df.drop(columns=self.remove_cols_, inplace=True, errors="ignore")
        report["removed_columns"] = self.remove_cols_

        # handle missing values
        for col in df.columns:

            missing_ratio = df[col].isnull().mean()

            # very small missing → drop rows
            if 0 < missing_ratio < self.missing_row_threshold:
                df = df.dropna(subset=[col])

            # moderate missing → fill values
            elif missing_ratio < 0.3:

                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].median())
                else:
                    if not df[col].mode().empty:
                        df[col] = df[col].fillna(df[col].mode()[0])

            # high missing → mark unknown
            elif missing_ratio < self.missing_col_threshold:
                df[col] = df[col].fillna("UNKNOWN")

        report["missing_after"] = df.isnull().sum().to_dict()
        report["final_shape"] = df.shape

        self.report_ = report
        return df

    # --------------------------
    # PIPELINE METHOD
    # --------------------------
    def fit_transform(self, df: pd.DataFrame):
        return self.fit(df).transform(df)

    # --------------------------
    # REPORT
    # --------------------------
    def get_report(self):
        return self.report_


# --------------------------
# USAGE
# --------------------------
if __name__ == "__main__":

    data = pd.read_csv("../titanic.csv")

    cleaner = SmartDataCleaner()

    clean_data = cleaner.fit_transform(data)

    print(clean_data.head())

    print(cleaner.get_report())