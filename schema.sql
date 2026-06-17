--drop tables if exists to restart
DROP TABLE IF EXISTS volunteers;
DROP TABLE IF EXISTS events;

-- volunteers table
CREATE TABLE volunteers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    assigned_drive TEXT NOT NULL
);

--events table
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    campaign_category TEXT NOT NULL,
    event_date TEXT NOT NULL,
    location TEXT NOT NULL,
    volunteers_needed INTEGER NOT NULL, 
    status TEXT NOT NULL DEFAULT 'Upcoming'
);