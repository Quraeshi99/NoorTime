from ...helpers.constants import PRAYER_CONFIG_MAP
from typing import Dict, Any, Optional, List

def parse_time_str(time_str: str) -> Optional[datetime.time]:
    if not time_str or time_str.lower() == "n/a": 
        return None
    
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.datetime.strptime(time_str.strip(), fmt).time()
        except ValueError:
            continue
            
    current_app.logger.warning(f"Service: Invalid or unrecognized time string format for parsing: {time_str}")
    return None

def format_time_obj(time_obj: Optional[datetime.time]) -> str:
    if not time_obj: return "N/A"
    return time_obj.strftime("%H:%M")

def add_minutes(time_obj: Optional[datetime.time], minutes_to_add: Optional[int]) -> Optional[datetime.time]:
    if not time_obj or minutes_to_add is None: return None
    dummy_date = datetime.date.min
    full_datetime = datetime.datetime.combine(dummy_date, time_obj)
    new_datetime = full_datetime + datetime.timedelta(minutes=int(minutes_to_add))
    return new_datetime.time()

def add_seconds(time_obj: Optional[datetime.time], seconds_to_add: Optional[int]) -> Optional[datetime.time]:
    if not time_obj or seconds_to_add is None: return None
    dummy_date = datetime.date.min
    full_datetime = datetime.datetime.combine(dummy_date, time_obj)
    new_datetime = full_datetime + datetime.timedelta(seconds=int(seconds_to_add))
    return new_datetime.time()

def apply_boundary_check(time_to_check: Optional[datetime.time], start_boundary: Optional[str], end_boundary: Optional[str]) -> Optional[datetime.time]:
    if not time_to_check: return None
    start_boundary_obj = parse_time_str(start_boundary)
    end_boundary_obj = parse_time_str(end_boundary)
    if not start_boundary_obj or not end_boundary_obj: return time_to_check
    if start_boundary_obj > end_boundary_obj: return time_to_check
    if time_to_check < start_boundary_obj: return start_boundary_obj
    if time_to_check > end_boundary_obj: return end_boundary_obj
    return time_to_check

def get_single_prayer_info(prayer_name: str, api_times: Dict[str, Any], user_settings: Any, api_times_day_after_tomorrow: Dict[str, Any], last_api_times: Dict[str, Any], calculation_date: datetime.date) -> Dict[str, str]:
    config = PRAYER_CONFIG_MAP.get(prayer_name.lower())
    if not config: return {"azan": "N/A", "jamaat": "N/A"}

    is_fixed = getattr(user_settings, config["is_fixed_attr"], False)
    api_start_time_str = api_times.get(config["api_key"])
    start_boundary_str = api_start_time_str
    end_boundary_key = config["end_boundary_key"]
    end_boundary_str = api_times_day_after_tomorrow.get("Fajr") if end_boundary_key == "Fajr_Tomorrow" else api_times.get(end_boundary_key)

    azan_time_obj, jamaat_time_obj = None, None
    if is_fixed:
        azan_time_obj = parse_time_str(getattr(user_settings, config["fixed_azan_attr"]))
        jamaat_time_obj = parse_time_str(getattr(user_settings, config["fixed_jamaat_attr"]))
    else:
        api_time_to_use_str = api_start_time_str
        if last_api_times and user_settings.threshold_minutes > 0:
            last_time_obj = parse_time_str(last_api_times.get(config["api_key"]))
            new_time_obj = parse_time_str(api_start_time_str)
            if last_time_obj and new_time_obj:
                diff = abs((datetime.datetime.combine(calculation_date, new_time_obj) - datetime.datetime.combine(calculation_date, last_time_obj)).total_seconds() / 60)
                if diff < user_settings.threshold_minutes:
                    api_time_to_use_str = last_api_time_str

        api_start_time_obj = parse_time_str(api_time_to_use_str)
        if api_start_time_obj:
            azan_offset = getattr(user_settings, config["azan_offset_attr"])
            calculated_azan_obj = add_minutes(api_start_time_obj, azan_offset)
            azan_time_obj = apply_boundary_check(calculated_azan_obj, start_boundary_str, end_boundary_str)
            if azan_time_obj:
                jamaat_offset = getattr(user_settings, config["jamaat_offset_attr"])
                calculated_jamaat_obj = add_minutes(azan_time_obj, jamaat_offset)
                jamaat_time_obj = apply_boundary_check(calculated_jamaat_obj, start_boundary_str, end_boundary_str)

    return {"azan": format_time_obj(azan_time_obj), "jamaat": format_time_obj(jamaat_time_obj)}

