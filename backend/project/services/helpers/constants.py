# project/services/helpers/constants.py

PRAYER_CONFIG_MAP = {
    "fajr":    {"is_fixed_attr": "fajr_is_fixed", "fixed_azan_attr": "fajr_fixed_azan", "fixed_jamaat_attr": "fajr_fixed_jamaat", "azan_offset_attr": "fajr_azan_offset", "jamaat_offset_attr": "fajr_jamaat_offset", "api_key": "Fajr", "end_boundary_key": "Sunrise"},
    "dhuhr":   {"is_fixed_attr": "dhuhr_is_fixed", "fixed_azan_attr": "dhuhr_fixed_azan", "fixed_jamaat_attr": "dhuhr_fixed_jamaat", "azan_offset_attr": "dhuhr_azan_offset", "jamaat_offset_attr": "dhuhr_jamaat_offset", "api_key": "Dhuhr", "end_boundary_key": "Asr"},
    "asr":     {"is_fixed_attr": "asr_is_fixed", "fixed_azan_attr": "asr_fixed_azan", "fixed_jamaat_attr": "asr_fixed_jamaat", "azan_offset_attr": "asr_azan_offset", "jamaat_offset_attr": "asr_jamaat_offset", "api_key": "Asr", "end_boundary_key": "Maghrib"},
    "maghrib": {"is_fixed_attr": "maghrib_is_fixed", "fixed_azan_attr": "maghrib_fixed_azan", "fixed_jamaat_attr": "maghrib_fixed_jamaat", "azan_offset_attr": "maghrib_azan_offset", "jamaat_offset_attr": "maghrib_jamaat_offset", "api_key": "Maghrib", "end_boundary_key": "Isha"},
    "isha":    {"is_fixed_attr": "isha_is_fixed", "fixed_azan_attr": "isha_fixed_azan", "fixed_jamaat_attr": "isha_fixed_jamaat", "azan_offset_attr": "isha_azan_offset", "jamaat_offset_attr": "isha_jamaat_offset", "api_key": "Isha", "end_boundary_key": "Fajr_Tomorrow"},
}
