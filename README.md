# Retail Data Pipeline

This is a personal project I'm building to improve my Data Engineering skills and get more hands-on experience working with data.

The goal is to take a messy retail sales CSV, clean and validate the data, and load the valid records into PostgreSQL. I also wanted to make the whole process reproducible, so I used Docker to run the pipeline and the database.

## What does it do?

The pipeline goes through these steps:

1. Reads raw retail sales data from a CSV file.
2. Standardizes column names and text values.
3. Handles different date and price formats.
4. Validates records and checks for missing or invalid values.
5. Removes exact duplicate records.
6. Separates valid records from rejected rows.
7. Generates a JSON report with data quality metrics.
8. Loads valid records into PostgreSQL.
9. Uses UPSERT logic to insert new orders or update existing ones without creating duplicate order IDs.

## How it works

The main processing logic is in `src/pipeline.py`.

The general workflow is:

```text
Raw CSV
   |
   v
Data cleaning and validation
   |
   +------> Clean CSV
   |
   +------> Rejected rows CSV
   |
   +------> Data quality report (JSON)
   |
   v
PostgreSQL
```

I use pandas to process the data, SQLAlchemy to interact with PostgreSQL, and Docker Compose to run the services together.

## Technologies

- Python
- pandas
- PostgreSQL
- SQLAlchemy
- Docker and Docker Compose
- pytest
- Python logging
- GitHub Actions for continuous integration

The GitHub Actions workflow runs the pipeline and test suite on pushes and pull requests targeting `main`.

## Project structure

```text
retail-data-pipeline/
|-- data/
|   |-- raw/
|   |   `-- orders_dirty.csv
|   |-- processed/
|   |-- rejected/
|   `-- reports/
|-- src/
|   `-- pipeline.py
|-- tests/
|   |-- test_pipeline.py
|   `-- test_postgres.py
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
|-- .env.example
`-- README.md
```

## How to run the project

You'll need Docker Desktop and Git installed.

### 1. Clone the repository

```bash
git clone https://github.com/jacm1200/retail-data-pipeline.git
cd retail-data-pipeline
```

### 2. Configure the environment

Create your local `.env` file from the example:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS/Linux**

```bash
cp .env.example .env
```

Review the PostgreSQL settings in `.env`. The credentials must match the configuration used by Docker Compose.

The `.env` file is for local configuration and should never be committed to GitHub.

### 3. Run the pipeline

Build the image and run the pipeline with Docker Compose:

```bash
docker compose run --build --rm pipeline
```

The pipeline reads the input CSV, processes the records, writes its output files, and loads valid orders into PostgreSQL.

The generated files include:

- `data/processed/orders_clean.csv`
- `data/rejected/orders_rejected.csv`
- `data/reports/quality_report.json`

The PostgreSQL table is called `retail_orders`.

### Example quality report

For the included sample CSV, the pipeline produces a report like this:

```json
{
  "input_rows": 16,
  "exact_duplicates_removed": 1,
  "valid_rows": 11,
  "rejected_rows": 4,
  "quality_rate_percent": 68.75,
  "rows_upserted_to_postgres": 11,
  "postgres_load_status": "success"
}
```

The counts reconcile: 16 input rows result in 11 valid rows, 4 rejected rows, and 1 exact duplicate removed. The quality rate is the percentage of input rows retained as valid records.

### 4. Run the tests

```bash
docker compose run --build --rm pipeline python -m pytest -v
```

The tests cover data cleaning, validation, and PostgreSQL loading, including the UPSERT behavior.

### 5. Query the database

You can connect to PostgreSQL using:

```bash
docker compose exec db psql -U retail_user -d retail_db
```

Once connected, you can run queries such as:

```sql
-- Count the loaded orders
SELECT COUNT(*)
FROM retail_orders;

-- Calculate revenue by country
SELECT
    country,
    SUM(quantity * unit_price) AS revenue
FROM retail_orders
GROUP BY country
ORDER BY revenue DESC;
```

These queries are useful for checking the loaded data and exploring basic sales metrics.

## Data quality rules

The pipeline currently checks for:

- Missing required fields.
- Invalid or unparseable dates and values.
- Quantities greater than zero.
- Unit prices greater than or equal to zero.
- Exact duplicate records.

Valid records continue through the pipeline, while rejected rows are saved separately for review. The JSON report summarizes the processing results and data quality metrics.

## What I've learned

Building this project has helped me practice:

- Working with pandas to clean and validate data.
- Structuring a Python pipeline.
- Connecting Python to PostgreSQL with SQLAlchemy.
- Using UPSERT to make repeated loads safer.
- Running applications and databases with Docker Compose.
- Writing unit and integration tests.
- Tracking data quality with a JSON report.
- Using Git and GitHub to manage a project.

## What's next?

I want to keep improving this project and explore more Data Engineering tools. Possible next steps are:

- Expanding data quality checks and test coverage.
- Improving the pipeline to handle larger datasets efficiently.
- Exploring dbt for analytics transformations.
- Adding orchestration with Airflow.
- Exploring deployment to a cloud platform.

## Data and security

The project uses sample data for demonstration purposes. No real customer information, passwords, API keys, or local `.env` files should be committed to the repository.
