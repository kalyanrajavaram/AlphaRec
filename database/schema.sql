-- Activity Tracker Database Schema

-- Table for browsing history
CREATE TABLE IF NOT EXISTS browsing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT,
    visit_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    leave_time TIMESTAMP,
    duration_seconds INTEGER,
    tab_id INTEGER,
    is_active BOOLEAN DEFAULT 1,
    active_duration_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_browsing_url ON browsing_history(url);
CREATE INDEX IF NOT EXISTS idx_browsing_time ON browsing_history(visit_time);
CREATE INDEX IF NOT EXISTS idx_browsing_duration ON browsing_history(duration_seconds);

-- Table for search queries
CREATE TABLE IF NOT EXISTS search_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    search_engine TEXT DEFAULT 'google',
    search_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    results_clicked TEXT,
    browsing_history_id INTEGER,
    FOREIGN KEY (browsing_history_id) REFERENCES browsing_history(id)
);

CREATE INDEX IF NOT EXISTS idx_search_query ON search_queries(query);
CREATE INDEX IF NOT EXISTS idx_search_time ON search_queries(search_time);

-- Table for search result clicks
CREATE TABLE IF NOT EXISTS search_result_clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_query_id INTEGER NOT NULL,
    result_url TEXT NOT NULL,
    result_title TEXT,
    result_position INTEGER,
    click_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    time_on_page_seconds INTEGER,
    FOREIGN KEY (search_query_id) REFERENCES search_queries(id)
);

CREATE INDEX IF NOT EXISTS idx_click_search_id ON search_result_clicks(search_query_id);
CREATE INDEX IF NOT EXISTS idx_click_url ON search_result_clicks(result_url);

-- Table for application usage
CREATE TABLE IF NOT EXISTS application_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name TEXT NOT NULL,
    app_bundle_id TEXT,
    window_title TEXT,
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    is_browser BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_app_name ON application_usage(app_name);
CREATE INDEX IF NOT EXISTS idx_app_time ON application_usage(start_time);
CREATE INDEX IF NOT EXISTS idx_app_duration ON application_usage(duration_seconds);

-- Table for user sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_start TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    total_active_seconds INTEGER DEFAULT 0,
    total_idle_seconds INTEGER DEFAULT 0,
    device_info TEXT
);

CREATE INDEX IF NOT EXISTS idx_session_start ON user_sessions(session_start);

-- Table for tracking settings
CREATE TABLE IF NOT EXISTS tracking_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    tracking_enabled BOOLEAN DEFAULT 1,
    data_retention_days INTEGER DEFAULT 90,
    last_cleanup TIMESTAMP,
    extension_version TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default settings
INSERT OR IGNORE INTO tracking_settings (id, tracking_enabled, data_retention_days, extension_version)
VALUES (1, 1, 90, '1.0.0');

-- Navigation events with transition info
CREATE TABLE IF NOT EXISTS navigation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    tab_id INTEGER,
    opener_tab_id INTEGER,
    transition_type TEXT,
    transition_qualifiers TEXT,
    is_spa_navigation BOOLEAN DEFAULT 0,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_nav_time ON navigation_events(event_time);
CREATE INDEX IF NOT EXISTS idx_nav_type ON navigation_events(transition_type);

-- Downloads
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    url TEXT,
    mime_type TEXT,
    file_size INTEGER,
    download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_download_time ON downloads(download_time);

-- Bookmarks
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT,
    bookmark_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bookmark_time ON bookmarks(bookmark_time);

-- User interactions (privacy-preserving)
CREATE TABLE IF NOT EXISTS user_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    tab_id INTEGER,
    interaction_type TEXT NOT NULL,
    interaction_data TEXT,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_interaction_time ON user_interactions(event_time);
CREATE INDEX IF NOT EXISTS idx_interaction_type ON user_interactions(interaction_type);