def calculate_display_times_from_service(user_settings: Any, api_times_today: Dict[str, Any], api_times_tomorrow: Dict[str, Any], app_config: Dict[str, Any], calculation_date: datetime.date) -> Tuple[Dict[str, Any], bool]:
    calculated_times = {}
    needs_db_update = False

    if not api_times_today:
        api_times_today = {}
    if not api_times_tomorrow:
        api_times_tomorrow = {}

    last_api_times = {}
    if user_settings.last_api_times_for_threshold:
        try:
            last_api_times = json.loads(user_settings.last_api_times_for_threshold)
        except (json.JSONDecodeError, TypeError):
            current_app.logger.warning("Could not parse last_api_times_for_threshold JSON. Resetting.")
            needs_db_update = True

    for p_key, config in PRAYER_CONFIG_MAP.items():
        is_fixed = getattr(user_settings, config["is_fixed_attr"], False)
        
        azan_time_obj, jamaat_time_obj = None, None

        if is_fixed:
            azan_time_obj = parse_time_str(getattr(user_settings, config["fixed_azan_attr"]))
            jamaat_time_obj = parse_time_str(getattr(user_settings, config["fixed_jamaat_attr"]))
        else:
            api_start_time_str = api_times_today.get(config["api_key"])
            
            if api_start_time_str:
                start_boundary_str = api_start_time_str
                end_boundary_key = config["end_boundary_key"]
                end_boundary_str = api_times_tomorrow.get("Fajr") if end_boundary_key == "Fajr_Tomorrow" else api_times_today.get(end_boundary_key)

                api_time_to_use_str = api_start_time_str
                last_api_time_str = last_api_times.get(config["api_key"])
                
                if last_api_time_str and user_settings.threshold_minutes > 0:
                    last_time_obj = parse_time_str(last_api_time_str)
                    new_time_obj = parse_time_str(api_start_time_str)
                    if last_time_obj and new_time_obj:
                        diff = abs((datetime.datetime.combine(calculation_date, new_time_obj) - datetime.datetime.combine(calculation_date, last_time_obj)).total_seconds() / 60)
                        if diff < user_settings.threshold_minutes:
                            api_time_to_use_str = last_api_time_str
                        else:
                            needs_db_update = True
                    else:
                        needs_db_update = True
                else:
                    needs_db_update = True

                api_start_time_obj = parse_time_str(api_time_to_use_str)
                if api_start_time_obj:
                    azan_offset = getattr(user_settings, config["azan_offset_attr"])
                    calculated_azan_obj = add_minutes(api_start_time_obj, azan_offset)
                    azan_time_obj = apply_boundary_check(calculated_azan_obj, start_boundary_str, end_boundary_str)
                    
                    if azan_time_obj:
                        jamaat_offset = getattr(user_settings, config["jamaat_offset_attr"])
                        calculated_jamaat_obj = add_minutes(azan_time_obj, jamaat_offset)
                        jamaat_time_obj = apply_boundary_check(calculated_jamaat_obj, start_boundary_str, end_boundary_str)

        calculated_times[p_key] = {"azan": format_time_obj(azan_time_obj), "jamaat": format_time_obj(jamaat_time_obj)}
    
    maghrib_time_str = api_times_today.get("Maghrib")
    calculated_times["iftari"] = {"time": format_time_obj(parse_time_str(maghrib_time_str))}

    imsak_time_str = api_times_today.get("Imsak")
    calculated_times["sehri_end"] = {"time": format_time_obj(parse_time_str(imsak_time_str))}

    if user_settings.jummah_is_fixed:
        jummah_azan_obj = parse_time_str(user_settings.jummah_azan_time)
        jummah_khutbah_obj = parse_time_str(user_settings.jummah_khutbah_start_time)
        jummah_jamaat_obj = parse_time_str(user_settings.jummah_jamaat_time)
    else:
        dhuhr_raw_time_str = api_times_today.get("Dhuhr")
        dhuhr_raw_time_obj = parse_time_str(dhuhr_raw_time_str)
        
        jummah_azan_obj, jummah_khutbah_obj, jummah_jamaat_obj = None, None, None

        if dhuhr_raw_time_obj:
            jummah_azan_obj = add_minutes(dhuhr_raw_time_obj, user_settings.jummah_azan_offset)
            
            if jummah_azan_obj:
                jummah_khutbah_obj = add_minutes(jummah_azan_obj, user_settings.jummah_khutbah_offset)
                jummah_jamaat_obj = add_minutes(jummah_azan_obj, user_settings.jummah_jamaat_offset)

    calculated_times["jummah"] = {
        "azan": format_time_obj(jummah_azan_obj),
        "khutbah": format_time_obj(jummah_khutbah_obj),
        "jamaat": format_time_obj(jummah_jamaat_obj)
    }

    sunrise_time_str = api_times_today.get("Sunrise")
    if sunrise_time_str:
        sunrise_time_obj = parse_time_str(sunrise_time_str)
        if sunrise_time_obj:
            chasht_time_obj = add_minutes(sunrise_time_obj, 20)
            chasht_time_obj = add_seconds(chasht_time_obj, 30)
            calculated_times["chasht"] = {"azan": format_time_obj(chasht_time_obj), "jamaat": "N/A"}
        else:
            calculated_times["chasht"] = {"azan": "N/A", "jamaat": "N/A"}
    else:
        calculated_times["chasht"] = {"azan": "N/A", "jamaat": "N/A"}

    fajr_time_str = api_times_today.get("Fajr")
    sunrise_time_str = api_times_today.get("Sunrise")
    sunset_time_str = api_times_today.get("Sunset")

    zohwa_kubra_start_obj = None
    fajr_obj = parse_time_str(fajr_time_str)
    sunset_obj = parse_time_str(sunset_time_str)
    if fajr_obj and sunset_obj:
        fajr_dt = datetime.datetime.combine(calculation_date, fajr_obj)
        sunset_dt = datetime.datetime.combine(calculation_date, sunset_obj)
        if sunset_dt < fajr_dt:
            sunset_dt += datetime.timedelta(days=1)
        duration = sunset_dt - fajr_dt
        midpoint_dt = fajr_dt + duration / 2
        zohwa_kubra_start_obj = midpoint_dt.time()

    zohwa_kubra_end_obj = None
    sunrise_obj = parse_time_str(sunrise_time_str)
    if sunrise_obj and sunset_obj:
        sunrise_dt = datetime.datetime.combine(calculation_date, sunrise_obj)
        sunset_dt = datetime.datetime.combine(calculation_date, sunset_obj)
        if sunset_dt < sunrise_dt:
            sunset_dt += datetime.timedelta(days=1)
        duration = sunset_dt - sunrise_dt
        midpoint_dt = sunrise_dt + duration / 2
        zohwa_kubra_end_obj = midpoint_dt.time()

    calculated_times["zohwa_kubra"] = {
        "start": format_time_obj(zohwa_kubra_start_obj),
        "end": format_time_obj(zohwa_kubra_end_obj)
    }
    return calculated_times, needs_db_update

