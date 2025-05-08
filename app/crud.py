\
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from . import models
import csv
import pytz
from datetime import datetime, timedelta, time

DEFAULT_TIMEZONE = "America/Chicago"

def get_max_timestamp(db: Session):
    max_ts = db.query(func.max(models.StoreStatus.timestamp_utc)).scalar()
    if max_ts:
        if isinstance(max_ts, datetime):
            return max_ts.strftime('%Y-%m-%d %H:%M:%S.%f UTC')
        return str(max_ts) 
    return None


def get_store_timezone_str(db: Session, store_id: str) -> str:
    tz_entry = db.query(models.StoreTimezone.timezone_str).filter(models.StoreTimezone.store_id == store_id).first()
    return tz_entry[0] if tz_entry else DEFAULT_TIMEZONE

def get_business_hours_for_store(db: Session, store_id: str):
    return db.query(models.BusinessHours).filter(models.BusinessHours.store_id == store_id).all()

def get_store_status_in_window(db: Session, store_id: str, start_utc: datetime, end_utc: datetime):
    return db.query(models.StoreStatus).\
        filter(models.StoreStatus.store_id == store_id).\
        filter(models.StoreStatus.timestamp_utc >= start_utc).\
        filter(models.StoreStatus.timestamp_utc <= end_utc).\
        order_by(models.StoreStatus.timestamp_utc).all()

def get_all_store_ids(db: Session):
    return [item[0] for item in db.query(models.StoreStatus.store_id).distinct().all()]


def bulk_insert_store_status(db: Session, file_path: str):
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        objects = []
        for row in reader:
       
            if not row.get('store_id') or not row.get('timestamp_utc') or not row.get('status'):
                print(f"Skipping malformed row: {row}")
                continue
            try:
      
                ts_str = row['timestamp_utc'].replace(" UTC", "")

                try:
                    dt_obj = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    dt_obj = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                
                objects.append(models.StoreStatus(
                    store_id=row['store_id'],
                    timestamp_utc=dt_obj,
                    status=row['status']
                ))
            except ValueError as e:
                print(f"Skipping row due to parsing error for timestamp_utc '{row['timestamp_utc']}': {e} in row {row}")
                continue
        db.bulk_save_objects(objects)
        db.commit()

def bulk_insert_business_hours(db: Session, file_path: str):
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        objects = []
        for row in reader:
            if not row.get('store_id') or row.get('dayOfWeek') is None or not row.get('start_time_local') or not row.get('end_time_local'):
                print(f"Skipping malformed business hours row: {row}")
                continue
            try:
                start_time = datetime.strptime(row['start_time_local'], '%H:%M:%S').time()
                end_time = datetime.strptime(row['end_time_local'], '%H:%M:%S').time()
                objects.append(models.BusinessHours(
                    store_id=row['store_id'],
                    day_of_week=int(row['dayOfWeek']),
                    start_time_local=start_time,
                    end_time_local=end_time
                ))
            except ValueError as e:
                print(f"Skipping row due to parsing error: {e} in row {row}")
                continue
        db.bulk_save_objects(objects)
        db.commit()

def bulk_insert_store_timezones(db: Session, file_path: str):
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        objects = []
        for row in reader:
            if not row.get('store_id') or not row.get('timezone_str'):
        
                 objects.append(models.StoreTimezone(
                    store_id=row['store_id'],
                    timezone_str=DEFAULT_TIMEZONE 
                ))
                 continue
            objects.append(models.StoreTimezone(
                store_id=row['store_id'],
                timezone_str=row['timezone_str'] if row['timezone_str'] else DEFAULT_TIMEZONE
            ))
        db.bulk_save_objects(objects)
        db.commit()

def clear_data(db: Session):
    db.execute(text(f"DELETE FROM {models.ReportData.__tablename__}"))
    db.execute(text(f"DELETE FROM {models.Report.__tablename__}"))
    db.execute(text(f"DELETE FROM {models.StoreStatus.__tablename__}"))
    db.execute(text(f"DELETE FROM {models.BusinessHours.__tablename__}"))
    db.execute(text(f"DELETE FROM {models.StoreTimezone.__tablename__}"))
    db.commit()

def save_report_data(db: Session, report_id: str, report_data_list: list[dict]):
    objects = []
    for data in report_data_list:
        objects.append(models.ReportData(
            report_id=report_id,
            store_id=data['store_id'],
            uptime_last_hour=data['uptime_last_hour'],
            uptime_last_day=data['uptime_last_day'],
            uptime_last_week=data['uptime_last_week'],
            downtime_last_hour=data['downtime_last_hour'],
            downtime_last_day=data['downtime_last_day'],
            downtime_last_week=data['downtime_last_week']
        ))
    db.bulk_save_objects(objects)
    db.commit()

def update_report_status(db: Session, report_id: str, status: str, file_path: str = None):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if report:
        report.status = status
        if file_path:
            report.file_path = file_path
        db.commit()
    else: # Create if not exists (e.g. if trigger_report doesn't create it in DB)
        new_report = models.Report(id=report_id, status=status, file_path=file_path)
        db.add(new_report)
        db.commit()

def create_report_entry(db: Session, report_id: str):
    new_report = models.Report(id=report_id, status="Running")
    db.add(new_report)
    db.commit()

