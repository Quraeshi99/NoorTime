# API Documentation: Geocoding and Location Management

## Core Principle: The "Fixed" User Location

This application follows a "Fixed Location" or "Golden Location" principle. The user's saved location in their profile is the single source of truth and **should not be updated automatically**. It should only change when the user performs an explicit action to change it. This ensures that a user's (e.g., a mosque admin's) carefully calibrated prayer times do not change if they travel.

---

## Recommended Frontend Workflow

### 1. On Application Start

- **Action:** Call the `/api/initial_prayer_data` endpoint **without** any `lat` or `lon` query parameters.
- **Result:** The backend will automatically detect the logged-in user and use their saved "Golden Location". If the user is a guest, it will use the server's default location.

### 2. Changing the Location

This functionality should be placed in a **Settings page**, not on the main dashboard, as it's an infrequent and important action.

**Flow:**
1.  User navigates to "Settings" and clicks a "Change Location" button.
2.  The app presents two options: "Use Current GPS Location" or "Search for a City".

**a) If "Use Current GPS Location":**
   1.  The frontend requests GPS permission from the device.
   2.  **(Optional but Recommended)** Send the obtained coordinates to the new `/api/reverse-geocode` endpoint (to be created) to get a human-readable address.
   3.  Show a confirmation to the user: "Set your location to [Address from Reverse Geocode]?".
   4.  Upon confirmation, send the new `lat`, `lon`, and `city_name` to the `/api/client/settings` endpoint to save them permanently.

**b) If "Search for a City":**
   1.  The user types in a search box.
   2.  The frontend uses **debouncing** (see below) to call the `/api/geocode/autocomplete` endpoint and show suggestions.
   3.  The user selects a city.
   4.  The frontend calls `/api/geocode` with the selected city to get its precise coordinates.
   5.  The frontend sends the new `lat`, `lon`, and `city_name` to the `/api/client/settings` endpoint to be saved.

---

## API Endpoints

### 1. Geocode a City
- **Purpose:** Get coordinates for a specific city name. Used in the "Search for a City" flow.
- **Method:** `GET`
- **URL:** `/api/geocode`
- **Query Parameters:** `city=<city_name>`
- **Example:** `GET /api/geocode?city=Mumbai`
- **Response:**
  ```json
  {
    "city": "Mumbai",
    "country": "India",
    "lat": 19.0760,
    "lon": 72.8777
  }
  ```

### 2. Autocomplete Suggestions
- **Purpose:** Get real-time suggestions as the user types.
- **Method:** `GET`
- **URL:** `/api/geocode/autocomplete`
- **Query Parameters:** `query=<search_text>`
- **Example:** `GET /api/geocode/autocomplete?query=Del`
- **Response:** An array of location objects from the LocationIQ API.

---

## Frontend Implementation Guide: Debouncing

To use the autocomplete feature efficiently, you must implement "debouncing".

**HTML:**
```html
<input type="text" id="citySearch" placeholder="Search for a city...">
<div id="suggestions"></div>
```

**JavaScript Example:**
```javascript
const searchInput = document.getElementById('citySearch');
const suggestionsPanel = document.getElementById('suggestions');
let debounceTimer;

searchInput.addEventListener('input', (e) => {
  const query = e.target.value;
  clearTimeout(debounceTimer);

  if (query.length < 2) {
    suggestionsPanel.innerHTML = '';
    return;
  }

  debounceTimer = setTimeout(() => {
    fetch(`/api/geocode/autocomplete?query=${query}`)
      .then(response => response.json())
      .then(data => {
        // Code to display suggestions
      })
      .catch(err => console.error(err));
  }, 400); // 400ms debounce time
});
```