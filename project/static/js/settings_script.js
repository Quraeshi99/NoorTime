// project/static/js/settings_script.js

document.addEventListener('DOMContentLoaded', function () {
    const settingsForm = document.getElementById('settingsForm');
    const saveAllSettingsButton = document.getElementById('saveAllSettingsButton');
    
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContentPanels = document.querySelectorAll('.tab-content-panel');
    const prayerSettingCards = document.querySelectorAll('.prayer-setting-card');
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    // --- Helper Functions ---
    function parseTimeToTotalMinutes(timeStr) {
        if (!timeStr || !timeStr.includes(':')) return 0;
        const [h, m] = timeStr.split(':').map(Number);
        return h * 60 + m;
    }
    function formatMinutesToHHMM(totalMinutes) {
        if (isNaN(totalMinutes) || totalMinutes === null) return "--:--";
        const hours = Math.floor(totalMinutes / 60) % 24;
        const minutes = totalMinutes % 60;
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    }
    function addMinutesToHHMM(baseTimeStr, minutesToAddStr) {
        const minutesToAdd = parseInt(minutesToAddStr);
        if (!baseTimeStr || baseTimeStr === "N/A" || baseTimeStr === "--:--" || isNaN(minutesToAdd)) return "--:--";
        const baseTotalMinutes = parseTimeToTotalMinutes(baseTimeStr);
        if (isNaN(baseTotalMinutes)) return "--:--";
        const newTotalMinutes = baseTotalMinutes + minutesToAdd;
        return formatMinutesToHHMM(newTotalMinutes);
    }

    // --- Tab Navigation Logic ---
    function switchTab(tabId) {
        tabButtons.forEach(tab => {
            const isSelected = tab.dataset.tab === tabId;
            tab.classList.toggle('active', isSelected);
            tab.setAttribute('aria-selected', isSelected);
        });
        tabContentPanels.forEach(panel => {
            panel.classList.toggle('hidden', panel.id !== `${tabId}-content`);
        });
    }

    if (tabButtons.length > 0 && tabContentPanels.length > 0) {
        tabButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                event.stopPropagation();
                const tabId = button.dataset.tab;
                switchTab(tabId);
                history.pushState(null, null, `#${tabId}`);
            });
        });

        tabContentPanels.forEach(panel => {
            panel.addEventListener('click', (event) => {
                if (event.target.tagName.toLowerCase() === 'a') {
                    event.stopPropagation();
                }
            });
        });

        const currentHash = window.location.hash.substring(1);
        if (currentHash) {
            switchTab(currentHash);
        } else {
            switchTab(tabButtons[0].dataset.tab);
        }
    }

    // --- Prayer Settings: Toggle Fixed vs Offset & Update Calculated Times ---
    function updateCalculatedTimesForPrayerUI(prayerKey) {
        const azanOffsetInput = document.getElementById(`${prayerKey}_azan_offset`);
        const calcAzanEl = document.getElementById(`${prayerKey}-calc-azan-home`);
        const jamaatOffsetInput = document.getElementById(`${prayerKey}_jamaat_offset`);
        const calcJamaatEl = document.getElementById(`${prayerKey}-calc-jamaat-home`);

        if (!apiTimesForRef || !calcAzanEl || !calcJamaatEl) return;

        let calculatedAzanTimeStr = "--:--";
        if (azanOffsetInput) {
            const apiPrayerName = prayerKey.charAt(0).toUpperCase() + prayerKey.slice(1);
            const apiStartTimeStr = apiTimesForRef[apiPrayerName] || 
                                  (prayerKey === 'maghrib' ? apiTimesForRef['Sunset'] : null) ||
                                  apiTimesForRef[apiPrayerName + '_Start']; // Fallback
            calculatedAzanTimeStr = addMinutesToHHMM(apiStartTimeStr, azanOffsetInput.value);
            calcAzanEl.textContent = calculatedAzanTimeStr;
        }

        if (jamaatOffsetInput) {
            // Base for Jamaat is the calculated Azan time from the offset mode
            calcJamaatEl.textContent = addMinutesToHHMM(calculatedAzanTimeStr, jamaatOffsetInput.value);
        }
    }

    prayerSettingCards.forEach(card => {
        const prayerKey = card.id.split('-settings-card')[0];
        if (prayerKey === 'jummah') return;

        const fixedInputsDiv = card.querySelector(`#${prayerKey}-fixed-settings-inputs`);
        const offsetInputsDiv = card.querySelector(`#${prayerKey}-offset-settings-inputs`);
        const modeRadios = card.querySelectorAll(`.settings-mode-radio[data-prayer="${prayerKey}"]`);

        modeRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (this.value === 'true') { // Fixed mode
                    fixedInputsDiv?.classList.remove('hidden');
                    offsetInputsDiv?.classList.add('hidden');
                } else { // Offset mode
                    fixedInputsDiv?.classList.add('hidden');
                    offsetInputsDiv?.classList.remove('hidden');
                }
                updateCalculatedTimesForPrayerUI(prayerKey);
            });
        });

        // Add event listeners to offset minute inputs to update calculated times
        const azanOffsetInput = document.getElementById(`${prayerKey}_azan_offset`);
        const jamaatOffsetInput = document.getElementById(`${prayerKey}_jamaat_offset`);
        if (azanOffsetInput) azanOffsetInput.addEventListener('input', () => updateCalculatedTimesForPrayerUI(prayerKey));
        if (jamaatOffsetInput) jamaatOffsetInput.addEventListener('input', () => updateCalculatedTimesForPrayerUI(prayerKey));
        
        // Initial update of calculated times if in offset mode
        if (offsetInputsDiv && !offsetInputsDiv.classList.contains('hidden')) {
            updateCalculatedTimesForPrayerUI(prayerKey);
        }
    });
    
    // --- Form Submission Logic ---
    if (saveAllSettingsButton && settingsForm) {
        saveAllSettingsButton.addEventListener('click', async function(event) {
            event.preventDefault();
            saveAllSettingsButton.disabled = true;
            saveAllSettingsButton.innerHTML = `
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...`;

            const settingsData = { profile: {}, home_location: {}, preferences: {}, prayer_times: {} };

            settingsData.profile.name = document.getElementById('profile_name')?.value.trim() || '';
            settingsData.home_location.city_name = document.getElementById('home_city_name')?.value.trim() || '';
            settingsData.home_location.latitude = parseFloat(document.getElementById('home_latitude')?.value) || null;
            settingsData.home_location.longitude = parseFloat(document.getElementById('home_longitude')?.value) || null;
            
            settingsData.preferences.time_format = document.getElementById('time_format_preference')?.value || '12h';
            settingsData.preferences.calculation_method = document.getElementById('calculation_method')?.value || 'Karachi';
            settingsData.preferences.adjust_offsets_on_location_change = document.getElementById('adjust_timings_with_api_location')?.checked || false;
            settingsData.preferences.auto_update_location = document.getElementById('auto_update_api_location')?.checked || false;

            const prayerKeysForForm = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha', 'jummah'];
            prayerKeysForForm.forEach(pKey => {
                settingsData.prayer_times[pKey] = {};
                const isFixedRadio = document.querySelector(`input[name="prayer_times.${pKey}.is_fixed"][value="true"]`);
                let isFixed = isFixedRadio ? isFixedRadio.checked : (pKey === 'jummah');

                if (pKey === 'jummah') {
                    isFixed = true; 
                    settingsData.prayer_times[pKey].is_fixed = true;
                    settingsData.prayer_times[pKey].fixed_azan = document.getElementById('jummah_fixed_azan')?.value || '01:15';
                    settingsData.prayer_times[pKey].fixed_khutbah = document.getElementById('jummah_fixed_khutbah')?.value || '01:30';
                    settingsData.prayer_times[pKey].fixed_jamaat = document.getElementById('jummah_fixed_jamaat')?.value || '01:45';
                } else {
                    settingsData.prayer_times[pKey].is_fixed = isFixed;
                    if (isFixed) {
                        settingsData.prayer_times[pKey].fixed_azan = document.getElementById(`${pKey}_fixed_azan`)?.value || '00:00';
                        settingsData.prayer_times[pKey].fixed_jamaat = document.getElementById(`${pKey}_fixed_jamaat`)?.value || '00:00';
                    } else {
                        settingsData.prayer_times[pKey].azan_offset = parseInt(document.getElementById(`${pKey}_azan_offset`)?.value) || 0;
                        settingsData.prayer_times[pKey].jamaat_offset = parseInt(document.getElementById(`${pKey}_jamaat_offset`)?.value) || 0;
                    }
                }
            });

            console.log("Data to save:", JSON.stringify(settingsData, null, 2));

            try {
                const response = await fetch('/api/user/settings/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify(settingsData)
                });
                const result = await response.json();
                if (response.ok && result.status === 'success') {
                    showDynamicFlash(result.message || 'Settings saved successfully!', 'success');
                } else {
                    showDynamicFlash(result.message || `Error: ${result.error || 'Could not save settings.'}`, 'danger');
                }
            } catch (error) {
                console.error("Error saving settings via API:", error);
                showDynamicFlash('An unexpected error occurred. Please try again.', 'danger');
            } finally {
                saveAllSettingsButton.disabled = false;
                saveAllSettingsButton.textContent = 'Save All My Settings';
            }
        });
    }

    function showDynamicFlash(message, category) {
        const existingFlash = document.getElementById('dynamic-flash-message');
        if (existingFlash) existingFlash.remove();

        const flashDiv = document.createElement('div');
        flashDiv.id = 'dynamic-flash-message';
        flashDiv.className = `p-3 mb-6 max-w-3xl mx-auto rounded-md text-sm text-white fixed top-20 left-1/2 -translate-x-1/2 z-[200] shadow-lg`;
        flashDiv.style.opacity = '0'; // Start transparent for fade-in
        
        if (category === 'success') flashDiv.classList.add('bg-green-500');
        else if (category === 'danger') flashDiv.classList.add('bg-red-500');
        else if (category === 'info') flashDiv.classList.add('bg-blue-500');
        else flashDiv.classList.add('bg-primary-container', 'text-on-primary-container'); // Default/warning
        
        flashDiv.textContent = message;
        
        const mainContentArea = document.querySelector('main > div'); // Target the main content container
        if (mainContentArea) {
            mainContentArea.insertBefore(flashDiv, mainContentArea.firstChild);
        } else { // Fallback
            document.body.insertBefore(flashDiv, document.body.firstChild);
        }

        // Fade in
        setTimeout(() => { flashDiv.style.opacity = '1'; }, 10); 

        // Auto-remove after a few seconds with fade out
        setTimeout(() => {
            flashDiv.style.opacity = '0';
            setTimeout(() => flashDiv.remove(), 600); 
        }, 5000);
        flashDiv.style.transition = 'opacity 0.5s ease-in-out';
    }

    // Initial setup for prayer time calculation display on page load
    prayerSettingCards.forEach(card => {
        const prayerKey = card.id.split('-settings-card')[0];
        if (prayerKey !== 'jummah') {
            updateCalculatedTimesForPrayerUI(prayerKey);
        }
    });
});