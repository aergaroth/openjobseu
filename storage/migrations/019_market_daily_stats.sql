CREATE TABLE market_daily_stats (
    date DATE PRIMARY KEY,

    jobs_created INTEGER NOT NULL,
    jobs_expired INTEGER NOT NULL,
    jobs_active INTEGER NOT NULL,
    jobs_reposted INTEGER NOT NULL,

    avg_salary_eur NUMERIC,
    median_salary_eur NUMERIC,

    avg_job_lifetime INTERVAL,

    remote_ratio NUMERIC
);

CREATE INDEX idx_market_daily_stats_date
ON market_daily_stats(date);