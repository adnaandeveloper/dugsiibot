CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    hourly_rate INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS lessons (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    date TIMESTAMP DEFAULT NOW(),
    amount INTEGER NOT NULL,
    note TEXT,
    invoiced BOOLEAN DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    date TIMESTAMP DEFAULT NOW(),
    amount INTEGER NOT NULL,
    status TEXT DEFAULT 'betalt',
    note TEXT
);
