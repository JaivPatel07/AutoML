# Smart Data Cleaner

An intelligent data cleaning application featuring a high-contrast **Neobrutalist UI**. It automates the tedious parts of data preparation, providing smart suggestions for column removal and handling missing data or outliers with ease.

## Key Features
- **Drag-and-Drop Upload**: Supports CSV and Excel (`.xlsx`, `.xls`) files.
- **Smart Detection**: Automatically flags constant columns, high-null columns, and unique ID-like columns.
- **Advanced Cleaning**:
    - Standardizes missing value representations (e.g., `?`, `NA`, `null`).
    - Detects and removes repetitive junk values.
    - Handles numeric and categorical imputation (Mean, Median, Mode, Constant).
    - Statistical outlier detection using the Interquartile Range (IQR) method.
- **Interactive Reports**: Detailed visualization of missing values and data retention using Chart.js.
- **Neobrutalist Dark Mode**: A high-contrast dark theme toggle for better accessibility.
- **Memory Optimization**: Automatically downcasts data types to reduce memory footprint.

##  Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd AutoML
   ```

2. **Set up a virtual environment (optional):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

##  Usage

1. **Start the FastAPI server:**
   ```bash
   python run.py
   ```
   The application will start at `http://localhost:8000`.

2. **Access the Web Interface**:
   Open your browser and navigate to `http://localhost:8000`.

3. **Workflow**:
   - Upload your file to see a **Data Preview**.
   - Review auto-flagged columns and adjust cleaning settings (imputation methods, outlier sensitivity).
   - Click **Clean File** to process the entire dataset.
   - Explore the **Original**, **Cleaned**, and **Removed** tabs to verify the results.
   - Download your cleaned CSV.

##  Project Structure

```
AutoML/
├── app/
│   ├── cleaner/
│   │   └── cleaner.py       # Core SmartDataCleaner engine
│   ├── routes/
│   │   └── clean_routes.py  # FastAPI endpoints for processing/previewing
│   ├── main.py              # Application setup & static mounting
│   ├── uploads/             # Processed datasets storage
│   └── reports/             # JSON report storage
├── static/
│   ├── index.html           # Neobrutalist frontend
│   ├── styles.css           # Custom CSS with Dark Mode variables
│   └── script.js            # Frontend logic & Chart.js integration
├── run.py                   # Server entry point
└── requirements.txt         # Project dependencies
```

##  API Overview
- `POST /preview`: Generates a 10-row preview and identifies auto-flagging suggestions.
- `POST /clean`: Processes the file based on user-defined parameters.
- `GET /view/original`: Returns the original data with outlier highlighting.
- `GET /view/cleaned`: Returns the final cleaned dataset.
- `GET /view/removed`: Returns rows discarded during cleaning with specific reasons (Duplicates, Outliers, etc.).
- `GET /report`: Fetches the comprehensive JSON cleaning report.
- `GET /download`: Triggers the download of the cleaned CSV.

##  License
This project is licensed under the MIT License.

---
*Built with FastAPI, Pandas, and Neobrutalist Design.*