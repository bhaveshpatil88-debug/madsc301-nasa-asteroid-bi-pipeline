-- NASA BI Pipeline — PostgreSQL Schema

CREATE TABLE IF NOT EXISTS asteroids (
    asteroid_id              VARCHAR(20)  PRIMARY KEY,
    name                     TEXT         NOT NULL,
    absolute_magnitude_h     FLOAT,
    est_diameter_min_km      FLOAT,
    est_diameter_max_km      FLOAT,
    est_diameter_avg_km      FLOAT,
    size_category            VARCHAR(30),
    is_potentially_hazardous BOOLEAN      DEFAULT FALSE,
    is_sentry_object         BOOLEAN      DEFAULT FALSE,
    nasa_jpl_url             TEXT,
    created_at               TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS close_approaches (
    id                   SERIAL       PRIMARY KEY,
    asteroid_id          VARCHAR(20)  NOT NULL REFERENCES asteroids(asteroid_id) ON DELETE CASCADE,
    close_approach_date  DATE         NOT NULL,
    orbiting_body        VARCHAR(20)  DEFAULT 'Earth',
    velocity_kph         FLOAT,
    velocity_kps         FLOAT,
    miss_distance_km     FLOAT,
    miss_distance_lunar  FLOAT,
    miss_distance_au     FLOAT,
    risk_score           FLOAT,
    week_of_year         INT,
    ingested_at          TIMESTAMP    DEFAULT NOW(),
    UNIQUE (asteroid_id, close_approach_date)
);

CREATE INDEX IF NOT EXISTS idx_approaches_date ON close_approaches (close_approach_date DESC);
CREATE INDEX IF NOT EXISTS idx_approaches_risk ON close_approaches (risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_asteroids_hazardous ON asteroids (is_potentially_hazardous) WHERE is_potentially_hazardous = TRUE;

CREATE OR REPLACE VIEW daily_summary AS
SELECT ca.close_approach_date,
    COUNT(*) AS total_neos,
    SUM(a.is_potentially_hazardous::INT) AS hazardous_count,
    ROUND(AVG(ca.miss_distance_lunar)::NUMERIC, 2) AS avg_miss_distance_ld,
    ROUND(AVG(ca.velocity_kph)::NUMERIC, 0) AS avg_velocity_kph,
    ROUND(MAX(ca.risk_score)::NUMERIC, 2) AS max_risk_score
FROM close_approaches ca JOIN asteroids a USING (asteroid_id)
GROUP BY ca.close_approach_date ORDER BY ca.close_approach_date DESC;

CREATE OR REPLACE VIEW high_risk_alerts AS
SELECT a.name, ca.close_approach_date, ca.miss_distance_lunar,
    ca.miss_distance_km, ca.velocity_kph, ca.risk_score,
    a.est_diameter_avg_km, a.size_category
FROM close_approaches ca JOIN asteroids a USING (asteroid_id)
WHERE a.is_potentially_hazardous = TRUE AND ca.miss_distance_lunar < 10
ORDER BY ca.risk_score DESC;
