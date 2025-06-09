# project/utils/prayer_display_helper.py

from datetime import datetime, timedelta

def get_tomorrow_display_for_current_prayer():
    tomorrow = datetime.now() + timedelta(days=1)
    return {
        "fajr": "05:00",
        "dhuhr": "12:30",
        "asr": "16:00",
        "maghrib": "18:45",
        "isha": "20:00",
        "date": tomorrow.strftime("%Y-%m-%d")
    }

def get_prayer_info():
    now = datetime.now().time()
    return {
        "current": "asr",
        "next": "maghrib",
        "now_time": now.strftime("%H:%M")
    }
