\
# Loop Backend - Restaurant Uptime Monitoring

## Project Overview
This project is a backend system designed to monitor the uptime and downtime of restaurants in the US. It provides restaurant owners with detailed reports about how often their stores were online or offline during their business hours. The system uses data from periodic polls, business hours, and timezones to calculate uptime and downtime metrics.

### Key Features
- **Dynamic Report Generation**: Generates reports on demand, detailing uptime and downtime for the last hour, day, and week.
- **APIs**:
  - `/trigger_report`: Triggers the generation of a report.
  - `/get_report/{report_id}`: Retrieves the status of the report or the generated CSV file.
- **Data Handling**:
  - Handles missing data by assuming default values (e.g., 24/7 business hours, `America/Chicago` timezone).
  - Extrapolates uptime/downtime based on periodic polls.

---

## How to Run the Project

### Prerequisites
Ensure the following are installed on your system:
- **Python 3.11+**
- **pip**
- **Virtual Environment (optional)**
- **Docker (optional)**

### Step-by-Step Guide

#### 1. Install Dependencies
1. Navigate to the project directory:
   ```bash
   cd /Users/shrishmishra/Desktop/Loop-Backend
   ```
2. Create and activate a virtual environment (optional):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

#### 2. Prepare the Database
1. Ensure the following CSV files are in the `data/` directory:
   - `store_status.csv`
   - `business_hours.csv`
   - `timezones.csv`
2. Run the initial setup script to populate the database:
   ```bash
   python initial_setup.py
   ```

#### 3. Start the Application
1. Run the FastAPI application using Uvicorn:
   ```bash
   uvicorn app.main:app --reload
   ```
2. Access the application at `http://127.0.0.1:8000`.

#### 4. Test the APIs
- **Trigger a Report**:
  - Send a `POST` request to `/trigger_report`.
  - Example using `curl`:
    ```bash
    curl -X POST http://127.0.0.1:8000/trigger_report
    ```
  - Response:
    ```json
    { "report_id": "some-unique-uuid" }
    ```
- **Get the Report Status**:
  - Send a `GET` request to `/get_report/{report_id}`.
  - Example using `curl`:
    ```bash
    curl http://127.0.0.1:8000/get_report/some-unique-uuid
    ```
  - Response:
    - If the report is still being generated:
      ```json
      { "status": "Running" }
      ```
    - If the report is complete, the CSV file will be returned.

#### 5. Run Tests
1. Install testing dependencies:
   ```bash
   pip install pytest pytest-asyncio httpx
   ```
2. Run the tests:
   ```bash
   pytest
   ```

---

## Ideas for Improvement
Here are some potential improvements to enhance the solution:

1. **Scalability**:
   - Use a more robust database like PostgreSQL instead of SQLite for handling larger datasets.
   - Implement asynchronous database queries to improve performance.

2. **Error Handling**:
   - Add more detailed error messages and logging for debugging.
   - Handle edge cases like overlapping business hours more efficiently.

3. **Optimization**:
   - Optimize the `calculate_uptime_downtime` function to handle large datasets more efficiently.
   - Use caching for frequently accessed data like business hours and timezones.

4. **Frontend Integration**:
   - Build a simple frontend dashboard to visualize uptime/downtime metrics.

5. **Containerization**:
   - Provide a Docker Compose setup to simplify deployment with services like PostgreSQL.

6. **Monitoring and Alerts**:
   - Add real-time monitoring and alerting for downtime events.

---

This README provides a comprehensive guide to understanding, running, and improving the project. Let us know if you encounter any issues or have suggestions for further enhancements!

