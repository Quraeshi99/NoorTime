# project/utils/template_helpers.py

def user_settings_to_dict(user_settings):
    if not user_settings:
        return {}

    user = user_settings.user

    return {
        'default_latitude': user.default_latitude if user else None,
        'default_longitude': user.default_longitude if user else None,
        'default_calculation_method': user.default_calculation_method if user else None,
        'time_format_preference': user.time_format_preference if user else None,

        'adjust_timings_with_api_location': user_settings.adjust_timings_with_api_location,
        'auto_update_api_location': user_settings.auto_update_api_location,

        'fajr_is_fixed': user_settings.fajr_is_fixed,
        'fajr_fixed_azan': user_settings.fajr_fixed_azan,
        'fajr_fixed_jamaat': user_settings.fajr_fixed_jamaat,
        'fajr_azan_offset': user_settings.fajr_azan_offset,
        'fajr_jamaat_offset': user_settings.fajr_jamaat_offset,

        'dhuhr_is_fixed': user_settings.dhuhr_is_fixed,
        'dhuhr_fixed_azan': user_settings.dhuhr_fixed_azan,
        'dhuhr_fixed_jamaat': user_settings.dhuhr_fixed_jamaat,
        'dhuhr_azan_offset': user_settings.dhuhr_azan_offset,
        'dhuhr_jamaat_offset': user_settings.dhuhr_jamaat_offset,

        'asr_is_fixed': user_settings.asr_is_fixed,
        'asr_fixed_azan': user_settings.asr_fixed_azan,
        'asr_fixed_jamaat': user_settings.asr_fixed_jamaat,
        'asr_azan_offset': user_settings.asr_azan_offset,
        'asr_jamaat_offset': user_settings.asr_jamaat_offset,

        'maghrib_is_fixed': user_settings.maghrib_is_fixed,
        'maghrib_fixed_azan': user_settings.maghrib_fixed_azan,
        'maghrib_fixed_jamaat': user_settings.maghrib_fixed_jamaat,
        'maghrib_azan_offset': user_settings.maghrib_azan_offset,
        'maghrib_jamaat_offset': user_settings.maghrib_jamaat_offset,

        'isha_is_fixed': user_settings.isha_is_fixed,
        'isha_fixed_azan': user_settings.isha_fixed_azan,
        'isha_fixed_jamaat': user_settings.isha_fixed_jamaat,
        'isha_azan_offset': user_settings.isha_azan_offset,
        'isha_jamaat_offset': user_settings.isha_jamaat_offset,

        'jummah_azan_time': user_settings.jummah_azan_time,
        'jummah_khutbah_start_time': user_settings.jummah_khutbah_start_time,
        'jummah_jamaat_time': user_settings.jummah_jamaat_time,
    }

def user_profile_to_dict(user):
    if not user:
        return {}

    return {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'default_latitude': user.default_latitude,
        'default_longitude': user.default_longitude,
        'default_calculation_method': user.default_calculation_method,
        'time_format_preference': user.time_format_preference,
        'is_admin': getattr(user, 'is_admin', False)
    }