def get_next_prayer_info_from_service(display_times_today: Dict[str, Any], tomorrow_fajr_display_details: Dict[str, Any], now_datetime_obj: datetime.datetime) -> Dict[str, Any]:
    now_time_obj = now_datetime_obj.time()
    is_friday = now_datetime_obj.weekday() == 4
    prayer_sequence_keys = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
    today_prayer_events = []
    for p_key in prayer_sequence_keys:
        prayer_name_display = p_key.capitalize()
        if is_friday and p_key == "dhuhr":
            prayer_name_display = "Jummah"
            jamaat_time_str = display_times_today.get("jummah", {}).get("jamaat")
            azan_time_str = display_times_today.get("jummah", {}).get("azan")
        else:
            jamaat_time_str = display_times_today.get(p_key, {}).get("jamaat")
            azan_time_str = display_times_today.get(p_key, {}).get("azan")
        jamaat_time_obj = parse_time_str(jamaat_time_str)
        if jamaat_time_obj:
            today_prayer_events.append({
                "key": p_key,
                "name_display": prayer_name_display,
                "datetime": datetime.datetime.combine(now_datetime_obj.date(), jamaat_time_obj),
                "azan": azan_time_str,
                "jamaat": jamaat_time_str
            })
    today_prayer_events.sort(key=lambda x: x["datetime"])
    next_prayer_event = None
    for event in today_prayer_events:
        if now_datetime_obj < event["datetime"]:
            next_prayer_event = event
            break
    details = { "name": "N/A", "azanTime": "N/A", "jamaatTime": "N/A", "timeToJamaatMinutes": 0, "isNextDayFajr": False, "isJamaatCountdownActive": False, "jamaatCountdownSeconds": 0, "isPostJamaatCountdownActive": False, "postJamaatCountdownSeconds": 0, }
    if next_prayer_event:
        details["name"] = next_prayer_event["name_display"]
        details["azanTime"] = next_prayer_event["azan"]
        details["jamaatTime"] = next_prayer_event["jamaat"]
        time_diff = next_prayer_event["datetime"] - now_datetime_obj
        details["timeToJamaatMinutes"] = int(time_diff.total_seconds() // 60)
        if 0 < time_diff.total_seconds() <= 120:
            details["isJamaatCountdownActive"] = True
            details["jamaatCountdownSeconds"] = int(time_diff.total_seconds())
    else:
        details["name"] = "Fajr (Tomorrow)"
        details["isNextDayFajr"] = True
        if tomorrow_fajr_display_details:
            details["azanTime"] = tomorrow_fajr_display_details["azan"]
            details["jamaatTime"] = tomorrow_fajr_display_details["jamaat"]
            fajr_tmrw_time_obj = parse_time_str(tomorrow_fajr_display_details["jamaat"])
            if fajr_tmrw_time_obj:
                tmrw_date = now_datetime_obj.date() + datetime.timedelta(days=1)
                fajr_tmrw_dt = datetime.datetime.combine(tmrw_date, fajr_tmrw_time_obj)
                time_diff_fajr = fajr_tmrw_dt - now_datetime_obj
                if time_diff_fajr.total_seconds() > 0:
                    details["timeToJamaatMinutes"] = int(time_diff_fajr.total_seconds() // 60)
                    if 0 < time_diff_fajr.total_seconds() <= 120:
                        details["isJamaatCountdownActive"] = True
                        details["jamaatCountdownSeconds"] = int(time_diff_fajr.total_seconds())
    last_jamaat_passed = None
    for event in reversed(today_prayer_events):
        if now_datetime_obj >= event["datetime"]:
            last_jamaat_passed = event
            break
    if last_jamaat_passed:
        time_since_last = now_datetime_obj - last_jamaat_passed["datetime"]
        if 0 <= time_since_last.total_seconds() < 600:
            if not details["isJamaatCountdownActive"]:
                details["isPostJamaatCountdownActive"] = True
                details["postJamaatCountdownSeconds"] = 600 - int(time_since_last.total_seconds())
    return details

def get_current_prayer_period_from_service(api_times_today: Dict[str, Any], api_times_tomorrow: Dict[str, Any], now_datetime_obj: datetime.datetime) -> Dict[str, str]:
    if not api_times_today: return {"name": "N/A", "start": "N/A", "end": "N/A"}
    now_time = now_datetime_obj.time()
    periods_config = [
        ("Fajr", "Fajr", "Sunrise"), ("Post-Sunrise", "Sunrise", "Dhuhr"),
        ("Dhuhr", "Dhuhr", "Asr"), ("Asr", "Asr", "Maghrib"),
        ("Maghrib", "Maghrib", "Isha"), ("Isha", "Isha", "Fajr_Tomorrow")
    ]
    for p_name, start_key, end_key in periods_config:
        start_time_str = api_times_today.get(start_key)
        end_time_str = api_times_tomorrow.get("Fajr") if end_key == "Fajr_Tomorrow" and api_times_tomorrow else api_times_today.get(end_key)
        start_time_obj = parse_time_str(start_time_str)
        end_time_obj = parse_time_str(end_time_str)
        if start_time_obj and end_time_obj:
            if start_time_obj > end_time_obj:
                if (now_time >= start_time_obj) or (now_time < end_time_obj):
                    return {"name": p_name.upper(), "start": start_time_str, "end": end_time_str}
            elif start_time_obj <= now_time < end_time_obj:
                return {"name": p_name.upper(), "start": start_time_str, "end": end_time_str}
    return {"name": "N/A", "start": "N/A", "end": "N/A"}