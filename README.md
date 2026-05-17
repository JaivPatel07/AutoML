# Smart Data Cleaner

![Version](https://img.shields.io/badge/version-v1-blue)
![Backend](https://img.shields.io/badge/backend-FastAPI-green)
![Status](https://img.shields.io/badge/status-active-success)

Smart Data Cleaner is an intelligent dataset preprocessing and cleaning system built with FastAPI and Pandas.

The project automates repetitive data cleaning tasks such as missing value handling, duplicate removal, outlier detection, column analysis, and memory optimization while generating explainable cleaning reports.

It is designed to simplify preprocessing workflows for machine learning and data analytics pipelines.

---

## Features

### Smart Dataset Analysis

Automatically detects:

* Constant columns
* High-null columns
* ID-like columns
* High-cardinality columns
* Statistical outliers

### Advanced Data Cleaning

* Missing value standardization
* Duplicate row removal
* Junk value detection
* Numeric imputation:

  * Mean
  * Median
  * Constant
* Categorical imputation:

  * Mode
  * Constant
* IQR-based outlier removal

### Explainable Cleaning Reports

Generates detailed reports including:

* Removed columns with reasons
* Missing value replacements
* Outlier statistics
* Duplicate row information
* Dataset retention summary
* Memory optimization details

### File Support

* CSV (`.csv`)
* Excel (`.xlsx`, `.xls`)

### Optimization

* Automatic datatype downcasting
* Reduced memory footprint

---

## API Endpoints

| Method | Endpoint         | Description                                              |
| ------ | ---------------- | -------------------------------------------------------- |
| POST   | `/preview`       | Generates dataset preview and auto-detection suggestions |
| POST   | `/clean`         | Cleans dataset using selected parameters                 |
| GET    | `/view/original` | Returns original dataset                                 |
| GET    | `/view/cleaned`  | Returns cleaned dataset                                  |
| GET    | `/view/removed`  | Returns removed rows with reasons                        |
| GET    | `/report`        | Returns detailed cleaning report                         |
| GET    | `/download`      | Downloads cleaned CSV                                    |

---

## Tech Stack

### Backend

* FastAPI
* Pandas
* NumPy
* Python

### Data Processing

* Statistical preprocessing
* IQR outlier detection
* Memory optimization
* Dataset profiling

---

## Installation

### Clone Repository

```bash
git clone <repository-url>
cd AutoML
```

### Create Virtual Environment

```bash
python -m venv venv
```

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / Mac

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run Project

```bash
python run.py
```

Server starts at:

```txt
http://localhost:8000
```

---

## Workflow

1. Upload dataset
2. Preview auto-detected issues
3. Configure cleaning parameters
4. Run cleaning process
5. Review reports
6. Download cleaned dataset

---

## Project Structure

```bash
AutoML/
├── app/
│   ├── cleaner/
│   │   └── cleaner.py
│   ├── routes/
│   │   └── clean_routes.py
│   ├── uploads/
│   ├── reports/
│   └── main.py
│
├── static/
│   ├── index.html
│   ├── styles.css
│   └── script.js
│
├── run.py
├── requirements.txt
└── README.md
```

---

## Why I Built This

Data preprocessing is one of the most repetitive stages in machine learning workflows.

I built Smart Data Cleaner to automate common cleaning operations while keeping the process transparent through explainable reports and structured preprocessing summaries.

---

## Upcoming Features

* Prediction pipeline integration
* ML-based cleaning recommendations
* Exportable PDF reports
* Advanced dataset profiling
* Automated preprocessing workflows

---

## Author

Jaiv Patel
