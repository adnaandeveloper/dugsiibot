CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    pricing_type TEXT DEFAULT 'hourly',
    hourly_rate INTEGER DEFAULT 0,
    monthly_price INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS lessons (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    date TIMESTAMP DEFAULT NOW(),
    amount INTEGER NOT NULL,
    note TEXT,
    invoiced BOOLEAN DEFAULT FALSE,
    hours NUMERIC
);
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    date TIMESTAMP DEFAULT NOW(),
    amount INTEGER NOT NULL,
    status TEXT DEFAULT 'betalt',
    note TEXT
);
-- migrer gamle tabeller hvis de findes
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='customers' AND column_name='pricing_type') THEN
        ALTER TABLE customers ADD COLUMN pricing_type TEXT DEFAULT 'hourly';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='customers' AND column_name='monthly_price') THEN
        ALTER TABLE customers ADD COLUMN monthly_price INTEGER DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='lessons' AND column_name='hours') THEN
        ALTER TABLE lessons ADD COLUMN hours NUMERIC;
    END IF;
END $$;