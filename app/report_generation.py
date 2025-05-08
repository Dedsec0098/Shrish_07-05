import pytz
from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from . import crud, models, database
import csv
import os

DEFAULT_TIMEZONE = "America/Chicago"

def get_utc_from_local_time(local_dt_naive, timezone_str):
    try:
        tz = pytz.timezone(timezone_str)
        local_dt_aware = tz.localize(local_dt_naive, is_dst=None) 
    except pytz.exceptions.AmbiguousTimeError:
        local_dt_aware = tz.localize(local_dt_naive, is_dst=False)
    except pytz.exceptions.NonExistentTimeError:
        local_dt_aware = tz.localize(local_dt_naive + timedelta(hours=1), is_dst=False) 
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone(DEFAULT_TIMEZONE) 
        local_dt_aware = tz.localize(local_dt_naive, is_dst=None)

    return local_dt_aware.astimezone(pytz.utc)


def calculate_uptime_downtime(
    store_id: str,
    current_utc_dt: datetime,
    db: Session
):
    uptime_last_hour = 0
    downtime_last_hour = 0
    uptime_last_day = 0
    downtime_last_day = 0
    uptime_last_week = 0
    downtime_last_week = 0

    store_tz_str = crud.get_store_timezone_str(db, store_id)
    store_tz = pytz.timezone(store_tz_str)

    business_hours_records = crud.get_business_hours_for_store(db, store_id)
    
    is_always_open = not business_hours_records

    time_intervals = [
        ("hour", current_utc_dt - timedelta(hours=1), current_utc_dt),
        ("day", current_utc_dt - timedelta(days=1), current_utc_dt),
        ("week", current_utc_dt - timedelta(weeks=1), current_utc_dt),
    ]

    for period_name, start_utc_calc, end_utc_calc in time_intervals:
        total_business_seconds_in_period = 0
        observed_uptime_seconds = 0
        
        status_polls = crud.get_store_status_in_window(db, store_id, start_utc_calc, end_utc_calc)

        if not status_polls: 
            temp_cursor_utc_bh_calc = start_utc_calc
            temp_total_business_seconds = 0
            while temp_cursor_utc_bh_calc < end_utc_calc:
                next_minute_utc_bh = temp_cursor_utc_bh_calc + timedelta(minutes=1)
                actual_next_utc_bh = min(next_minute_utc_bh, end_utc_calc)
                duration_seconds_bh = (actual_next_utc_bh - temp_cursor_utc_bh_calc).total_seconds()
                if duration_seconds_bh <= 0: break

                mid_point_utc_bh = temp_cursor_utc_bh_calc + timedelta(seconds=duration_seconds_bh / 2)
                mid_point_local_bh = mid_point_utc_bh.astimezone(store_tz)
                is_bh_segment_active = False
                if is_always_open:
                    is_bh_segment_active = True
                else:
                    for bh in business_hours_records:
                        if bh.day_of_week == mid_point_local_bh.weekday():
                            if bh.start_time_local <= bh.end_time_local:
                                if bh.start_time_local <= mid_point_local_bh.time() < bh.end_time_local:
                                    is_bh_segment_active = True; break
                            else: 
                                if mid_point_local_bh.time() >= bh.start_time_local or mid_point_local_bh.time() < bh.end_time_local:
                                    is_bh_segment_active = True; break
                if is_bh_segment_active:
                    temp_total_business_seconds += duration_seconds_bh
                temp_cursor_utc_bh_calc = actual_next_utc_bh
            
            total_business_seconds_in_period = temp_total_business_seconds
            observed_uptime_seconds = total_business_seconds_in_period
        else: 
            status_polls.sort(key=lambda x: x.timestamp_utc)
            
   
            all_relevant_intervals = []


            first_poll_ts_utc = status_polls[0].timestamp_utc.replace(tzinfo=pytz.utc)
            if start_utc_calc < first_poll_ts_utc:
                all_relevant_intervals.append({
                    "start": start_utc_calc, 
                    "end": first_poll_ts_utc, 
                    "status": status_polls[0].status
                })

         
            for i in range(len(status_polls) - 1):
                current_poll = status_polls[i]
                next_poll = status_polls[i+1]
                current_poll_ts_utc = current_poll.timestamp_utc.replace(tzinfo=pytz.utc)
                next_poll_ts_utc = next_poll.timestamp_utc.replace(tzinfo=pytz.utc)
                all_relevant_intervals.append({
                    "start": current_poll_ts_utc, 
                    "end": next_poll_ts_utc, 
                    "status": current_poll.status
                })
            
            
            last_poll = status_polls[-1]
            last_poll_ts_utc = last_poll.timestamp_utc.replace(tzinfo=pytz.utc)
            if last_poll_ts_utc < end_utc_calc:
                 all_relevant_intervals.append({
                    "start": last_poll_ts_utc, 
                    "end": end_utc_calc, 
                    "status": last_poll.status
                })
            elif not all_relevant_intervals and last_poll_ts_utc >= start_utc_calc: 
                 all_relevant_intervals.append({
                    "start": max(start_utc_calc, last_poll_ts_utc),
                    "end": end_utc_calc, 
                    "status": last_poll.status
                })



            for interval in all_relevant_intervals:
                effective_interval_start = max(interval["start"], start_utc_calc)
                effective_interval_end = min(interval["end"], end_utc_calc)

                if effective_interval_start >= effective_interval_end: continue

                temp_cursor_utc = effective_interval_start
                while temp_cursor_utc < effective_interval_end:
                    next_minute_utc = temp_cursor_utc + timedelta(minutes=1)
                    actual_next_utc = min(next_minute_utc, effective_interval_end)
                    duration_seconds = (actual_next_utc - temp_cursor_utc).total_seconds()
                    if duration_seconds <= 0: break

                    mid_point_utc = temp_cursor_utc + timedelta(seconds=duration_seconds / 2)
                    mid_point_local = mid_point_utc.astimezone(store_tz)
                    
                    is_bh_segment = False
                    if is_always_open:
                        is_bh_segment = True
                    else:
                        for bh in business_hours_records:
                            if bh.day_of_week == mid_point_local.weekday():
                                if bh.start_time_local <= bh.end_time_local:
                                    if bh.start_time_local <= mid_point_local.time() < bh.end_time_local:
                                        is_bh_segment = True; break
                                else: 
                                    if mid_point_local.time() >= bh.start_time_local or mid_point_local.time() < bh.end_time_local:
                                        is_bh_segment = True; break
                    
                    if is_bh_segment:
       
                        if interval["status"] == "active":
                            observed_uptime_seconds += duration_seconds
                    
                    temp_cursor_utc = actual_next_utc
            
    
            current_total_business_seconds = 0
            temp_cursor_utc_total_bh = start_utc_calc
            while temp_cursor_utc_total_bh < end_utc_calc:
                next_minute_utc_total_bh = temp_cursor_utc_total_bh + timedelta(minutes=1)
                actual_next_utc_total_bh = min(next_minute_utc_total_bh, end_utc_calc)
                duration_seconds_total_bh = (actual_next_utc_total_bh - temp_cursor_utc_total_bh).total_seconds()
                if duration_seconds_total_bh <= 0: break

                mid_point_utc_total_bh = temp_cursor_utc_total_bh + timedelta(seconds=duration_seconds_total_bh / 2)
                mid_point_local_total_bh = mid_point_utc_total_bh.astimezone(store_tz)
                is_bh_segment_total = False
                if is_always_open:
                    is_bh_segment_total = True
                else:
                    for bh in business_hours_records:
                        if bh.day_of_week == mid_point_local_total_bh.weekday():
                            if bh.start_time_local <= bh.end_time_local:
                                if bh.start_time_local <= mid_point_local_total_bh.time() < bh.end_time_local:
                                    is_bh_segment_total = True; break
                            else:
                                if mid_point_local_total_bh.time() >= bh.start_time_local or mid_point_local_total_bh.time() < bh.end_time_local:
                                    is_bh_segment_total = True; break
                if is_bh_segment_total:
                    current_total_business_seconds += duration_seconds_total_bh
                temp_cursor_utc_total_bh = actual_next_utc_total_bh
            total_business_seconds_in_period = current_total_business_seconds


        if total_business_seconds_in_period > 0:
            uptime_for_period = observed_uptime_seconds
            uptime_for_period = min(uptime_for_period, total_business_seconds_in_period)
            downtime_for_period = total_business_seconds_in_period - uptime_for_period
        else: 
            uptime_for_period = 0
            downtime_for_period = 0

        if period_name == "hour":
            uptime_last_hour = uptime_for_period / 60  
            downtime_last_hour = downtime_for_period / 60 
        elif period_name == "day":
            uptime_last_day = uptime_for_period / 3600  
            downtime_last_day = downtime_for_period / 3600 
        elif period_name == "week":
            uptime_last_week = uptime_for_period / 3600  
            downtime_last_week = downtime_for_period / 3600 

    return {
        "store_id": store_id,
        "uptime_last_hour": round(uptime_last_hour, 2),
        "uptime_last_day": round(uptime_last_day, 2),
        "uptime_last_week": round(uptime_last_week, 2),
        "downtime_last_hour": round(downtime_last_hour, 2),
        "downtime_last_day": round(downtime_last_day, 2),
        "downtime_last_week": round(downtime_last_week, 2),
    }


