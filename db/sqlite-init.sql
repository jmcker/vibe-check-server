CREATE TABLE IF NOT EXISTS location (
    id INTEGER PRIMARY KEY,
    latitude TEXT NOT NULL,
    longitude TEXT NOT NULL,
    UNIQUE (latitude, longitude)
);

CREATE TABLE IF NOT EXISTS track (
    id INTEGER PRIMARY KEY,
    spotify_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    genre TEXT NOT NULL,
    popularity FLOAT NOT NULL,
    UNIQUE (title, artist)
);

CREATE TABLE IF NOT EXISTS vibe (
    location_id INTEGER REFERENCES location(id),
    track_id INTEGER REFERENCES track(id),
    count INTEGER DEFAULT 0,
    PRIMARY KEY (location_id, track_id)
);