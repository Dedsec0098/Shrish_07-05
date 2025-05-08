from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
import uuid
import os
from . import crud, schemas, report_generation, database

database.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

REPORTS_DIR = "generated_reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

report_status = {}

@app.post("/trigger_report", response_model=schemas.ReportID)
async def trigger_report_endpoint(background_tasks: BackgroundTasks):
    report_id = str(uuid.uuid4())
    report_status[report_id] = "Running"
    
    db = next(database.get_db())
    max_timestamp_str = crud.get_max_timestamp(db)
    db.close()

    if not max_timestamp_str:
        raise HTTPException(status_code=500, detail="Could not determine max timestamp from data.")

    background_tasks.add_task(report_generation.generate_report_logic, report_id, REPORTS_DIR, report_status, max_timestamp_str)
    return {"report_id": report_id}

@app.get("/get_report/{report_id}")
async def get_report_endpoint(report_id: str):
    status = report_status.get(report_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Report ID not found.")
    
    if status == "Running":
        return {"status": "Running"}
    elif status == "Complete":
        report_file_path = os.path.join(REPORTS_DIR, f"{report_id}.csv")
        if os.path.exists(report_file_path):
            return FileResponse(report_file_path, media_type='text/csv', filename=f"{report_id}.csv", headers={"Content-Disposition": f"attachment; filename={report_id}.csv"})
        else:
            report_status[report_id] = "Error"
            raise HTTPException(status_code=500, detail="Report file not found but status was Complete. Please try triggering again.")
    elif status == "Error":
        raise HTTPException(status_code=500, detail="Report generation failed.")
    else:
        raise HTTPException(status_code=500, detail="Unknown report status.")

