# NoorTime Prayer Time Settings Architecture

## Overview

This document outlines the flexible and hierarchical system used by the NoorTime application to calculate and display prayer times. The system is designed to provide accurate, user-configurable prayer times for a global Muslim audience, accounting for different jurisprudential schools (Fiqh) and geographical challenges like high latitudes.

The core principle is to fetch raw prayer time data from a reliable external source (Al Adhan API) and then apply user-defined settings on top of it. The system heavily relies on caching to ensure performance and reliability.

## Settings Hierarchy

The application determines which prayer time settings to use based on a clear priority system. This ensures that the user's intent is always respected.

1.  **Followed Masjid (Highest Priority):** If a logged-in user has set a default Masjid to follow, the application will **exclusively** use the location and prayer time settings configured by that Masjid's administrator. The user's personal settings are ignored.

2.  **Custom Location Search:** If the user is not following a default Masjid and performs a one-time search for a location, the application will use the coordinates of the searched location. It will then apply the user's **own saved calculation settings** (Method, Asr Fiqh, etc.) to this new location.

3.  **User's Personal Saved Settings:** If the user is not following a Masjid or performing a custom search, the application uses the user's saved default location and prayer time calculation settings from their profile.

4.  **Application Default (Lowest Priority):** If none of the above conditions are met (e.g., a guest user), the application will use a default location and calculation method defined in the application's configuration.

## User-Configurable Settings

To provide maximum flexibility, the following settings are stored for each user and can be configured through a proposed "Advanced Settings" screen in the app.

### 1. Calculation Method

This is the primary method for calculating Fajr and Isha times. The system supports two modes for selecting this method:

#### a) Automatic Mode (Default)

This is the recommended setting for most users as it requires zero configuration.

*   **How it works:** The application automatically determines the user's country from their location. It then uses a mapping file (`project/static/country_method_map.json`) to select the most common and appropriate calculation method for that country.
*   **Example:** If the user is in India (`IN`), the system will automatically use the `Karachi` method (ID: 1). If they are in the USA (`US`), it will use `ISNA` (ID: 2).
*   **Benefit:** Provides a highly accurate, localized experience out-of-the-box without confusing the user with technical choices.

#### b) Manual Selection

For advanced users or those with specific Fiqhi needs, the app provides an option to manually select a calculation method.

*   **Database Column:** `user.default_calculation_method_id`
*   **Options:** The user can choose from a list of internationally recognized methods, including:
    *   Muslim World League (ID: 3)
    *   Islamic Society of North America (ISNA) (ID: 2)
    *   Egyptian General Authority of Survey (ID: 5)
    *   University of Islamic Sciences, Karachi (ID: 1)
    *   Umm al-Qura University, Makkah (ID: 4)
    *   And many others.

### 2. Asr Juristic (Fiqh)

This setting determines the timing of the Asr prayer.

*   **Database Column:** `user_settings.asr_juristic`
*   **Options:**
    *   **Standard (Jumhoor):** Asr begins when an object's shadow is equal to its length. Corresponds to `school=0` in the API call.
    *   **Hanafi:** Asr begins when an object's shadow is twice its length. Corresponds to `school=1` in the API call.

### 3. High Latitude Adjustment Method

This setting is crucial for users in northern regions (e.g., Europe, Canada) where twilight signs for Fajr and Isha may be absent during summer months.

*   **Database Column:** `user_settings.high_latitude_method`
*   **UI/UX:** This option should only be visible to users whose location is detected to be above a certain latitude (e.g., 48° N) to avoid confusing other users.
*   **Options:**
    *   **Middle of the Night:** The period between Sunset and Sunrise is divided in half to determine Fajr and Isha.
    *   **One-Seventh of the Night:** The night is divided into seven parts. Isha is at the end of the first part, and Fajr is at the beginning of the last part.
    *   **Angle Based:** A twilight angle is used to extrapolate the prayer times even when the sun does not reach that angle.

## A-to-Z Data Flow

1.  A request is made to the `/api/initial_prayer_data` endpoint.
2.  The `get_prayer_settings_from_user` helper function determines the correct `latitude`, `longitude`, `method_id`, `asr_juristic_id`, and `high_latitude_method_id` based on the hierarchy described above.
3.  These parameters are passed to the `prayer_time_service`.
4.  The service creates a unique `composite_method_key` (e.g., "3-0-1") from these settings.
5.  It checks the `PrayerZoneCalendar` table for a cached calendar matching the `zone_id`, `year`, and the `composite_method_key`.
6.  If a cache miss occurs, the `aladhan_adapter` is called with all five parameters.
7.  The adapter constructs a URL with these parameters (e.g., `...&method=3&school=0&latitudeAdjustmentMethod=1`) and fetches the data from the Al Adhan API.
8.  The fetched yearly calendar is saved to the database against the composite key for future requests.
9.  The final data is returned to the user.
