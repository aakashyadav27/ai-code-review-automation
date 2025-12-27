-- Supabase Schema for AI Code Review Automation
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Installations table: stores GitHub App installations
CREATE TABLE installations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_installation_id BIGINT UNIQUE NOT NULL,
    owner_login VARCHAR(255) NOT NULL,
    owner_type VARCHAR(50) DEFAULT 'User', -- 'User' or 'Organization'
    api_key_encrypted TEXT, -- Encrypted Gemini API key
    enabled BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{
        "review_style": true,
        "review_security": true,
        "review_performance": true,
        "review_logic": true,
        "auto_approve": false
    }'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Reviews table: stores review history for analytics
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    installation_id UUID REFERENCES installations(id) ON DELETE CASCADE,
    repo_full_name VARCHAR(255) NOT NULL, -- e.g., "owner/repo"
    pr_number INTEGER NOT NULL,
    pr_title VARCHAR(500),
    commit_sha VARCHAR(40),
    files_reviewed INTEGER DEFAULT 0,
    issues_found INTEGER DEFAULT 0,
    issues_by_type JSONB DEFAULT '{
        "style": 0,
        "security": 0,
        "performance": 0,
        "logic": 0
    }'::jsonb,
    review_duration_ms INTEGER,
    status VARCHAR(50) DEFAULT 'pending', -- pending, completed, failed
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX idx_installations_github_id ON installations(github_installation_id);
CREATE INDEX idx_reviews_installation ON reviews(installation_id);
CREATE INDEX idx_reviews_repo ON reviews(repo_full_name);
CREATE INDEX idx_reviews_created ON reviews(created_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
CREATE TRIGGER update_installations_updated_at
    BEFORE UPDATE ON installations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) - optional but recommended
ALTER TABLE installations ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything
CREATE POLICY "Service role full access to installations" ON installations
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to reviews" ON reviews
    FOR ALL USING (auth.role() = 'service_role');
