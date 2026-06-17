import sqlite3
import os
import re
import datetime
from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, url_for

current_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_dir, 'templates')
load_dotenv()

app = Flask(__name__, template_folder=template_dir)
app.secret_key = os.getenv("SECRET_KEY")



DATABASE_FILE = os.getenv("DATABASE_FILE")

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  
    return conn



def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            assigned_drive TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
            event_date TEXT NOT NULL,
            volunteers_needed INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS allocations (
            event_id INTEGER,
            volunteer_id INTEGER,
            PRIMARY KEY (event_id, volunteer_id),
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (volunteer_id) REFERENCES volunteers(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manual_unassignments (
            event_id INTEGER,
            volunteer_id INTEGER,
            PRIMARY KEY (event_id, volunteer_id),
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (volunteer_id) REFERENCES volunteers(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# init_db()


def auto_assign_volunteers():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    events = cursor.execute('SELECT * FROM events ORDER BY event_date ASC').fetchall()
    volunteers = cursor.execute('SELECT * FROM volunteers').fetchall()
    
    for vol in volunteers:
        vol_id = vol['id']
        
        already_allocated = cursor.execute('''
            SELECT 1 FROM allocations a
            JOIN events e ON a.event_id = e.id
            WHERE a.volunteer_id = ? AND e.event_date >= ?
        ''', (vol_id, today_str)).fetchone()
        
        if already_allocated:
            continue  
            
        track_words = set(vol['assigned_drive'].lower().replace('_', ' ').split())
        
        for event in events:
            event_id = event['id']
            event_date = event['event_date']
            
            if event_date < today_str:
                continue
                
            was_manually_unassigned = cursor.execute('''
                SELECT 1 FROM manual_unassignments 
                WHERE event_id = ? AND volunteer_id = ?
            ''', (event_id, vol_id)).fetchone()
            
            if was_manually_unassigned:
                continue 
                
            title_words = set(event['title'].lower().replace('_', ' ').split())
            
            if bool(track_words & title_words):  
                max_capacity = event['volunteers_needed'] 
                current_count = cursor.execute('SELECT COUNT(*) FROM allocations WHERE event_id = ?', (event_id,)).fetchone()[0]
                
                if current_count < max_capacity:
                    cursor.execute('INSERT INTO allocations (event_id, volunteer_id) VALUES (?, ?)', (event_id, vol_id))
                    break 
                        
    conn.commit()
    conn.close()


@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')


@app.route('/volunteers', methods=['GET'])
def view_volunteers():
    auto_assign_volunteers()  
    conn = get_db_connection()
    query = '''
        SELECT v.*, GROUP_CONCAT(e.title, ', ') as assigned_events
        FROM volunteers v
        LEFT JOIN allocations a ON v.id = a.volunteer_id
        LEFT JOIN events e ON a.event_id = e.id
        GROUP BY v.id
    '''
    volunteers = conn.execute(query).fetchall()
    conn.close()
    return render_template('volunteers.html', volunteers=volunteers)

@app.route('/add-volunteer', methods=['POST'])
def add_volunteer():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    assigned_drive = request.form.get('assigned_drive')
    
    if not name or not email or not phone or not assigned_drive:
        return redirect(url_for('view_volunteers'))
    if not re.match(r'^\d{10}$', phone) or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return redirect(url_for('view_volunteers'))

    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO volunteers (name, email, phone, assigned_drive)
            VALUES (?, ?, ?, ?)
        ''', (name, email, phone, assigned_drive))
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        pass
            
    return redirect(url_for('view_volunteers'))

@app.route('/remove-volunteer/<int:volunteer_id>', methods=['POST', 'GET'])
def remove_volunteer(volunteer_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM allocations WHERE volunteer_id = ?', (volunteer_id,))
    conn.execute('DELETE FROM manual_unassignments WHERE volunteer_id = ?', (volunteer_id,))
    conn.execute('DELETE FROM volunteers WHERE id = ?', (volunteer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_volunteers'))


@app.route('/events', methods=['GET'])
def view_events():
    auto_assign_volunteers()  
    conn = get_db_connection()
    
    query_events = '''
        SELECT e.*, 
               COUNT(a.volunteer_id) as total_assigned,
               (e.volunteers_needed - COUNT(a.volunteer_id)) as slots_remaining,
               GROUP_CONCAT(v.id || ':' || v.name, '||') as volunteer_details
        FROM events e
        LEFT JOIN allocations a ON e.id = a.event_id
        LEFT JOIN volunteers v ON a.volunteer_id = v.id
        GROUP BY e.id
        ORDER BY e.event_date ASC
    '''
    raw_events = conn.execute(query_events).fetchall()
    
    today = datetime.date.today()
    events = []
    
    for row in raw_events:
        event_dict = dict(row)
        event_dict['volunteer_list'] = []
        
        if event_dict['volunteer_details']:
            details = event_dict['volunteer_details'].split('||')
            for detail in details:
                if ':' in detail:
                    v_id, v_name = detail.split(':', 1)
                    event_dict['volunteer_list'].append({'id': int(v_id), 'name': v_name})
                    
        try:
            event_date_object = datetime.datetime.strptime(event_dict['event_date'], '%Y-%m-%d').date()
            if event_date_object < today:
                event_dict['status'] = 'Expired'
            elif event_date_object == today:
                event_dict['status'] = 'Ongoing'
            else:
                event_dict['status'] = 'Upcoming'
        except ValueError:
            event_dict['status'] = 'Upcoming'
            
        events.append(event_dict)
    
    query_all_volunteers = '''
        SELECT v.*, GROUP_CONCAT(e.title, ', ') as active_assignments
        FROM volunteers v
        LEFT JOIN allocations a ON v.id = a.volunteer_id
        LEFT JOIN events e ON a.event_id = e.id
        GROUP BY v.id
    '''
    all_volunteers = conn.execute(query_all_volunteers).fetchall()
    
    conn.close()
    return render_template('events.html', events=events, unassigned_volunteers=all_volunteers)

@app.route('/add-event', methods=['POST'])
def add_event():
    title = request.form.get('title')
    category = request.form.get('category') or ""
    event_date = request.form.get('event_date')
    location = request.form.get('location')
    volunteers_needed = request.form.get('volunteers_needed') or request.form.get('slots_needed') or 0

    full_title = f"{category}: {title}" if category and category not in title else title

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO events (title, location, event_date, volunteers_needed)
        VALUES (?, ?, ?, ?)
    ''', (full_title, location, event_date, int(volunteers_needed)))
    conn.commit()
    conn.close()
    return redirect('/events')

@app.route('/manual-assign', methods=['POST'])
def manual_assign():
    event_id = request.form.get('event_id')
    volunteer_id = request.form.get('volunteer_id')
    
    if event_id and volunteer_id:
        conn = get_db_connection()
        event = conn.execute('SELECT volunteers_needed FROM events WHERE id = ?', (event_id,)).fetchone()
        current_count = conn.execute('SELECT COUNT(*) FROM allocations WHERE event_id = ?', (event_id,)).fetchone()[0]
        
        if event and current_count < event['volunteers_needed']:
            try:
                conn.execute('DELETE FROM manual_unassignments WHERE event_id = ? AND volunteer_id = ?', (int(event_id), int(volunteer_id)))
                conn.execute('INSERT OR IGNORE INTO allocations (event_id, volunteer_id) VALUES (?, ?)', (int(event_id), int(volunteer_id)))
                conn.commit()
            except sqlite3.IntegrityError:
                pass
        conn.close()
    return redirect('/events')

@app.route('/unassign-volunteer/<int:event_id>/<int:volunteer_id>', methods=['GET', 'POST'])
def unassign_volunteer(event_id, volunteer_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM allocations WHERE event_id = ? AND volunteer_id = ?', (event_id, volunteer_id))
    conn.execute('INSERT OR IGNORE INTO manual_unassignments (event_id, volunteer_id) VALUES (?, ?)', (event_id, volunteer_id))
    conn.commit()
    conn.close()
    return redirect(url_for('view_events'))

@app.route('/remove-event/<int:id>')
def remove_event(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM allocations WHERE event_id = ?', (id,))
    conn.execute('DELETE FROM manual_unassignments WHERE event_id = ?', (id,))
    conn.execute('DELETE FROM events WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/events')

if __name__ == '__main__':
    init_db()
    app.run()