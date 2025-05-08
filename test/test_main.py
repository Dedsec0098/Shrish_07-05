from fastapi.testclient import TestClient
from app.main import app
from app import crud, database, models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import time
import shutil

TEST_DATABASE_URL = "sqlite:///./test_store_monitoring.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[database.get_db] = override_get_db

client = TestClient(app)

SAMPLE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data_for_tests")
STORE_STATUS_CSV = os.path.join(SAMPLE_DATA_DIR, "store_status.csv")
BUSINESS_HOURS_CSV = os.path.join(SAMPLE_DATA_DIR, "business_hours.csv")
TIMEZONES_CSV = os.path.join(SAMPLE_DATA_DIR, "timezones.csv")
REPORTS_TEST_DIR = "generated_reports_test"


def setup_module(module):
    models.Base.metadata.create_all(bind=engine)
    os.makedirs(REPORTS_TEST_DIR, exist_ok=True)
    app.state.REPORTS_DIR = REPORTS_TEST_DIR
    from app import main as main_app
    main_app.REPORTS_DIR = REPORTS_TEST_DIR


    os.makedirs(SAMPLE_DATA_DIR, exist_ok=True)
    if not os.path.exists(STORE_STATUS_CSV):
        with open(STORE_STATUS_CSV, "w") as f:
            f.write("store_id,timestamp_utc,status\\n")
            f.write("1,2023-01-25 10:00:00.000000 UTC,active\\n")
            f.write("1,2023-01-25 09:00:00.000000 UTC,inactive\\n")
            f.write("2,2023-01-25 10:00:00.000000 UTC,active\\n")


    if not os.path.exists(BUSINESS_HOURS_CSV):
        with open(BUSINESS_HOURS_CSV, "w") as f:
            f.write("store_id,dayOfWeek,start_time_local,end_time_local\\n")
            f.write("1,0,09:00:00,17:00:00\\n")

    if not os.path.exists(TIMEZONES_CSV):
        with open(TIMEZONES_CSV, "w") as f:
            f.write("store_id,timezone_str\\n")
            f.write("1,America/New_York\\n")


def teardown_module(module):
    if os.path.exists("./test_store_monitoring.db"):
        os.remove("./test_store_monitoring.db")
    if os.path.exists(REPORTS_TEST_DIR):
        shutil.rmtree(REPORTS_TEST_DIR)
    if os.path.exists(SAMPLE_DATA_DIR):
        shutil.rmtree(SAMPLE_DATA_DIR)
    app.dependency_overrides.clear()


def load_test_data():
    db = TestingSessionLocal()
    crud.clear_data(db)
    crud.bulk_insert_store_status(db, STORE_STATUS_CSV)
    crud.bulk_insert_business_hours(db, BUSINESS_HOURS_CSV)
    crud.bulk_insert_store_timezones(db, TIMEZONES_CSV)
    db.close()


def test_trigger_report():
    load_test_data()
    response = client.post("/trigger_report")
    assert response.status_code == 200
    json_response = response.json()
    assert "report_id" in json_response
    report_id = json_response["report_id"]
    assert isinstance(report_id, str)
    from app.main import report_status as main_report_status
    assert main_report_status.get(report_id) == "Running"


def test_get_report_running_and_complete():
    load_test_data()
    trigger_response = client.post("/trigger_report")
    assert trigger_response.status_code == 200
    report_id = trigger_response.json()["report_id"]

    status_response = client.get(f"/get_report/{report_id}")
    assert status_response.status_code == 200
    assert status_response.json() == {"status": "Running"}

    max_wait_time = 30
    start_time = time.time()
    completed = False
    while time.time() - start_time < max_wait_time:
        status_response = client.get(f"/get_report/{report_id}")
        if status_response.json() != {"status": "Running"}:
            completed = True
            break
        time.sleep(0.5)
    
    assert completed, "Report did not complete in time"
    
    final_status_response = client.get(f"/get_report/{report_id}")
    assert final_status_response.status_code == 200
    
    assert final_status_response.headers["content-type"] == "text/csv"
    assert "attachment; filename=" in final_status_response.headers["content-disposition"]
    
    report_file_path = os.path.join(REPORTS_TEST_DIR, f"{report_id}.csv")
    assert os.path.exists(report_file_path)
    
    with open(report_file_path, 'r') as f:
        header = f.readline().strip()
        assert header == "store_id,uptime_last_hour,uptime_last_day,uptime_last_week,downtime_last_hour,downtime_last_day,downtime_last_week"


def test_get_report_not_found():
    response = client.get("/get_report/non_existent_id")
    assert response.status_code == 404
    assert response.json() == {"detail": "Report ID not found."}

