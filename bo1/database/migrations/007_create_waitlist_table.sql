-- Migration 007: Create waitlist table for closed beta
-- Date: 2025-01-19

-- Create waitlist table
CREATE TABLE IF NOT EXISTS waitlist (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, approved, converted
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE,
    converted_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,

    -- Indexes
    CONSTRAINT waitlist_email_unique UNIQUE (email),
    CONSTRAINT waitlist_status_check CHECK (status IN ('pending', 'approved', 'converted'))
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_waitlist_email ON waitlist(email);
CREATE INDEX IF NOT EXISTS idx_waitlist_status ON waitlist(status);
CREATE INDEX IF NOT EXISTS idx_waitlist_created_at ON waitlist(created_at DESC);

-- Add comments
COMMENT ON TABLE waitlist IS 'Waitlist for closed beta access';
COMMENT ON COLUMN waitlist.email IS 'Email address (unique, lowercase)';
COMMENT ON COLUMN waitlist.status IS 'Waitlist status: pending (on waitlist), approved (granted access), converted (signed up)';
COMMENT ON COLUMN waitlist.created_at IS 'When user joined waitlist';
COMMENT ON COLUMN waitlist.approved_at IS 'When user was approved for beta access';
COMMENT ON COLUMN waitlist.converted_at IS 'When user created an account';
COMMENT ON COLUMN waitlist.notes IS 'Admin notes about this waitlist entry';
