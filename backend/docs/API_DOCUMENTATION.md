# NoorTime API Documentation

This document provides details on specific API endpoints to guide frontend development.

---

## Daily Prayer Times Endpoint

This endpoint is the primary source for the day's prayer schedule and date information.

*   **Endpoint:** `GET /api/v1/prayer-times/daily` (Assumed endpoint)
*   **Authentication:** Required (User token)
*   **Query Parameters:**
    *   `lat`: (Float) User's latitude.
    *   `lon`: (Float) User's longitude.
    *   `date`: (String) Date in `DD-MM-YYYY` format. If not provided, defaults to today.

### Success Response (200 OK)

**Body:**

```json
{
  "timings": {
    "Fajr": "05:41",
    "Sunrise": "07:01",
    "Dhuhr": "12:23",
    "Asr": "15:28",
    "Sunset": "17:45",
    "Maghrib": "17:45",
    "Isha": "19:05",
    "Imsak": "05:31",
    "Midnight": "00:23"
  },
  "date": {
    "readable": "30 Oct 2025",
    "timestamp": "1730252400",
    "gregorian": {
      "date": "30-10-2025",
      "format": "DD-MM-YYYY",
      "day": "30",
      "weekday": { "en": "Thursday" },
      "month": { "number": 10, "en": "October" },
      "year": "2025"
    },
    "hijri": {
      "date": "08-05-1447",
      "format": "DD-MM-YYYY",
      "day": "08",
      "weekday": { "en": "Al Khamis", "ar": "الخميس" },
      "month": { "number": 5, "en": "Jumada Al-Awwal", "ar": "جمادى الأولى" },
      "year": "1447"
    }
  }
}
```

### Fields Explanation

| Field       | Type   | Description                                                                                                                                                              |
| ----------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `timings`   | Object | An object containing the raw prayer times for the day.                                                                                                                   |
| `date`      | Object | An object containing detailed date information. **This should be used to display both Gregorian and Hijri dates.**                                                       |
| `...gregorian` | Object | Contains the full Gregorian date details. Use `gregorian.date` for a simple display or other fields for a richer format (e.g., "Thursday, 30 October 2025").             |
| `...hijri`  | Object | Contains the full Hijri date details. Use `hijri.date` for a simple display or other fields for a richer format (e.g., "8 Jumada Al-Awwal 1447"). |

---

## Next Prayer Information Endpoint

This endpoint provides all the necessary real-time information to power the "Next Prayer" widget, including various countdown states.

*   **Endpoint:** `GET /api/v1/prayer-times/next` (Assumed endpoint)
*   **Authentication:** Required (User token)
*   **Query Parameters:**
    *   `lat`: (Float) User's latitude.
    *   `lon`: (Float) User's longitude.

### Success Response (200 OK)

**Body:**

```json
{
  "next_prayer_info": {
    "name": "Asr",
    "azanTime": "16:20",
    "jamaatTime": "16:30",
    "timeToJamaatMinutes": 5,
    "isNextDayFajr": false,
    "isJamaatCountdownActive": false,
    "jamaatCountdownSeconds": 0,
    "isPostJamaatCountdownActive": false,
    "postJamaatCountdownSeconds": 0
  }
}
```

### Fields Explanation

| Field                         | Type    | Description                                                                                                                              |
| ----------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                        | String  | The display name of the next prayer (e.g., "Asr", "Jummah", "Fajr (Tomorrow)").                                                          |
| `azanTime`                    | String  | The formatted Azan time for the next prayer (e.g., "16:20").                                                                             |
| `jamaatTime`                  | String  | The formatted Jamaat time for the next prayer (e.g., "16:30").                                                                           |
| `timeToJamaatMinutes`         | Number  | The number of minutes remaining until the next Jamaat. This is used for the normal countdown.                                            |
| `isNextDayFajr`               | Boolean | `true` if the next prayer is the Fajr of the following day (i.e., after Isha).                                                           |
| `isJamaatCountdownActive`     | Boolean | **Signal for "Alert" state.** `true` only when the Jamaat is less than 2 minutes away.                                                   |
| `jamaatCountdownSeconds`      | Number  | The exact number of seconds remaining to Jamaat. Only relevant when `isJamaatCountdownActive` is `true`.                                 |
| `isPostJamaatCountdownActive` | Boolean | **Signal for "Just Passed" state.** `true` for 10 minutes after a Jamaat time has passed.                                                |
| `postJamaatCountdownSeconds`  | Number  | A countdown value for the 10-minute post-jamaat window. Only relevant when `isPostJamaatCountdownActive` is `true`.                      |

---

## Frontend Logic for the "Smart Box" Widget

The `next_prayer_info` object is designed to power a single, stateful "Smart Box" widget. Use the boolean flags to determine which UI state to display. The states are mutually exclusive.

### State 1: Normal Countdown

*   **Condition:** `isJamaatCountdownActive` is `false` AND `isPostJamaatCountdownActive` is `false`.
*   **UI:** Display a standard countdown using the `timeToJamaatMinutes` value.
*   **Example Display:** "25 min to Asr Jamaat"

### State 2: Alert Countdown (Live Timer)

*   **Condition:** `isJamaatCountdownActive` is `true`.
*   **UI:** Hide the normal countdown and display a live, second-by-second timer using the `jamaatCountdownSeconds` value. This state takes precedence over the normal state.
*   **Example Display:** "Jamaat in: 1:29"

### State 3: "Just Passed" Info

*   **Condition:** `isPostJamaatCountdownActive` is `true`.
*   **UI:** Display information indicating that the prayer time has recently passed. You can calculate the minutes/seconds passed from the `postJamaatCountdownSeconds` value (`time_passed = 600 - postJamaatCountdownSeconds`).
*   **Example Display:** "Asr Jamaat passed 4 mins ago"

By following this logic, the frontend will provide a clean, intuitive, and highly informative user experience using a single UI component that intelligently changes its content.