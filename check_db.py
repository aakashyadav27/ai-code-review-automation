import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(url, key)

sql = """
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Installations table
CREATE TABLE IF NOT EXISTS installations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_installation_id BIGINT UNIQUE NOT NULL,
    owner_login VARCHAR(255) NOT NULL,
    owner_type VARCHAR(50) DEFAULT 'User',
    api_key_encrypted TEXT,
    enabled BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{"review_style": true, "review_security": true, "review_performance": true, "review_logic": true, "auto_approve": false}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    installation_id UUID REFERENCES installations(id) ON DELETE CASCADE,
    repo_full_name VARCHAR(255) NOT NULL,
    pr_number INTEGER NOT NULL,
    pr_title VARCHAR(500),
    commit_sha VARCHAR(40),
    files_reviewed INTEGER DEFAULT 0,
    issues_found INTEGER DEFAULT 0,
    issues_by_type JSONB DEFAULT '{"style": 0, "security": 0, "performance": 0, "logic": 0}'::jsonb,
    review_duration_ms INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_installations_github_id ON installations(github_installation_id);
CREATE INDEX IF NOT EXISTS idx_reviews_installation ON reviews(installation_id);
CREATE INDEX IF NOT EXISTS idx_reviews_repo ON reviews(repo_full_name);
CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at DESC);
"""

# Split statements and execute individually (Supabase-py doesn't support executing raw SQL block directly easily without RPC, but we can try via REST if enabled, or just inform user to run it)
print("Note: Python client cannot run DDL (CREATE TABLE) directly without a postgres functions.")
print("Please run the content of db/schema.sql in your Supabase SQL Editor.")
