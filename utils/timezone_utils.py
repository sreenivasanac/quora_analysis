from datetime import datetime, timedelta
import pytz

# Timezone mappings
TIMEZONES = {
    'IST': 'Asia/Kolkata',      # UTC+5:30
    'CST': 'Asia/Shanghai',     # UTC+8:00
    'PST': 'America/Los_Angeles', # UTC-8:00 (varies with DST)
    'EST': 'America/New_York'    # UTC-5:00 (varies with DST)
}

def convert_to_timezone(timestamp, target_tz_name):
    """Convert timestamp to target timezone"""
    if timestamp is None:
        return None

    target_tz = pytz.timezone(TIMEZONES.get(target_tz_name, 'Asia/Kolkata'))
    ist_tz = pytz.timezone('Asia/Kolkata')

    # If timestamp is naive, assume it's in IST (as per database storage)
    if timestamp.tzinfo is None:
        timestamp = ist_tz.localize(timestamp)
    elif timestamp.tzinfo.utcoffset(timestamp) is None:
        # If tzinfo exists but no offset, replace with IST
        timestamp = ist_tz.localize(timestamp.replace(tzinfo=None))

    # Convert to target timezone
    return timestamp.astimezone(target_tz)

def get_date_range_for_timezone(start_date_str, end_date_str, timezone_name):
    """Parse and convert date range for database queries"""
    if start_date_str and end_date_str:
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
    else:
        # Default to current week in the selected timezone
        selected_tz = pytz.timezone(TIMEZONES.get(timezone_name, 'Asia/Kolkata'))
        now = datetime.now(selected_tz)
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)

    # Convert date range to IST for database query (since DB stores in IST)
    ist_tz = pytz.timezone('Asia/Kolkata')
    if start_date.tzinfo:
        start_date_ist = start_date.astimezone(ist_tz)
        end_date_ist = end_date.astimezone(ist_tz)
    else:
        # If no timezone info, assume UTC
        start_date_ist = pytz.UTC.localize(start_date).astimezone(ist_tz)
        end_date_ist = pytz.UTC.localize(end_date).astimezone(ist_tz)

    return start_date, end_date, start_date_ist, end_date_ist

def calculate_distributions(all_timestamps, timezone_name):
    """Calculate hourly and weekday distributions for the target timezone"""
    hourly_dist = {hour: 0 for hour in range(24)}
    weekday_dist = {day: 0 for day in range(7)}  # 0=Monday, 6=Sunday

    for row in all_timestamps:
        timestamp = row['post_timestamp_parsed']
        converted = convert_to_timezone(timestamp, timezone_name)
        if converted:
            hourly_dist[converted.hour] += 1
            weekday_dist[converted.weekday()] += 1

    # Find busiest hour and day
    busiest_hour = max(hourly_dist, key=hourly_dist.get)
    busiest_day = max(weekday_dist, key=weekday_dist.get)

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    return {
        'hourly_distribution': hourly_dist,
        'weekday_distribution': {days[i]: count for i, count in weekday_dist.items()},
        'busiest_hour': busiest_hour,
        'busiest_day': days[busiest_day]
    }