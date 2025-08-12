# Client-Side API Documentation

**Version**: 2.1 (Granular Permissions)

This document provides details on the API endpoints relevant for Client-side applications.

---

## API Access Details

To connect your frontend application to this backend, you will need the following:

1.  **Live Backend URL (Your API Endpoint):**
    *   This is the base URL where your backend API is deployed.
    *   **Please replace `YOUR_LIVE_BACKEND_URL_HERE` with your actual deployed backend URL.**
    *   Example: `https://api.yourdomain.com`
    ```
    YOUR_LIVE_BACKEND_URL_HERE
    ```

2.  **Supabase Anon Key (For Authentication):**
    *   This key is required to initialize the Supabase client in your frontend for user authentication (login, register).
    *   You can find this in your Supabase project settings.
    *   **Please replace `YOUR_SUPABASE_ANON_KEY_HERE` with your actual Supabase Anon Key.**
    ```
    YOUR_SUPABASE_ANON_KEY_HERE
    ```

---

## Authentication & Permissions

All protected requests must include an `Authorization` header with a JWT from Supabase:
`Authorization: Bearer <your_supabase_jwt>`

Access to specific API endpoints is now controlled by granular permissions. A user must possess the required permission to access a protected endpoint.

This documentation primarily focuses on the **Client** role and the permissions typically associated with it. For Management and Super Admin roles and their associated permissions, please refer to the `management_api_documentation.md`.

---

## Public API Endpoints (`/api`)

These endpoints can be accessed by anyone.

### 1. Get Initial Prayer Data

- **Endpoint**: `GET /initial_prayer_data`
- **Description**: Fetches all necessary data for the initial page load. If called with a valid token, it will use the authenticated user's saved preferences.
- **Success Response (200 OK)**:
  ```json
  {
    "currentLocationName": "Custom Location",
    "prayerTimes": {
      "fajr": { "azan": "05:00", "jamaat": "05:15" },
      "dhuhr": { "azan": "13:00", "jamaat": "13:15" },
      "asr": { "azan": "17:00", "jamaat": "17:15" },
      "maghrib": { "azan": "19:00", "jamaat": "19:05" },
      "isha": { "azan": "20:30", "jamaat": "20:45" },
      "jummah": { "azan": "13:00", "khutbah": "13:15", "jamaat": "13:30" },
      "chasht": { "azan": "06:20", "jamaat": "N/A" } // New Chasht time
    },
    "dateInfo": { ... },
    "tomorrowFajrDisplay": { ... },
    "userPreferences": { ... },
    "isUserAuthenticated": false
  }
  ```

### 2. Geocode City Name

- **Endpoint**: `GET /geocode`
- **Description**: Converts a city name into latitude and longitude.

---

## Client API Endpoints (`/api/client`)

These endpoints require authentication and specific permissions.

### 1. Update Client Settings

- **Endpoint**: `POST /client/settings`
- **Required Permission**: `can_update_own_settings`
- **Description**: Allows an authenticated user (Client) to update their personal profile and prayer time settings.
- **Request Body (JSON)**:
  ```json
  {
    "name": "Updated Name",
    "default_city_name": "New City",
    "settings": {
        "fajr_is_fixed": false,
        "fajr_azan_offset": 15
    }
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Settings updated successfully."
  }
  ```