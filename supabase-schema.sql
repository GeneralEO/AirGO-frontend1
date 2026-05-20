-- ============================================
-- AIRGO Supabase Schema v3
-- Run this in Supabase SQL Editor
-- ============================================

-- Users table (linked to Clerk)
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    clerk_user_id TEXT UNIQUE,
    email TEXT,
    full_name TEXT,
    phone TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Bookings table (works with or without Clerk auth)
CREATE TABLE IF NOT EXISTS bookings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    clerk_user_id TEXT,               -- NULL if user wasn't signed in
    booking_reference TEXT UNIQUE NOT NULL,
    airline TEXT NOT NULL,
    flight_number TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_time TEXT,
    arrival_time TEXT DEFAULT '',
    flight_date TEXT DEFAULT '',
    duration TEXT DEFAULT '',
    passenger_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    price NUMERIC NOT NULL,
    currency TEXT DEFAULT 'NGN',
    payment_method TEXT DEFAULT 'card',
    payment_reference TEXT,
    payment_status TEXT DEFAULT 'completed',
    status TEXT DEFAULT 'confirmed',
    booked_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_bookings_email ON bookings(email);
CREATE INDEX IF NOT EXISTS idx_bookings_clerk_user ON bookings(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_reference ON bookings(booking_reference);
CREATE INDEX IF NOT EXISTS idx_users_clerk ON users(clerk_user_id);

-- If table already exists and you need to ADD new columns, run these:
-- ALTER TABLE bookings ADD COLUMN IF NOT EXISTS clerk_user_id TEXT;
-- ALTER TABLE bookings ADD COLUMN IF NOT EXISTS flight_date TEXT DEFAULT '';
-- ALTER TABLE bookings ADD COLUMN IF NOT EXISTS duration TEXT DEFAULT '';
-- ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booked_at TIMESTAMPTZ DEFAULT now();

-- Enable Row Level Security (optional, recommended for production)
-- ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
