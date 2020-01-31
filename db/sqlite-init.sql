PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS location (
    id INTEGER PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    UNIQUE (latitude, longitude)
);

CREATE TABLE IF NOT EXISTS genre (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS artist (
    id INTEGER PRIMARY KEY,
    spotify_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS track (
    id INTEGER PRIMARY KEY,
    spotify_id TEXT NOT NULL UNIQUE,
    genre_id INTEGER REFERENCES genre(id),
    artist_id INTEGER REFERENCES artist(id),
    title TEXT NOT NULL,
    album TEXT NOT NULL,
    original_genre TEXT,
    popularity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS vibe (
    location_id INTEGER REFERENCES location(id),
    track_id INTEGER REFERENCES track(id),
    count INTEGER DEFAULT 0,
    last_vibed TEXT NOT NULL,
    PRIMARY KEY (location_id, track_id)
);