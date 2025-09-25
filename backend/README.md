# NoorTime Backend

This is the backend server for the NoorTime application, a prayer time management tool for mosques.

## Core Architecture

The backend is built with Flask and employs a sophisticated caching strategy to provide accurate, reliable, and fast prayer times globally.

### Prayer Time Caching: The Grid System

To ensure accuracy for mosques worldwide while minimizing dependency on external APIs, the application uses a persistent, database-backed grid caching system.

1.  **Geographic Grid**: The world is divided into a grid of uniform cells (currently configured to `0.2x0.2` degrees, which is approximately `22x22` kilometers).
2.  **Zoning**: When a request for prayer times is made from a specific latitude and longitude, the coordinate is first mapped to a unique `zone_id` representing its grid cell.
3.  **Database Cache**: The application then checks a local database (`PrayerZoneCalendar` table) for a valid, full-year prayer time calendar for that `zone_id`.
4.  **Cache Hit**: If a calendar for the zone and year is found in the database, prayer times are served instantly from this local cache. No external API call is made.
5.  **Cache Miss**: If no calendar is found for the zone, the application contacts the Al-Adhan API **once** to fetch the **entire year's calendar** for the center of that zone. This data is then stored in the database, and all future requests from within that zone are served from the new cache.

This architecture ensures that for any ~22x22 km area, we only contact the external API once per year, making the application extremely fast and resilient to API outages.

### Caching Architecture: The Two-Layer Defense

To handle a global user base and ensure 100% uptime, especially during the new year transition, the application implements a "Two-Layer Defense" caching strategy. This solves the "Thundering Herd" problem (where all users request new data at once on Jan 1st) and ensures a seamless user experience.

#### Layer 1: Proactive Background Pre-caching

-   **What:** A background script (`scripts/precache_next_year.py`) runs independently of user traffic.
-   **When:** It's designed to be run by a scheduler (cron job) in the last quarter of the year (Oct-Dec).
-   **How:** It queries the database for all unique zones that have been used in the current year. For each zone, it proactively fetches and caches the calendar for the *entire next year*. This pre-fills the cache for the vast majority of users before the new year begins.

#### Layer 2: "Stale-While-Revalidate" Grace Period

-   **What:** This is a safety net built into the main application logic (`prayer_time_service.py`) to handle edge cases.
-   **When:** It activates during a "grace period" at the end of the year (e.g., Dec 15th onwards, configurable in `.env`).
-   **How:** If a request comes for a zone whose *next year's* calendar has not yet been pre-cached (e.g., a brand new zone), the system provides an instant response using the *current year's* (stale) data. Simultaneously, it triggers a background thread to fetch the new year's calendar.
-   **Benefit:** The user never experiences a loading delay or data glitch.

#### Housekeeping: Automatic Cleanup

-   **What:** A separate script (`scripts/cleanup_old_calendars.py`) ensures the database remains clean.
-   **When:** It's scheduled to run once a year, on a safe date like January 3rd.
-   **How:** It deletes all calendar data for years that are no longer current (e.g., in Jan 2026, it deletes all 2025 data). This prevents data bloat while keeping the previous year's data as a short-term backup during the critical cutover period.

## Database Schema

The primary table for the caching system is `prayer_zone_calendar`.

| Column          | Type    | Description                                                                 |
| --------------- | ------- | --------------------------------------------------------------------------- |
| `zone_id`       | TEXT    | **Primary Key**. The unique ID of the grid cell (e.g., "grid_28.6_77.2").   |
| `year`          | INTEGER | **Primary Key**. The year for which the calendar is valid (e.g., 2025).     |
| `calendar_data` | JSON    | The full 365-day calendar data fetched from the API, stored as a JSON object. |
| `created_at`    | DATETIME| Timestamp of when the record was first created.                             |
| `updated_at`    | DATETIME| Timestamp of when the record was last updated.                              |

## Setup and Installation

1.  **Clone the repository.**
2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
3.  **Set up your `.env` file:**
    Create a `.env` file in the root directory by copying `.env.example`. You will need to provide:
    *   `DATABASE_URL`: Your Supabase PostgreSQL connection string.
    *   `SECRET_KEY`: A secret key for Flask sessions.
    *   `PRAYER_API_BASE_URL`: The base URL for the Al-Adhan API (`http://api.aladhan.com/v1`).

4.  **Set up the Database in Supabase:**
    Connect to your Supabase project and run the following SQL command in the **SQL Editor** to create the necessary prayer calendar table:

    ```sql
    CREATE TABLE prayer_zone_calendar (
        zone_id VARCHAR(100) NOT NULL,
        year INTEGER NOT NULL,
        calendar_data JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
        PRIMARY KEY (zone_id, year)
    );
    ```

5.  **Run Database Migrations:**
    The application uses Flask-Migrate to manage other tables. Run the following commands to create the rest of the tables:
    ```bash
    flask db init  # (Only if you haven't already)
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```

6.  **Run the application:**
    ```bash
    flask run
    ```

## Scheduler Setup (Cron Jobs)

The "Two-Layer Defense" system relies on two scripts that need to be run automatically at scheduled times. In a production environment, the standard way to do this is using a scheduler like `cron` on Linux.

You will need to edit your server's crontab file (usually by running `crontab -e`) and add entries similar to the examples below.

**Important:** Make sure to replace `/path/to/your/project/` with the actual absolute path to the `NoorTime` directory on your server, and `/path/to/your/venv/` with the path to your Python virtual environment.

### 1. Pre-caching Script (`precache_next_year.py`)

This script pre-fetches next year's calendars. It is recommended to run it periodically during the last quarter of the year at an off-peak time (e.g., early morning on a weekend).

**Example Cron Job:**
```cron
# Runs at 2:00 AM every Sunday in October, November, and December.
# Logs output to /var/log/noortime_precache.log
0 2 * 10-12 0 /path/to/your/venv/bin/python /path/to/your/project/NoorTime/backend/scripts/precache_next_year.py >> /var/log/noortime_precache.log 2>&1
```

### 2. Cleanup Script (`cleanup_old_calendars.py`)

This script deletes old, expired calendar data from the database. It should be run once a year, after the new year has safely begun, to ensure the previous year's data was available as a backup during the cutover.

**Example Cron Job:**
```cron
# Runs at 4:00 AM on January 3rd every year.
# Logs output to /var/log/noortime_cleanup.log
0 4 3 1 * /path/to/your/venv/bin/python /path/to/your/project/NoorTime/backend/scripts/cleanup_old_calendars.py >> /var/log/noortime_cleanup.log 2>&1
```