def generate_report_logic(report_id: str, reports_dir: str, report_status_dict: dict, current_timestamp_str: str):
    db: Session = next(database.get_db())
    try:
        crud.create_report_entry(db, report_id) 

        ts_str_cleaned = current_timestamp_str.replace(" UTC", "")
        try:
            current_utc_dt = datetime.strptime(ts_str_cleaned, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            current_utc_dt = datetime.strptime(ts_str_cleaned, '%Y-%m-%d %H:%M:%S')
        
        current_utc_dt = pytz.utc.localize(current_utc_dt) 

        all_store_ids = crud.get_all_store_ids(db)
        if not all_store_ids:
            print("No store IDs found in the database. Report will be empty.")
            report_file_path = os.path.join(reports_dir, f"{report_id}.csv")
            fieldnames = [
                "store_id", "uptime_last_hour", "uptime_last_day", "uptime_last_week",
                "downtime_last_hour", "downtime_last_day", "downtime_last_week"
            ]
            with open(report_file_path, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
            report_status_dict[report_id] = "Complete"
            crud.update_report_status(db, report_id, "Complete", report_file_path)
            return
            
        report_data_list = []

        for store_id in all_store_ids:
            data = calculate_uptime_downtime(store_id, current_utc_dt, db)
            report_data_list.append(data)
        
        crud.save_report_data(db, report_id, report_data_list)

        report_file_path = os.path.join(reports_dir, f"{report_id}.csv")
        fieldnames = [
            "store_id", "uptime_last_hour", "uptime_last_day", "uptime_last_week",
            "downtime_last_hour", "downtime_last_day", "downtime_last_week"
        ]
        with open(report_file_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row_data in report_data_list:
                writer.writerow(row_data)
        
        report_status_dict[report_id] = "Complete"
        crud.update_report_status(db, report_id, "Complete", report_file_path)

    except Exception as e:
        print(f"Error generating report {report_id}: {e}") 
        import traceback
        traceback.print_exc()
        report_status_dict[report_id] = "Error"
        crud.update_report_status(db, report_id, "Error")
    finally:
        db.close()

