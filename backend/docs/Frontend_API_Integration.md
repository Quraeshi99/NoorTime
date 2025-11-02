# Frontend API Integration Guide

## 1. Overview

This guide details how the frontend application should interact with the NoorTime backend API, with a special focus on the proactive, performance-oriented features like "Rolling Push" for schedule caching.

## 2. Proactive Schedule Caching (The "Rolling Push")

To prevent a "thundering herd" problem where all clients request the new month's schedule on the 1st of the month, the backend will proactively signal to the client when the next month's schedule is ready for download.

### a. The `next_schedule_url` Field

The primary API endpoint, `/api/initial_prayer_data`, which is called on app startup, now includes a new field in its response:

```json
{
  "currentLocationName": "...",
  "prayerTimes": { ... },
  // ... other fields
  "next_schedule_url": "/api/v1/schedule/monthly?year=2025&month=4" 
}
```

- **If this field is present and not `null`**, it is a signal from the backend that the schedule for the month indicated in the URL is ready for download.
- **If this field is `null` or absent**, it means there is no new schedule ready for the client to download at this time.

### b. Required Frontend Logic

As a frontend developer, you must implement the following logic:

1.  **Check on App Load:** Every time the app loads and you call `/api/initial_prayer_data`, check for the existence of a non-null `next_schedule_url`.

2.  **Trigger Background Download:** If the URL is present, you must immediately trigger a background `GET` request to this URL. 
    - **Example:** `GET https://your-api-domain.com/api/v1/schedule/monthly?year=2025&month=4`

3.  **Cache the Response:** The response from this URL will be the complete JSON "Director's Script" for the next month. You must save this entire JSON object to the device's local storage. 
    - **Recommended Storage:** Use **IndexedDB** for its reliability and capacity for storing large JSON objects.
    - **Cache Key:** Use a clear and predictable key for the stored data, such as `schedule_{year}_{month}`. For the example above, the key would be `schedule_2025_4`.

4.  **Implement Local Cache-First Strategy:**
    - When a new month begins (e.g., it becomes April 1st), your application **must first** check its local storage (IndexedDB) for the corresponding schedule (e.g., `schedule_2025_4`).
    - **If the schedule exists in local storage**, load it directly from there and start the UI. **DO NOT** make an API call to fetch the schedule.
    - **If the schedule does not exist in local storage** (which should be a rare fallback case), only then should you make a `GET` request to `/api/v1/schedule/monthly` to fetch it from the server.

### c. Flow Diagram

```
[User opens app in March] -> [App calls /api/initial_prayer_data]
        |
        v
[Backend sees April schedule is ready, responds with `next_schedule_url`]
        |
        v
[App receives URL, triggers background GET to that URL]
        |
        v
[App receives April's JSON script, saves it to IndexedDB as `schedule_2025_4`]

------------------ TIME PASSES ------------------

[User opens app on April 1st]
        |
        v
[App checks local storage for `schedule_2025_4`]
        |
        v
[Finds it!] -> [Loads schedule from local storage, starts UI instantly]
        |
        +-----> NO API CALL NEEDED FOR SCHEDULE
```

By following this guide, the frontend application will become extremely fast and efficient, providing an instant experience on the 1st of the month and dramatically reducing the load on the backend server.
