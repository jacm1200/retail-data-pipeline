# Retail Data Pipeline

This is a personal project I'm building to practice Data Engineering and learn how to work with data from start to finish.

The idea is simple: take a messy retail sales CSV, clean and validate the data, and load the valid records into PostgreSQL. I also wanted to make the project easy to run on another machine, so I used Docker.

## What does the pipeline do?

- Reads raw sales data from a CSV file.
- Cleans column names and standardizes text values.
- Handles different date and price formats.
- Checks for missing or invalid values.
- Removes exact duplicate records.
- Saves valid records and rejected rows into separate CSV files.
- Generates a JSON report with data quality metrics.
- Loads the valid records into PostgreSQL.
- Uses an UPSERT strategy to avoid creating duplicate orders when the pipeline runs more than once.

## How it works

The pipeline follows this process:

`Raw CSV → Data cleaning → Validation → CSV outputs + Quality report → PostgreSQL`

The main logic is in `src/pipeline.py`. I use pandas to process the data, SQLAlchemy to connect to PostgreSQL, and Docker Compose to run the services.

## Technologies I'm using

- Python
- pandas
- PostgreSQL
- SQLAlchemy
- Docker and Docker Compose
- pytest

## Project structure

```text
retail-data-pipeline/
├── data/
│   ├── raw/
│   ├── processed/
│   ├── rejected/
│   └── reports/
├── src/
│   └── pipeline.py
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## How to run it

You need Python and Docker Desktop installed.

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd retail-data-pipeline
```

### 2. Configure the environment

Create a `.env` file based on `.env.example` and configure the PostgreSQL variables.

```powershell
Copy-Item .env.example .env
```

Make sure the credentials in `.env` match the configuration used by Docker Compose.

### 3. Run the pipeline

```bash
docker compose up --build
```

The pipeline processes the input CSV and loads valid records into PostgreSQL. The generated CSV files and quality report are saved in the `data/` directory.

### 4. Run the tests

```bash
docker compose run --build --rm pipeline python -m pytest -v
```

The tests cover data processing and PostgreSQL loading, including the UPSERT behavior.

## Data quality checks

The pipeline currently checks for:

- Missing or invalid required fields.
- Quantities that are zero or negative.
- Negative unit prices.
- Duplicate records.
- Dates and prices that need normalization.

Invalid rows are separated from valid records so they can be reviewed instead of silently discarded.

## What I've learned

While building this project, I've been practicing:

- Structuring a Python data pipeline.
- Cleaning and validating data with pandas.
- Working with PostgreSQL and SQLAlchemy.
- Using UPSERT to make repeated loads safer.
- Running an application and database with Docker Compose.
- Writing unit and integration tests.
- Tracking data quality through a JSON report.

## What's next?

This project is still a work in progress. Some improvements I'd like to explore next are:

- Adding structured logging and better error handling.
- Setting up automated tests with GitHub Actions.
- Improving the pipeline for larger datasets.
- Exploring dbt for analytics transformations.
- Adding orchestration with Airflow.
- Deploying the project to a cloud platform.

## A note about the data

The project uses sample data for demonstration purposes. No real customer information or credentials should be committed to the repository.
