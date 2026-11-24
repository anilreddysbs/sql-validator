# SQL Script Validator


> **Portfolio:** [anilreddysbs.vercel.app](https://anilreddysbs.vercel.app) · [GitHub profile](https://github.com/anilreddysbs)

A Flask-based utility for checking SQL and PL/SQL scripts against a configurable set of database development rules. It accepts text scripts, reports rule results, and generates a downloadable PDF validation report.

## What it checks

The rule set is designed for Oracle-style SQL and PL/SQL conventions. It includes checks for:

- DML and DDL commit handling
- PL/SQL block terminators and statement semicolons
- Object naming, schema prefixes, and schema consistency
- Backup-table naming, tablespace, grant, and drop restrictions
- Grant privilege restrictions and prohibited GRANT ALL statements
- NOLOGGING and tablespace restrictions

Rule configuration, including loader aliases, is maintained in `config/checks.json`.

For the detailed rule definitions and examples, see [SQL Validator Rule Documentation](SQL%20Validator%20%E2%80%93%20Final%20Rule%20Documentation.txt).

## Features

- Browser-based interface for submitting SQL text files
- Validation results grouped by query, with file-level checks and warnings
- Summary of total, passed, and failed checks
- PDF report generation with run metadata
- Configurable validation rules
- 2 MB request-size limit and basic response security headers

## Technology

- Python
- Flask
- ReportLab
- Gunicorn

## Run locally

### Prerequisites

- Python 3.10 or newer
- pip

### Setup

```bash
git clone https://github.com/anilreddysbs/sql-validator.git
cd sql-validator

python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install dependencies and start the application:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Validation workflow

1. Upload a SQL script saved as a `.txt` file.
2. Enter the optional run details shown in the form.
3. Choose whether the backup-specific validation toggle should be enabled.
4. Submit the script and review the query-level and file-level results.
5. Download the generated PDF report.

The application also accepts base64-encoded SQL content through the `sql_content_b64` form field.

## API

### POST /validate

Submit a multipart form containing either:

- `sqlFile`: a text file with a `.txt` extension, or
- `sql_content_b64`: base64-encoded UTF-8 SQL content.

Optional metadata fields include `name`, `email`, `team`, `cr_number`, and `backup_toggle`.

A successful response includes:

- `results`: validation output for each parsed query
- `summary`: aggregate counts, file-level validations, and warnings
- `pdf_url`: URL for downloading the generated report

### GET /download/<filename>

Downloads a generated PDF report.

## Tests and examples

Sample validation inputs and the comprehensive test runner are in the `test/` directory. Run the test script from the repository root:

```bash
python test/run_comprehensive.py
```

## Notes

This tool checks scripts against the configured rule set; it does not execute SQL against an Oracle database. Review the rules and test cases against your team's standards before using the output as a release approval.

The Flask application does not implement user authentication. Restrict access appropriately before exposing it beyond a trusted environment.
