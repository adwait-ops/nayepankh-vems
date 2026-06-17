# NayePankh Foundation Portal

An operational dashboard platform built for the NayePankh Foundation to manage volunteer registrations, schedule field events, and track allocations. The application automates the process of pairing available volunteers with relevant field events based on track preferences.

---

## Project Structure

The repository consists of the following key components:
* **`app.py`**: The primary Flask application file managing the web server routing, database connection sessions, and automatic/manual allocation workflows.
* **`models.py`**: Contains data models for `Volunteer` and `Event` handling ID generation, custom query filtering, and validation tracking.
* **`schema.sql`**: Database schema setup defining the relational structures for tracking personnel and scheduled events.
* **`requirements.txt`**: Lists the Python library dependencies required to build and execute the backend framework.
* **`.env`**: Configures required environment variable strings like secret keys and database targets.
* **`.gitignore`**: Specifies untracked files and patterns that Git should disregard, protecting temporary or credentialed local files.
* **`index.html`**: The main homepage template featuring an animated landing splash presentation.
* **`volunteers.html`**: UI view dashboard providing tools to register personnel and list active profiles.
* **`events.html`**: UI view panel providing tools to organize field drives, track capacity counts, and manually adjust rosters.

---

## Dependencies

The implementation runs on the following fundamental dependencies listed in `requirements.txt`:
* **Flask** (`3.1.2`): The core Python micro-framework handling web context mapping and layout routing.
* **python-dotenv** (`1.2.1`): Manages secure externalized parsing of workspace environment configurations.
* **sqlite3**: Built-in Python library providing local engine persistence management.

---

## Installation & Execution

Follow these setups to set up the runtime environment locally:

1. **Install Dependencies**  
   
```bash
   pip install -r requirements.txt
```
2. **Setup Config Environment**
    Create a `.env` file 

3. **Execute**
```bash
   python app.py
```

## Cloud Hosting Limitation

This application was initially planned for deployment on Vercel. However, hosting was not feasible because the project uses SQLite3, which stores data in a local database file (`nayepankh.db`).

- **Temporary Storage:** Vercel's serverless functions do not provide permanent local storage. Any changes made to the SQLite database can be lost when the server instance is restarted.
- **No Shared Database State:** Different serverless instances cannot reliably access the same local database file. This can lead to inconsistent data, synchronization issues, and user access problems.

As a result, the application requires a hosting solution with persistent storage or migration to a cloud-based database system.

## Future Scalability

To support future growth, the following enhancements are planned:

- **Volunteer Performance Tracking:** Add features to monitor volunteer hours, track participation across events, and measure engagement levels.

- **Automated Document Generation:** Enable automatic issuance of Certificates of Appreciation and Letters of Recommendation (LORs) when volunteers achieve predefined milestones.

- **Cloud Database Migration:** Replace the local SQLite database with a cloud-hosted solution such as PostgreSQL or MySQL to improve scalability, reliability, and deployment flexibility.