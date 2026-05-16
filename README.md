# Smart Data Cleaner 🧹

An intelligent data cleaning application with a modern web interface that allows you to upload CSV or Excel files, automatically clean them, and compare before/after results.

## Features

✨ **Key Features:**
- 🚀 Easy drag-and-drop CSV or Excel file upload
- 🧹 Automatic data cleaning with smart algorithms
- 📊 Side-by-side comparison of original vs cleaned data
- 📈 Detailed cleaning report with statistics
- 📱 Responsive web interface
- 🎨 Modern, intuitive UI

## Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd AutoML
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Application

1. **Run the server:**
```bash
python run.py
```

The API will start at `http://localhost:8000`

2. **Open in browser:**
Navigate to `http://localhost:8000/static/index.html`

### Using the Frontend

1. **Upload File**: Select or drag-drop a CSV/Excel file.
2. **Clean File**: Click "Clean File".
3. **View Results**: Compare data and view statistics in the tabs.
   - **Original Tab**: See your original data
   - **Cleaned Tab**: See the cleaned version
   - **Report Tab**: View detailed cleaning statistics and changes

## Project Structure

```
AutoML/
├── app/
│   ├── main.py              # FastAPI application setup
│   ├── cleaner/
│   │   └── cleaner.py       # Data cleaning logic
│   ├── routes/
│   │   └── clean_routes.py  # API endpoints
│   └── uploads/             # Uploaded files (auto-created)
├── static/
│   ├── index.html          # Frontend UI
│   ├── styles.css          # Styling
│   └── script.js           # Frontend logic
├── run.py                   # Application entry point
└── requirements.txt         # Python dependencies
```

## API Endpoints

### POST `/clean`
Upload and clean a CSV/Excel file.
**Parameters:**
- `file`: File to clean

**Response:**
```json
{
  "message": "Cleaning completed",
  "cleaned_file": "app/uploads/cleaned_filename.csv",
  "report_file": "app/reports/filename.csv_report.json",
  "filename": "filename.csv"
}
```

### GET `/view/original`
Get original file data (first 100 rows).

**Response:**
```json
{
  "filename": "filename.csv",
  "data": [...],
  "shape": [rows, columns],
  "columns": [...],
  "total_rows": number
}
```

### GET `/view/cleaned`
Get cleaned data (first 100 rows).

**Response:** Same format as `/view/original`

### GET `/report`
Get cleaning report with statistics.

## What Gets Cleaned

The Smart Data Cleaner performs the following operations:

- ✓ Missing value detection and handling
- ✓ Duplicate value removal
- ✓ Data type inference
- ✓ Outlier detection
- ✓ Invalid character removal
- ✓ Whitespace trimming
- ✓ Format standardization

## System Requirements

- Python 3.8 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)
- 2GB RAM minimum

## Troubleshooting

**Issue: "Cannot connect to API server"**
- Make sure the server is running: `python run.py`
- Check that port 8000 is not in use
- Verify no firewall is blocking localhost:8000

**Issue: File upload fails**
- Ensure the file is a valid CSV or Excel format
- Check file size is reasonable (< 100MB recommended)
- Try a different file to confirm it's not file-specific

**Issue: Cleaning takes too long**
- Large files may take time to process
- Try with a smaller sample of your data first

## License

This project is licensed under the MIT License.

## Support

For issues or questions, please open an issue in the repository.