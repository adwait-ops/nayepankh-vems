import sqlite3
from datetime import datetime


class Volunteer:

    def __init__(
        self,
        vol_id,
        name,
        email,
        phone,
        city,
        pincode,
        skills,
        status="Active",
    ):
        self.id = vol_id
        self.name = name
        self.email = email
        self.phone = phone
        self.city = city
        self.pincode = pincode
        self.skills = skills  #Expected as a comma-separated string (example: "Food Distribution, Social Media")
        self.status = status  #Active, On-Leave, Completed

    @staticmethod
    def generate_next_id():
        #automatically calculates next sequence identification string for a new volunteer
        conn = sqlite3.connect("nayepankh.db")
        cursor = conn.cursor()

        #get total row count to safely increment sequential sequence
        cursor.execute("SELECT COUNT(*) FROM volunteers")
        count = cursor.fetchone()[0]
        conn.close()

        current_year = datetime.now().year
        #returns a cleanly formatted, zero-padded structural ID token
        return f"NP-VOL-{current_year}-{str(count + 1).zfill(3)}"

    def save_to_db(self):
        #maps and commits current instance to the sqlite database
        conn = sqlite3.connect("nayepankh.db")
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO volunteers (id, name, email, phone, city, pincode, skills, status) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                #insert into values
                (
                    self.id,
                    self.name,
                    self.email,
                    self.phone,
                    self.city,
                    self.pincode,
                    self.skills,
                    self.status,
                ),
            )

            
            conn.commit()
            return True, "Volunteer registered successfully!"
        except sqlite3.IntegrityError:
            #triggered if unique constraints (like email) are broken
            return (
                False,
                "Operational Fault: A volunteer with this email address is already registered.",
            )
        finally:
            conn.close()

    @staticmethod
    def search_and_filter(search_query="", city_filter=""):
        #class method: assembles and executes sql queries based on runtime search params passed down from the dashboard
        conn = sqlite3.connect("nayepankh.db")
        cursor = conn.cursor()

        #base structure execution block
        query = "SELECT * FROM volunteers WHERE 1=1"
        parameters = []

        if search_query:
            query += " AND (name LIKE ? OR id LIKE ? OR skills LIKE ?)"
            match_string = f"%{search_query}%"
            parameters.extend([match_string, match_string, match_string])

        if city_filter:
            query += " AND city = ?"
            parameters.append(city_filter)

        cursor.execute(query, parameters)
        rows = cursor.fetchall()


        
        conn.close()
        return rows


class Event:

    def __init__(
        self,
        event_id,
        title,
        category,
        date,
        location,
        volunteers_needed,
        status="Upcoming",
    ):
        self.id = event_id
        self.title = title
        self.category = category  #example: Stray Feeding, Sanitary Drive, Education Pack
        self.date = date  #ISO Date String format: yyyy-mm-dd
        self.location = location
        self.volunteers_needed = int(volunteers_needed)
        self.status = status  #upcoming, ongoing, concluded

    @staticmethod
    def save_event(title, category, date, location, volunteers_needed):
        #commits newly proposed foundation project block into the events table
        conn = sqlite3.connect("nayepankh.db")
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO events (title, campaign_category, event_date, location, volunteers_needed, status) 
               VALUES (?, ?, ?, ?, ?, 'Upcoming')""",
            (title, category, date, location, int(volunteers_needed)),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def assign_volunteer_to_event(event_id, volunteer_id):
        #calculates the metrics to protect campaigns against over-allocation before committing
        conn = sqlite3.connect("nayepankh.db")
        cursor = conn.cursor()

        #query current roster count for this target campaign ID
        cursor.execute(
            "SELECT COUNT(*) FROM allocations WHERE event_id = ?", (event_id,)
        )
        current_headcount = cursor.fetchone()[0]

        #grab the maximum staffing capability threshold allowed for this event
        cursor.execute(
            "SELECT volunteers_needed FROM events WHERE id = ?", (event_id,)
        )
        event_data = cursor.fetchone()

        if not event_data:
            conn.close()
            return False, "Error: Selected event campaign does not exist."

        maximum_capacity = event_data[0]

        #enforce threshold check 
        if current_headcount >= maximum_capacity:
            conn.close()
            return (
                False,
                f"Roster Allocation Rejected: Staffing cap limit ({maximum_capacity}) has strictly been reached",
            )

        
        try:
            cursor.execute(
                "INSERT INTO allocations (event_id, volunteer_id) VALUES (?, ?)",
                (int(event_id), volunteer_id),
            )
            conn.commit()
            return True, "Volunteer assignment successfully committed to roster."
        except sqlite3.IntegrityError:
            #catches double-assignment bugs caused by UNIQUE(event_id, volunteer_id) schema constraint
            return (
                False,
                "Constraint Warning: Selected volunteer is already assigned to this specific campaign",
            )
        finally:
            conn.close()

    @staticmethod
    def get_event_roster(event_id):
        #fetches full profiles of volunteers mapped to a certain campaign id
        conn = sqlite3.connect("nayepankh.db")
        cursor = conn.cursor()
        cursor.execute(
            """SELECT v.id, v.name, v.phone, v.city 
               FROM volunteers v
               JOIN allocations a ON v.id = a.volunteer_id
               WHERE a.event_id = ?""",
            (event_id,),
        )
        roster = cursor.fetchall()
        conn.close()
        return roster