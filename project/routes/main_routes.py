# project/routes/main_routes.py

from flask import Blueprint, render_template, current_app, jsonify, request, flash, redirect, url_for
from flask_login import current_user, login_required
import datetime # For API calls and date handling

# project/__init__.py से db और अन्य एक्सटेंशन इम्पोर्ट करें
from .. import db
from ..models import User, UserSettings
# from ..forms import FullSettingsForm # हम JSON का उपयोग कर रहे हैं, इसलिए WTForm आवश्यक नहीं है
# services से हेल्पर फंक्शन्स इम्पोर्ट करें
from ..services.prayer_time_service import get_api_prayer_times_for_date_from_service # Renamed for clarity

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # मुख्य डिस्प्ले पेज। डेटा JavaScript द्वारा API से फ़ेच किया जाएगा।
    # हम यहाँ कुछ बेसिक जानकारी पास कर सकते हैं जो बदलने की संभावना कम हो,
    # या फिर सब कुछ JS पर छोड़ सकते हैं।
    # अभी के लिए, JS ही /api/initial_prayer_data कॉल करेगा।
    return render_template('index.html', title="Prayer Times")

@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required # सेटिंग्स पेज के लिए लॉगिन आवश्यक है
def settings():
    # GET रिक्वेस्ट के लिए, वर्तमान सेटिंग्स और API समय दिखाएं
    # POST रिक्वेस्ट (जो JavaScript से AJAX के रूप में आएगी) सेटिंग्स को अपडेट करेगी
    
    # वर्तमान उपयोगकर्ता की सेटिंग्स प्राप्त करें
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        # यदि किसी कारण से सेटिंग्स मौजूद नहीं हैं, तो डिफ़ॉल्ट बनाएँ
        # (यह रजिस्ट्रेशन के समय बन जानी चाहिए थीं)
        current_app.logger.warning(f"UserSettings not found for user {current_user.id}, creating defaults.")
        user_settings = UserSettings(user_id=current_user.id)
        # User model से डिफ़ॉल्ट लोकेशन और मेथड लें (यदि सेट हैं)
        user_settings.default_latitude = current_user.default_latitude
        user_settings.default_longitude = current_user.default_longitude
        user_settings.default_calculation_method = current_user.default_calculation_method
        user_settings.time_format_preference = current_user.time_format_preference

        db.session.add(user_settings)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating default UserSettings for user {current_user.id}: {e}", exc_info=True)
            flash("सेटिंग्ज लोड करताना त्रुटी आली. कृपया पुन्हा प्रयत्न करा.", "danger") # Marathi
            return redirect(url_for('main.index'))

    # एडमिन पैनल की तरह, संदर्भ के लिए आज का API समय प्राप्त करें
    user_lat = current_user.default_latitude if current_user.default_latitude is not None else float(current_app.config.get('DEFAULT_LATITUDE', 19.2183))
    user_lon = current_user.default_longitude if current_user.default_longitude is not None else float(current_app.config.get('DEFAULT_LONGITUDE', 72.8493))
    user_calc_method_key = current_user.default_calculation_method if current_user.default_calculation_method else current_app.config.get('DEFAULT_CALCULATION_METHOD', 'Karachi')
    
    today_api_times = get_api_prayer_times_for_date_from_service(
        date_obj=datetime.date.today(),
        latitude=user_lat,
        longitude=user_lon,
        calculation_method_key=user_calc_method_key,
        force_refresh=True
    )

    if not today_api_times:
        current_app.logger.warning("API times for settings page could not be fetched. Using empty dict.")
        today_api_times = {}
        flash("सध्याच्या API नमाज़ वेळापत्रकासाठी संदर्भ मिळू शकला नाही.", "warning") # Marathi

    calculation_method_choices_for_template = [
        {'key': 'Karachi', 'name': "Karachi (Univ. of Islamic Sci.)"},
        {'key': 'ISNA', 'name': "ISNA (N. America) - Standard Asr"},
        {'key': 'MWL', 'name': "Muslim World League - Standard Asr"},
        {'key': 'Egyptian', 'name': "Egyptian General Authority - Standard Asr"},
        {'key': 'Makkah', 'name': "Makkah (Umm al-Qura) - Standard Asr"},
        {'key': 'Tehran', 'name': "Tehran (Univ. of Tehran Geophysics)"},
        {'key': 'Jafari', 'name': "Shia Ithna-Ashari (Jafari)"},
    ]

    return render_template('settings.html', 
                           title="सेटिंग्ज", 
                           user_settings=user_settings_to_dict(user_settings),
                           user_profile=user_profile_to_dict(current_user),
                           api_times_for_reference=today_api_times,
                           calculation_method_choices=calculation_method_choices_for_template)

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
