-- Reference data the assistant may read. Fictional bank, no customer data.
CREATE SCHEMA reference;

CREATE TABLE reference.plans (
    plan_id            text PRIMARY KEY,
    name               text NOT NULL,
    monthly_price_eur  numeric(6, 2) NOT NULL CHECK (monthly_price_eur >= 0)
);

CREATE TABLE reference.supported_countries (
    country_code        char(2) PRIMARY KEY,
    name                text NOT NULL UNIQUE,
    aliases             text[] NOT NULL DEFAULT '{}',   -- lower-case alternative names
    can_open_account    boolean NOT NULL,
    card_delivery_days_min integer CHECK (card_delivery_days_min > 0),
    card_delivery_days_max integer CHECK (card_delivery_days_max >= card_delivery_days_min),
    cash_top_up         boolean NOT NULL DEFAULT false,   -- cash at partner retail points
    transfers_allowed   boolean NOT NULL DEFAULT true
);

CREATE TABLE reference.fees (
    plan_id           text NOT NULL REFERENCES reference.plans,
    fee_type          text NOT NULL,
    fixed_eur         numeric(8, 2) CHECK (fixed_eur >= 0),
    percent           numeric(5, 2) CHECK (percent >= 0),
    monthly_free_eur  numeric(10, 2) CHECK (monthly_free_eur >= 0),  -- free allowance before the fee applies
    note              text,
    PRIMARY KEY (plan_id, fee_type)
);

CREATE TABLE reference.limits (
    plan_id     text NOT NULL REFERENCES reference.plans,
    limit_type  text NOT NULL,
    value       numeric(12, 2) NOT NULL CHECK (value >= 0),
    unit        text NOT NULL,
    note        text,
    PRIMARY KEY (plan_id, limit_type)
);

CREATE TABLE reference.currencies (
    code        char(3) PRIMARY KEY,
    name        text NOT NULL,
    can_hold    boolean NOT NULL DEFAULT true,
    can_top_up  boolean NOT NULL DEFAULT false
);

CREATE TABLE reference.exchange_rates (
    base        char(3) NOT NULL REFERENCES reference.currencies,
    quote       char(3) NOT NULL REFERENCES reference.currencies,
    rate        numeric(14, 6) NOT NULL CHECK (rate > 0),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (base, quote)
);

CREATE TABLE reference.atms (
    atm_id    serial PRIMARY KEY,
    city      text NOT NULL,
    location  text NOT NULL,
    operator  text NOT NULL,
    fee_free  boolean NOT NULL   -- true: the operator charges no fee of its own
);

CREATE INDEX atms_city_idx ON reference.atms (lower(city));
