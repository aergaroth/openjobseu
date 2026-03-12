CREATE TABLE market_daily_stats_segments (
    date DATE NOT NULL,

    segment_type TEXT NOT NULL,
    segment_value TEXT NOT NULL,

    jobs_active INTEGER NOT NULL,
    jobs_created INTEGER NOT NULL,

    avg_salary_eur NUMERIC,
    median_salary_eur NUMERIC,

    PRIMARY KEY (date, segment_type, segment_value)
);

CREATE INDEX idx_market_segments_date
ON market_daily_stats_segments(date);