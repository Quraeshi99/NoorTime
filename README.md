# NoorTime Backend

Welcome to the NoorTime Backend repository. This project provides a robust, role-based REST API to serve prayer times, manage users, and handle application settings.

## Features

- **Dynamic Prayer Times**: Serves prayer times based on location and calculation methods.
- **Role-Based Access Control (RBAC)**: A 3-tier role system with distinct permissions:
  - **Super Admin**: Full control over the application.
  - **Manager**: Can manage users and content like popups.
  - **Client**: A regular end-user with access to personal settings.
- **User & App Management**: Comprehensive APIs for Super Admins and Managers to control the application.
- **Secure Authentication**: Uses Supabase for JWT-based authentication.
- **Containerized**: Comes with a `Dockerfile` for easy deployment.

## Technology Stack

- **Framework**: Flask
- **Database**: PostgreSQL
- **Authentication**: Supabase (JWT Validation)
- **Testing**: Pytest
- **Deployment**: Docker, Gunicorn

---

## Backend Setup: A Step-by-Step Guide

Follow these instructions to set up and run the backend on your local machine.

### Prerequisites

- Python (3.10+)
- PostgreSQL database server

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

1.  **Create two PostgreSQL databases**: one for development and one for testing. For example, `noortime_dev` and `noortime_test`.
2.  **Create your `.env` file**: Copy the `backend/.env.example` file to a new file named `backend/.env`.
3.  **Fill in the `.env` file** with your credentials:

    ```env
    # Your Supabase project URL for JWT validation
    SUPABASE_URL=https://<your-project-ref>.supabase.co

    # Connection string for your development database
    DATABASE_URL=postgresql://user:password@host:port/noortime_dev

    # Connection string for your testing database
    # IMPORTANT: Tests will clear this database. Use a separate one.
    TEST_DATABASE_URL=postgresql://user:password@host:port/noortime_test

    # A strong, random secret key
    SECRET_KEY=generate_a_strong_secret_key

    # (Optional) Other API keys
    OPENWEATHERMAP_API_KEY=
    SENTRY_DSN=
    ```

### Step 4: Manual Database Schema Setup

Since the project no longer uses migrations, you need to create the database schema manually. Connect to your **development database** (`noortime_dev`) and run the following SQL script. You must run this script on your **test database** (`noortime_test`) as well.

```sql
-- Create the user table with the new role column
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    supabase_user_id VARCHAR(36) UNIQUE,
    email VARCHAR(120) UNIQUE NOT NULL,
    name VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'Client',
    default_latitude FLOAT,
    default_longitude FLOAT,
    default_city_name VARCHAR(100),
    default_calculation_method VARCHAR(50),
    time_format_preference VARCHAR(10) DEFAULT '12h'
);
CREATE INDEX ix_user_supabase_user_id ON "user" (supabase_user_id);

-- Create the user_settings table
CREATE TABLE user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES "user"(id),
    adjust_timings_with_api_location BOOLEAN DEFAULT true,
    auto_update_api_location BOOLEAN DEFAULT false,
    threshold_minutes INTEGER DEFAULT 5, -- New: Threshold for prayer time updates
    last_api_times_for_threshold TEXT, -- New: Stores last API times as JSON string
    fajr_is_fixed BOOLEAN DEFAULT false,
    fajr_fixed_azan VARCHAR(5) DEFAULT '05:30',
    fajr_fixed_jamaat VARCHAR(5) DEFAULT '05:45',
    fajr_azan_offset INTEGER DEFAULT 10,
    fajr_jamaat_offset INTEGER DEFAULT 15,
    dhuhr_is_fixed BOOLEAN DEFAULT true,
    dhuhr_fixed_azan VARCHAR(5) DEFAULT '01:30',
    dhuhr_fixed_jamaat VARCHAR(5) DEFAULT '01:45',
    dhuhr_azan_offset INTEGER DEFAULT 15,
    dhuhr_jamaat_offset INTEGER DEFAULT 15,
    asr_is_fixed BOOLEAN DEFAULT false,
    asr_fixed_azan VARCHAR(5) DEFAULT '05:00',
    asr_fixed_jamaat VARCHAR(5) DEFAULT '05:20',
    asr_azan_offset INTEGER DEFAULT 20,
    asr_jamaat_offset INTEGER DEFAULT 20,
    maghrib_is_fixed BOOLEAN DEFAULT false,
    maghrib_fixed_azan VARCHAR(5) DEFAULT '18:50',
    maghrib_fixed_jamaat VARCHAR(5) DEFAULT '18:55',
    maghrib_azan_offset INTEGER DEFAULT 0,
    maghrib_jamaat_offset INTEGER DEFAULT 5,
    isha_is_fixed BOOLEAN DEFAULT false,
    isha_fixed_azan VARCHAR(5) DEFAULT '20:15',
    isha_fixed_jamaat VARCHAR(5) DEFAULT '20:30',
    isha_azan_offset INTEGER DEFAULT 45,
    isha_jamaat_offset INTEGER DEFAULT 15,
    jummah_azan_time VARCHAR(5) DEFAULT '01:15',
    jummah_khutbah_start_time VARCHAR(5) DEFAULT '01:30',
    jummah_jamaat_time VARCHAR(5) DEFAULT '01:45'
);

-- Create the app_settings table
CREATE TABLE app_settings (
    id SERIAL PRIMARY KEY,
    default_latitude FLOAT,
    default_longitude FLOAT,
    default_calculation_method VARCHAR(50),
    sentry_dsn VARCHAR(255),
    openweathermap_api_key VARCHAR(255),
    is_new_feature_enabled BOOLEAN DEFAULT false,
    welcome_message VARCHAR(500) DEFAULT 'Welcome to NoorTime!'
);

-- Create the popup table
CREATE TABLE popup (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
);
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

Ensure you have set up your `TEST_DATABASE_URL` in the `.env` file and created the schema in the test database.

```bash
pytest
```

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
