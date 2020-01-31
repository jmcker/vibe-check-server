INSERT OR IGNORE INTO genre (
    name
) VALUES ('Pop'), ('Rock');

INSERT OR IGNORE INTO artist (
    spotify_id,
    name
) VALUES
    ('6M2wZ9GZgrQXHCFfjv46we', 'Dua Lipa'),
    ('0Cp8WN4V8Tu4QJQwCN5Md4', 'BENEE'),
    ('58lV9VcRSjABbAbfWS6skp', 'Bon Jovi')
;

INSERT OR IGNORE INTO track (
    spotify_id,
    genre_id,
    artist_id,
    title,
    album,
    popularity
) VALUES
    ('6WrI0LAC5M1Rw2MnX2ZvEg', 1, 1, 'Dont Start Now', 'Dont Start Now (Album)', 80),
    ('4Ve0Jx7MXjU4aPrFHJRZK7', 1, 2, 'Find an Island', 'STELLA & STEVE', 70),
    ('5ZH9eXVK1rs0NboOhvY86Y', 2, 3, 'Two Story Town', 'Crush', 60)
;

INSERT OR IGNORE INTO location (
    latitude,
    longitude
) VALUES
    (42.9, -85.34),
    (34.3, -87.98)
;

INSERT OR IGNORE INTO vibe (
    location_id,
    track_id,
    count,
    last_vibed
) VALUES
    (1, 1, 2, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    (1, 2, 4, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    (1, 3, 3, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    (2, 1, 4, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    (2, 2, 2, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    (2, 3, 5, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
;
