\
import os
from app import crud, database, models
from sqlalchemy.orm import Session


DATA_DIR = "data"
STORE_STATUS_CSV = os.path.join(DATA_DIR, "store_status.csv")
BUSINESS_HOURS_CSV = os.path.join(DATA_DIR, "business_hours.csv")
TIMEZONES_CSV = os.path.join(DATA_DIR, "timezones.csv") 

def check_files_exist():
    files_ok = True
    if not os.path.exists(STORE_STATUS_CSV):
        print(f"Error: Store status CSV not found at {STORE_STATUS_CSV}")
        files_ok = False
    if not os.path.exists(BUSINESS_HOURS_CSV):
        print(f"Error: Business hours CSV not found at {BUSINESS_HOURS_CSV}")
        files_ok = False
    if not os.path.exists(TIMEZONES_CSV):
        print(f"Error: Timezones CSV not found at {TIMEZONES_CSV}")
        print("Please ensure 'bq-results-20230125-202210-1674678181880.csv' is renamed to 'timezones.csv' in the data directory.")
        files_ok = False
    
    if not files_ok:
        print("\\nPlease ensure all CSV files are present in the 'data/' directory and named correctly:")
        print(f"  - {os.path.basename(STORE_STATUS_CSV)}")
        print(f"  - {os.path.basename(BUSINESS_HOURS_CSV)}")
        print(f"  - {os.path.basename(TIMEZONES_CSV)} (renamed from the bq-results... file)")
        print("Setup aborted.")
    return files_ok

def main():
    print("Starting initial data setup...")

    if not check_files_exist():
        return


    print("Creating database tables...")
    models.Base.metadata.create_all(bind=database.engine)
    print("Database tables created (if they didn't exist).")

    db: Session = next(database.get_db())

    try:
       
        print("Clearing existing data from tables...")
        crud.clear_data(db)
        print("Existing data cleared.")


        print(f"Loading store status data from {STORE_STATUS_CSV}...")
        crud.bulk_insert_store_status(db, STORE_STATUS_CSV)
        print("Store status data loaded.")

        print(f"Loading business hours data from {BUSINESS_HOURS_CSV}...")
        crud.bulk_insert_business_hours(db, BUSINESS_HOURS_CSV)
        print("Business hours data loaded.")

        print(f"Loading timezone data from {TIMEZONES_CSV}...")
        crud.bulk_insert_store_timezones(db, TIMEZONES_CSV)
        print("Timezone data loaded.")
        
        print("\\nInitial data setup complete!")
        
        max_ts = crud.get_max_timestamp(db)
        if max_ts:
            print(f"Max timestamp found in data (will be used as 'current time' for reports): {max_ts}")
        else:
            print("Warning: Could not determine max timestamp from store_status data.")

    except Exception as e:
        print(f"An error occurred during setup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created '{DATA_DIR}' directory. Please place your CSV files there and rename them as specified in README.md.")
        print("Expected files:")
        print(f"  - {os.path.basename(STORE_STATUS_CSV)}")
        print(f"  - {os.path.basename(BUSINESS_HOURS_CSV)}")
        print(f"  - {os.path.basename(TIMEZONES_CSV)} (renamed from bq-results-*.csv)")
    else:
        main()

