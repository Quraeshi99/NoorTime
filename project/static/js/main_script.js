// project/static/js/main_script.js

document.addEventListener('DOMContentLoaded', function () {
    // --- DOM Element Cache ---
    const dom = {
        currentTimeEl: document.getElementById('currentTime'),
        currentDayEl: document.getElementById('currentDay'),
        timeToNextJamaatEl: document.getElementById('timeToNextJamaat'),
        nextJamaatDisplayTimeEl: document.getElementById('nextJamaatDisplayTime'),
        nextJamaatNameEl: document.getElementById('nextJamaatName'),
        nextJamaatAzanTimeEl: document.getElementById('nextJamaatAzanTime'),
        jamaatCountdownEl: document.getElementById('jamaatCountdown'),
        postJamaatCountdownEl: document.getElementById('postJamaatCountdown'),
        currentNamazStartEl: document.getElementById('currentNamazStart'),
        currentNamazNameEl: document.getElementById('currentNamazName'),
        currentNamazEndEl: document.getElementById('currentNamazEnd'),
        zawalStartTimeApiEl: document.getElementById('zawalStartTimeApi'),
        zawalEndTimeApiEl: document.getElementById('zawalEndTimeApi'),
        sahrTimeEl: document.getElementById('sahrTime'),
        iftarTimeEl: document.getElementById('iftarTime'),
        gregorianDateEl: document.getElementById('gregorianDate'),
        hijriDateEl: document.getElementById('hijriDate'),
        masjidNameDisplayEl: document.getElementById('currentApiLocationDisplay'), // Changed from masjidName to currentApiLocation
        homeLocationNameDisplayEl: document.getElementById('homeLocationNameDisplay'),
        currentTemperatureDisplayEl: document.getElementById('currentTemperatureDisplay'),
        tuluTimeApiEl: document.getElementById('tuluTimeApi'),
        gurubTimeApiEl: document.getElementById('gurubTimeApi'),
        tomorrowFajrDisplayEl: document.getElementById('tomorrowFajrAzanDisplay'), // Displaying Azan time for Tomorrow Fajr
        khutbahDisplayRowEl: document.getElementById('khutbahDisplayRow'),
        khutbahTimeDisplayEl: document.getElementById('khutbahTimeDisplay'),
        beepSound: document.getElementById('beepSound'),
        offlineIndicator: document.getElementById('offline-indicator'),
        // Location Modal Elements
        updateApiLocationBtn: document.getElementById('updateApiLocationBtn'),
        locationModal: document.getElementById('locationModal'),
        closeLocationModalBtn: document.getElementById('closeLocationModal'),
        detectLocationBtn: document.getElementById('detectLocationBtn'),
        cityInput: document.getElementById('cityInput'),
        latInput: document.getElementById('latInput'),
        lonInput: document.getElementById('lonInput'),
        submitLocationBtn: document.getElementById('submitLocationBtn'),
        geocodeErrorEl: document.getElementById('geocodeError'),
        geocodeSuccessEl: document.getElementById('geocodeSuccess'),
    };

    // --- State Variables ---
    let initialData = null;
    let currentLiveAPILocation = { // For guests or when user updates API location
        latitude: null,
        longitude: null,
        method: null, // e.g., 'Karachi', 'ISNA'
        city_name: null,
        time_format: '12h' // Default for guests
    };
    let isUserAuthenticated = false; // Will be set by initial_prayer_data
    
    // Default to a known location if nothing is stored for guest
    const APP_DEFAULT_LAT = 19.2183; // Malad, Mumbai
    const APP_DEFAULT_LON = 72.8493;
    const APP_DEFAULT_METHOD = 'Karachi'; // Default calculation method key
    const APP_DEFAULT_CITY = "Mumbai, IN";


    // --- Helper Functions ---
    function formatTime12Hour(timeStr, formatPref = '12h') {
        if (!timeStr || timeStr === "N/A" || !timeStr.includes(':')) return "N/A";
        const [hours, minutes] = timeStr.split(':');
        let h = parseInt(hours, 10);
        const m = parseInt(minutes, 10);

        if (isNaN(h) || isNaN(m)) return "N/A";

        if (formatPref === '24h') {
            return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
        } else { // 12h format
            const ampm = h >= 12 ? 'PM' : 'AM';
            const h12 = h % 12 || 12;
            return `${h12.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')} ${ampm}`;
        }
    }

    function formatCountdownTime(totalSeconds) {
        if (isNaN(totalSeconds) || totalSeconds < 0) totalSeconds = 0;
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    function playBeepSound() {
        if (dom.beepSound && dom.beepSound.readyState >= 2) { // readyState 2 (HAVE_CURRENT_DATA) or more
            dom.beepSound.play().catch(error => console.warn("Beep sound play failed:", error));
        } else if (dom.beepSound) {
            console.warn("Beep sound not ready to play.");
            // Try to load it if not already loading
            dom.beepSound.load(); 
            // You might want to play it on 'canplaythrough' event if critical
        }
    }
    
    function updateTextContent(element, text, defaultText = "N/A") {
        if (element) {
            element.textContent = text || defaultText;
        }
    }

    function updateFormattedTime(element, timeStr, formatPref) {
        updateTextContent(element, formatTime12Hour(timeStr, formatPref));
    }

    // --- UI Update Functions ---
    function updatePrayerTimesTable(prayerTimesData, formatPref) {
        const prayerKeys = ["fajr", "dhuhr", "asr", "maghrib", "isha", "jummah"];
        prayerKeys.forEach(pKey => {
            const azanEl = document.querySelector(`.prayer-azan[data-prayer="${pKey}"]`);
            const jamaatEl = document.querySelector(`.prayer-jamaat[data-prayer="${pKey}"]`);
            if (prayerTimesData && prayerTimesData[pKey]) {
                updateFormattedTime(azanEl, prayerTimesData[pKey].azan, formatPref);
                updateFormattedTime(jamaatEl, prayerTimesData[pKey].jamaat, formatPref);
            } else {
                updateTextContent(azanEl, "N/A");
                updateTextContent(jamaatEl, "N/A");
            }
        });
        // Handle Khutbah time specifically for Jummah
        if (dom.khutbahDisplayRowEl && dom.khutbahTimeDisplayEl && prayerTimesData && prayerTimesData.jummah && prayerTimesData.jummah.khutbah && prayerTimesData.jummah.khutbah !== "N/A") {
            updateFormattedTime(dom.khutbahTimeDisplayEl, prayerTimesData.jummah.khutbah, formatPref);
            dom.khutbahDisplayRowEl.style.display = 'flex'; // Show the row
        } else if (dom.khutbahDisplayRowEl) {
            dom.khutbahDisplayRowEl.style.display = 'none'; // Hide if no Khutbah time
        }
    }

    function updateOtherTimes(apiTimesData, tomorrowFajrData, formatPref) {
        if (!apiTimesData) return;
        updateFormattedTime(dom.tuluTimeApiEl, apiTimesData.Sunrise, formatPref);
        updateFormattedTime(dom.gurubTimeApiEl, apiTimesData.Sunset, formatPref);
        updateFormattedTime(dom.zawalEndTimeApiEl, apiTimesData.Zawal_End_Approx, formatPref); // Dhuhr start
        updateFormattedTime(dom.tomorrowFajrDisplayEl, tomorrowFajrData?.azan, formatPref);
        // Zawal Start is in left panel
        updateFormattedTime(dom.zawalStartTimeApiEl, apiTimesData.Zawal_Start_Approx, formatPref);
    }

    function updateDateTimeInfo(dateInfoData) {
        if (!dateInfoData) return;
        updateTextContent(dom.gregorianDateEl, dateInfoData.gregorian);
        updateTextContent(dom.hijriDateEl, dateInfoData.hijri);
    }
    
    function updateLocationAndWeather(locationName, temperature, weatherDesc) {
        updateTextContent(dom.masjidNameDisplayEl, locationName || "Current Location", "Location N/A");
        if (temperature !== null && temperature !== undefined && !isNaN(temperature)) {
            updateTextContent(dom.currentTemperatureDisplayEl, `${parseFloat(temperature).toFixed(0)}°C`, "");
        } else {
            updateTextContent(dom.currentTemperatureDisplayEl, ""); // Hide if no temp
        }
        // Weather description can be added if needed
    }

    // --- API Call and Data Handling ---
    async function fetchInitialData() {
        try {
            // Construct URL with guest's temporary location if available
            let apiUrl = '/api/initial_prayer_data';
            if (!isUserAuthenticated && currentLiveAPILocation.latitude && currentLiveAPILocation.longitude && currentLiveAPILocation.method) {
                const params = new URLSearchParams({
                    lat: currentLiveAPILocation.latitude,
                    lon: currentLiveAPILocation.longitude,
                    method: currentLiveAPILocation.method,
                    city: currentLiveAPILocation.city_name || '',
                    time_format: currentLiveAPILocation.time_format
                });
                apiUrl += `?${params.toString()}`;
            } else if (isUserAuthenticated && initialData && initialData.userPreferences) { // For logged-in user, use their saved prefs
                 const params = new URLSearchParams({
                    time_format: initialData.userPreferences.timeFormat 
                    // Lat/lon/method for logged in user are fetched from DB by backend
                });
                apiUrl += `?${params.toString()}`;
            }


            const response = await fetch(apiUrl);
            if (!response.ok) {
                console.error("Failed to fetch initial data:", response.status, response.statusText);
                updateTextContent(dom.masjidNameDisplayEl, "Error loading data", "Error");
                return;
            }
            initialData = await response.json();
            console.log("Initial Data Received:", initialData);

            isUserAuthenticated = initialData.isUserAuthenticated;
            document.title = `${initialData.currentLocationName} - Prayer Times`;
            
            const formatPref = initialData.userPreferences.timeFormat || '12h';
            // Update currentLiveAPILocation for guest if this is the first load
            if (!isUserAuthenticated && !currentLiveAPILocation.latitude) { // Only if not set by location modal
                currentLiveAPILocation.latitude = initialData.userPreferences.homeLatitude || APP_DEFAULT_LAT;
                currentLiveAPILocation.longitude = initialData.userPreferences.homeLongitude || APP_DEFAULT_LON;
                currentLiveAPILocation.method = initialData.userPreferences.calculationMethod || APP_DEFAULT_METHOD;
                currentLiveAPILocation.city_name = initialData.currentLocationName || APP_DEFAULT_CITY;
                currentLiveAPILocation.time_format = formatPref;
                saveGuestLocationToLocalStorage();
            }


            updatePrayerTimesTable(initialData.prayerTimes, formatPref);
            updateOtherTimes(initialData.apiTimesForDisplay, initialData.tomorrowFajrDisplay, formatPref);
            updateDateTimeInfo(initialData.dateInfo);
            updateLocationAndWeather(initialData.currentLocationName, initialData.apiTimesForDisplay.CurrentTemperature, initialData.apiTimesForDisplay.WeatherDescription);
            
            if(dom.homeLocationNameDisplayEl) {
                if(isUserAuthenticated && initialData.userPreferences.homeLatitude) {
                     updateTextContent(dom.homeLocationNameDisplayEl, initialData.currentLocationName, "(Home Location)");
                     // TODO: If current API location is different from home, show both distinctly.
                     // For now, if logged in, currentLocationName should be their home location.
                } else if (isUserAuthenticated) {
                    updateTextContent(dom.homeLocationNameDisplayEl, "(Set Home Location in Settings)");
                } else {
                     updateTextContent(dom.homeLocationNameDisplayEl, "Guest Mode (Set Home in Settings by Logging In)");
                }
            }


            // Fetch live data immediately after initial data
            fetchLiveData(); 
            // Start interval for live data (clock, next prayer countdown)
            setInterval(fetchLiveData, 1000);
            // Periodically refresh less dynamic data (like daily prayer table, dates)
            setInterval(fetchInitialData, 15 * 60 * 1000); // Every 15 minutes

        } catch (error) {
            console.error("Error fetching or processing initial data:", error);
            updateTextContent(dom.masjidNameDisplayEl, "Error processing data", "Error");
        }
    }

    async function fetchLiveData() {
        if (!initialData) { // Don't run if initial data hasn't loaded
            // console.log("Waiting for initial data before fetching live data...");
            return;
        }
        try {
            let apiUrl = '/api/live_data';
            // Pass current API location for guests, or let backend use logged-in user's defaults
            const params = new URLSearchParams();
            if (!isUserAuthenticated && currentLiveAPILocation.latitude && currentLiveAPILocation.longitude && currentLiveAPILocation.method) {
                params.append('lat', currentLiveAPILocation.latitude);
                params.append('lon', currentLiveAPILocation.longitude);
                params.append('method', currentLiveAPILocation.method);
            }
            // Always send time_format preference
             params.append('time_format', currentLiveAPILocation.time_format || (initialData.userPreferences ? initialData.userPreferences.timeFormat : '12h'));

            if (Array.from(params).length > 0) {
                apiUrl += `?${params.toString()}`;
            }

            const response = await fetch(apiUrl);
            if (!response.ok) {
                console.warn("Failed to fetch live data:", response.status, response.statusText);
                if(dom.currentTimeEl) updateTextContent(dom.currentTimeEl, "--:--:-- ERR");
                return;
            }
            const liveData = await response.json();
            // console.log("Live Data:", liveData);

            const formatPref = currentLiveAPILocation.time_format || (initialData.userPreferences ? initialData.userPreferences.timeFormat : '12h');

            updateTextContent(dom.currentTimeEl, liveData.currentTime);
            updateTextContent(dom.currentDayEl, liveData.currentDay);

            // Next Prayer Logic
            let nextPrayerName = liveData.nextPrayer.name;
            let nextAzan = liveData.nextPrayer.azanTime;
            let nextJamaat = liveData.nextPrayer.jamaatTime;
            let timeToJamaatMins = liveData.nextPrayer.timeToJamaatMinutes;

            if (liveData.nextPrayer.isNextDayFajr && initialData.tomorrowFajrDisplay) {
                 // Backend now sends pre-calculated "Fajr (Tomorrow)" with its times
                 // No need to re-fetch or recalculate here if backend handles it well.
                 // Ensure timeToJamaatMinutes is correct for tomorrow.
                 const nowDT = new Date();
                 const tomorrowDT = new Date(nowDT);
                 tomorrowDT.setDate(nowDT.getDate() + 1);
                 const [fH, fM] = nextJamaat.split(':'); // Use Jamaat time sent by backend for Fajr (Tomorrow)
                 tomorrowDT.setHours(parseInt(fH), parseInt(fM), 0, 0);
                 const diffMs = tomorrowDT.getTime() - nowDT.getTime();
                 if (diffMs > 0) {
                     timeToJamaatMins = Math.floor(diffMs / (1000 * 60));
                 } else {
                     timeToJamaatMins = 0; // Or some indicator it's very close / passed
                 }
            }
            
            updateTextContent(dom.timeToNextJamaatEl, `Next: ${nextPrayerName} in ${timeToJamaatMins} min`);
            updateFormattedTime(dom.nextJamaatDisplayTimeEl, nextJamaat, formatPref);
            updateTextContent(dom.nextJamaatNameEl, nextPrayerName);
            updateFormattedTime(dom.nextJamaatAzanTimeEl, nextAzan, formatPref);

            // Countdowns
            if (liveData.nextPrayer.isJamaatCountdownActive) {
                updateTextContent(dom.jamaatCountdownEl, formatCountdownTime(liveData.nextPrayer.jamaatCountdownSeconds));
                dom.jamaatCountdownEl.style.display = 'block';
                if (liveData.nextPrayer.jamaatCountdownSeconds === 1 && dom.beepSound) {
                    playBeepSound();
                }
            } else {
                if (dom.jamaatCountdownEl) dom.jamaatCountdownEl.style.display = 'none';
            }

            if (liveData.nextPrayer.isPostJamaatCountdownActive) {
                updateTextContent(dom.postJamaatCountdownEl, formatCountdownTime(liveData.nextPrayer.postJamaatCountdownSeconds));
                dom.postJamaatCountdownEl.style.display = 'block';
            } else {
                if (dom.postJamaatCountdownEl) dom.postJamaatCountdownEl.style.display = 'none';
            }
            // Priority for pre-jamaat countdown
            if (liveData.nextPrayer.isJamaatCountdownActive && dom.postJamaatCountdownEl) {
                dom.postJamaatCountdownEl.style.display = 'none';
            }
            
            // Current Namaz Period
            updateFormattedTime(dom.currentNamazStartEl, liveData.currentNamazPeriod.start, formatPref);
            updateTextContent(dom.currentNamazNameEl, liveData.currentNamazPeriod.name);
            updateFormattedTime(dom.currentNamazEndEl, liveData.currentNamazPeriod.end, formatPref);

            // Fasting Times (usually don't change intra-day, but API provides them)
            updateFormattedTime(dom.sahrTimeEl, liveData.fastingTimes.sahr, formatPref);
            updateFormattedTime(dom.iftarTimeEl, liveData.fastingTimes.iftar, formatPref);

        } catch (error) {
            console.error("Error fetching or processing live data:", error);
            if(dom.currentTimeEl) updateTextContent(dom.currentTimeEl, "--:--:-- ERR");
        }
    }
    
    // --- Location Modal Logic ---
    if (dom.updateApiLocationBtn) {
        dom.updateApiLocationBtn.addEventListener('click', () => dom.locationModal.classList.remove('hidden'));
    }
    if (dom.closeLocationModalBtn) {
        dom.closeLocationModalBtn.addEventListener('click', () => dom.locationModal.classList.add('hidden'));
    }
    if (dom.detectLocationBtn) {
        dom.detectLocationBtn.addEventListener('click', () => {
            if (navigator.geolocation) {
                dom.geocodeSuccessEl.classList.add('hidden');
                dom.geocodeErrorEl.textContent = 'Detecting location...';
                dom.geocodeErrorEl.classList.remove('hidden');
                navigator.geolocation.getCurrentPosition(async position => {
                    currentLiveAPILocation.latitude = position.coords.latitude.toFixed(4);
                    currentLiveAPILocation.longitude = position.coords.longitude.toFixed(4);
                    // Try to get city name from lat/lon for display (reverse geocoding - harder)
                    // For now, just use lat/lon. We can try a reverse geocode API later.
                    currentLiveAPILocation.city_name = `Lat: ${currentLiveAPILocation.latitude}, Lon: ${currentLiveAPILocation.longitude}`;
                    // Keep user's or default calculation method
                    currentLiveAPILocation.method = initialData?.userPreferences?.calculationMethod || APP_DEFAULT_METHOD;
                    
                    dom.geocodeErrorEl.classList.add('hidden');
                    dom.geocodeSuccessEl.textContent = `Location detected: ${currentLiveAPILocation.city_name}. Fetching new times...`;
                    dom.geocodeSuccessEl.classList.remove('hidden');
                    
                    if (!isUserAuthenticated) saveGuestLocationToLocalStorage();
                    await fetchInitialData(); // Re-fetch all data with new location
                    setTimeout(() => dom.locationModal.classList.add('hidden'), 1500);

                }, error => {
                    console.error("Geolocation error:", error);
                    dom.geocodeErrorEl.textContent = `Error detecting location: ${error.message}. Please enter manually.`;
                });
            } else {
                dom.geocodeErrorEl.textContent = 'Geolocation is not supported by your browser.';
                dom.geocodeErrorEl.classList.remove('hidden');
            }
        });
    }
    if (dom.submitLocationBtn) {
        dom.submitLocationBtn.addEventListener('click', async () => {
            const city = dom.cityInput.value.trim();
            const lat = parseFloat(dom.latInput.value);
            const lon = parseFloat(dom.lonInput.value);

            dom.geocodeErrorEl.classList.add('hidden');
            dom.geocodeSuccessEl.classList.add('hidden');

            if (city) {
                try {
                    dom.geocodeErrorEl.textContent = `Geocoding city: ${city}...`;
                    dom.geocodeErrorEl.classList.remove('hidden');
                    const response = await fetch(`/api/geocode?city=${encodeURIComponent(city)}`);
                    const geoData = await response.json();
                    if (response.ok && !geoData.error) {
                        currentLiveAPILocation.latitude = parseFloat(geoData.latitude).toFixed(4);
                        currentLiveAPILocation.longitude = parseFloat(geoData.longitude).toFixed(4);
                        currentLiveAPILocation.city_name = `${geoData.city_name}, ${geoData.country}`;
                        currentLiveAPILocation.method = initialData?.userPreferences?.calculationMethod || APP_DEFAULT_METHOD;
                        
                        dom.geocodeErrorEl.classList.add('hidden');
                        dom.geocodeSuccessEl.textContent = `Location set to: ${currentLiveAPILocation.city_name}. Fetching new times...`;
                        dom.geocodeSuccessEl.classList.remove('hidden');

                        if (!isUserAuthenticated) saveGuestLocationToLocalStorage();
                        await fetchInitialData();
                        setTimeout(() => dom.locationModal.classList.add('hidden'), 1500);
                    } else {
                        dom.geocodeErrorEl.textContent = geoData.error || "Could not find city.";
                        dom.geocodeErrorEl.classList.remove('hidden');
                    }
                } catch (err) {
                    console.error("Geocoding API error:", err);
                    dom.geocodeErrorEl.textContent = "Error contacting geocoding service.";
                    dom.geocodeErrorEl.classList.remove('hidden');
                }
            } else if (!isNaN(lat) && !isNaN(lon)) {
                currentLiveAPILocation.latitude = lat.toFixed(4);
                currentLiveAPILocation.longitude = lon.toFixed(4);
                currentLiveAPILocation.city_name = `Lat: ${lat}, Lon: ${lon}`;
                currentLiveAPILocation.method = initialData?.userPreferences?.calculationMethod || APP_DEFAULT_METHOD;
                
                dom.geocodeSuccessEl.textContent = `Location set to Lat/Lon. Fetching new times...`;
                dom.geocodeSuccessEl.classList.remove('hidden');

                if (!isUserAuthenticated) saveGuestLocationToLocalStorage();
                await fetchInitialData();
                setTimeout(() => dom.locationModal.classList.add('hidden'), 1500);
            } else {
                dom.geocodeErrorEl.textContent = "Please enter a city name or valid Latitude/Longitude.";
                dom.geocodeErrorEl.classList.remove('hidden');
            }
        });
    }
    
    // --- Guest Mode: LocalStorage for API Location & Time Format ---
    function loadGuestLocationFromLocalStorage() {
        if (!isUserAuthenticated) { // Only for guests
            const guestPrefs = localStorage.getItem('prayerTimesGuestPrefs');
            if (guestPrefs) {
                try {
                    const parsedPrefs = JSON.parse(guestPrefs);
                    currentLiveAPILocation.latitude = parsedPrefs.latitude || APP_DEFAULT_LAT;
                    currentLiveAPILocation.longitude = parsedPrefs.longitude || APP_DEFAULT_LON;
                    currentLiveAPILocation.method = parsedPrefs.method || APP_DEFAULT_METHOD;
                    currentLiveAPILocation.city_name = parsedPrefs.city_name || APP_DEFAULT_CITY;
                    currentLiveAPILocation.time_format = parsedPrefs.time_format || '12h';
                    console.log("Loaded guest preferences from localStorage:", currentLiveAPILocation);
                } catch (e) {
                    console.error("Error parsing guest prefs from localStorage", e);
                    setDefaultGuestLocation();
                }
            } else {
                setDefaultGuestLocation();
            }
        }
    }
    function setDefaultGuestLocation() {
         currentLiveAPILocation.latitude = APP_DEFAULT_LAT;
         currentLiveAPILocation.longitude = APP_DEFAULT_LON;
         currentLiveAPILocation.method = APP_DEFAULT_METHOD;
         currentLiveAPILocation.city_name = APP_DEFAULT_CITY;
         currentLiveAPILocation.time_format = '12h';
         console.log("Set default guest preferences:", currentLiveAPILocation);
    }

    function saveGuestLocationToLocalStorage() {
        if (!isUserAuthenticated) { // Only for guests
            try {
                localStorage.setItem('prayerTimesGuestPrefs', JSON.stringify(currentLiveAPILocation));
                console.log("Saved guest preferences to localStorage:", currentLiveAPILocation);
            } catch (e) {
                console.error("Error saving guest prefs to localStorage", e);
            }
        }
    }

    // --- Offline/Online Detection ---
    function updateOnlineStatus() {
        if (dom.offlineIndicator) {
            if (navigator.onLine) {
                dom.offlineIndicator.style.display = 'none';
                console.log("App is online.");
                // Optionally, trigger a data refresh if coming back online
                // fetchInitialData(); // Be careful not to cause too many requests
            } else {
                dom.offlineIndicator.style.display = 'block';
                console.log("App is offline.");
            }
        }
    }
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    

    // --- PWA: Service Worker Registration ---
    // const swPathForRegister = '/service-worker.js'; // Ensure this path is correct
    // Using the path passed from base_layout.html (if set)
    const swPathFromTemplate = typeof serviceWorkerPath !== 'undefined' ? serviceWorkerPath : '/service-worker.js';

    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register(swPathFromTemplate) // Use the variable from template
                .then(registration => {
                    console.log('Service Worker registered successfully with scope:', registration.scope);
                })
                .catch(error => {
                    console.error('Service Worker registration failed:', error);
                });
        });
    }

    // --- Initializations ---
    loadGuestLocationFromLocalStorage(); // Load guest prefs before first fetchInitialData
    fetchInitialData(); // Main data loading function
    updateOnlineStatus(); // Set initial online/offline status

    // Font loading class (already in index.html, this is just a fallback or if managed by JS)
    // document.body.classList.add('fonts-loaded'); // Or use the more robust method from index.html
});