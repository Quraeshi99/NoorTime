# NoorTime Backend

Welcome to the NoorTime Backend repository. This project provides a robust, role-based REST API to serve prayer times, manage users, and handle application settings.

## Features

- **Dynamic Prayer Times**: Serves prayer times based on location and calculation methods.
- **Role-Based Access Control (RBAC)**: A 4-tier role system with distinct permissions:
  - **Super Admin**: Full control over the application.
  - **Manager**: Can manage users and content.
  - **Masjid**: A special account that can define prayer times and announcements for its followers.
  - **Client**: A regular end-user who can use the app individually or follow a Masjid.
- **User & App Management**: Comprehensive APIs for Super Admins and Managers.
- **Secure Authentication**: Uses Supabase for JWT-based authentication.
- **Containerized**: Comes with a `Dockerfile` for easy deployment.

### New! Community & Masjid Features

- **Follow a Masjid**: Users can follow one or more Masjids to get their official prayer times and announcements.
- **Default Masjid**: Traveling users can set a "default" Masjid from their followed list to see timings relevant to their current location.
- **Masjid Discovery**: Users can find Masjids by searching for them near their location or by entering a unique, shareable code provided by the Masjid.
- **Masjid Announcements**: Masjid accounts can post events and announcements to their followers.

## Technology Stack

- **Framework**: Flask
- **Database**: PostgreSQL
- **Authentication**: Supabase (JWT Validation)
- **Testing**: Pytest, SQLite (for tests)
- **Deployment**: Docker, Gunicorn

---

## Backend Setup: A Step-by-Step Guide

Follow these instructions to set up and run the backend on your local machine.

### Prerequisites

- Python (3.10+)
- PostgreSQL database server (for development/production)

### Step 1: Clone the Repository

```bash
git clone <your-repository-url>
cd NoorTime/backend
```

### Step 2: Create Virtual Environment & Install Dependencies

It's highly recommended to use a virtual environment.

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
# venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

### Step 3: Database & Environment Configuration

1.  **Create a PostgreSQL database** for development. For example, `noortime_dev`.
2.  **Create your `.env` file**: Copy the `backend/.env.example` file to a new file named `backend/.env`.
3.  **Fill in the `.env` file** with your credentials. Note that `TEST_DATABASE_URL` is no longer required as tests now run on a temporary SQLite database.

    ```env
    # Your Supabase project URL for JWT validation
    SUPABASE_URL=https://<your-project-ref>.supabase.co

    # Connection string for your development database
    DATABASE_URL=postgresql://user:password@host:port/noortime_dev

    # A strong, random secret key
    SECRET_KEY=generate_a_strong_secret_key

    # (Optional) Other API keys
    OPENWEATHERMAP_API_KEY=
    SENTRY_DSN=
    ```

### Step 4: Database Migrations

This project uses Flask-Migrate to manage database schema changes.

#### Pending Migrations (As of 2025-10-25)

**Important:** A new `timezone` field has been added to the `UserSettings` model to make the application fully timezone-aware. A unique constraint (`uq_zone_year_method`) has been added to the `PrayerZoneCalendar` model to ensure data integrity. Additionally, a `schema_version` field has been added to `PrayerZoneCalendar` for cache versioning. Migration scripts need to be generated and applied for these changes.

If the database service is not running, the migration commands will fail. Ensure your PostgreSQL server is active, then run:

```bash
# 1. Generate the migration script (if it doesn't exist yet)
flask db migrate -m "Add timezone to UserSettings model, unique constraint and schema_version to PrayerZoneCalendar"

# 2. Apply the migration to the database
flask db upgrade
```

#### General Usage

To initialize or upgrade your database to the latest version, run the following commands from the `backend` directory:

```bash
# To create a new migration after changing models.py
flask db migrate -m "Your migration message"

# To apply the migration to the database
flask db upgrade
```

### Step 5: Run the Application

```bash
# Set the environment variables for the Flask CLI
export FLASK_APP="project:create_app('development')"
export FLASK_ENV=development

# Run the development server
flask run --host=0.0.0.0 --port=5000
```

### Step 6: Running Tests

This project uses the `pytest` framework for testing. Thanks to a custom configuration, the test suite runs independently of any external database, making it fast, reliable, and easy to use.

#### Production vs. Test Environment

It is crucial to understand the difference:

-   **Production/Development (`flask run`):** When you run the application normally, it connects to the real PostgreSQL database specified by the `DATABASE_URL` in your `.env` file.
-   **Testing (`pytest`):** When you run tests, the application is **automatically** configured to use a temporary, **in-memory SQLite database**. This means:
    -   You do **not** need to set up a separate PostgreSQL test database.
    -   Your real database is **never** touched by the tests.
    -   Tests run very fast and do not require an internet connection.

#### How to Run Tests

To run the entire test suite, navigate to the `backend` directory and run the following command:

```bash
# From the NoorTime/backend/ directory
PYTHONPATH=. pytest
```

This command does two things:
1.  `PYTHONPATH=.`: Tells Python to find your application's 'project' module in the current directory.
2.  `pytest`: Discovers and runs all test files in the `tests/` directory.

To run a specific file, you can do:
```bash
PYTHONPATH=. pytest tests/test_new_logic.py
```

#### Test Files Overview

-   `tests/test_time_utils.py`: Contains **Unit Tests** for utility functions, including the complex "Jummah logic" for calculating the next day's prayer.
-   `tests/test_new_logic.py`: Contains **Integration Tests** for new features. These tests use "mocking" to simulate external services, ensuring they run without network dependency.
-   `tests/test_api.py`, `tests/test_api_routes.py`, `tests/test_management_routes.py`: Contain the original integration tests for the application's API endpoints. These are now running against the in-memory SQLite database.

---

## API Documentation

For detailed information on all available API endpoints, their parameters, and example responses, please see the [API Documentation](backend/API_DOCUMENTATION.md).

## Docker Deployment

This project includes a `Dockerfile` for easy containerization.

1.  **Build the Docker image:**
    ```bash
    docker build -t noortime-backend .
    ```
2.  **Run the Docker container:**
    You must pass the environment variables from your `.env` file to the container.
    ```bash
    docker run -d -p 5000:5000 --env-file .env --name noortime-app noortime-backend
    ```