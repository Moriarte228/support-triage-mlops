-- Fictional sample values for the fictional Acme Bank. Not based on any real bank.

INSERT INTO reference.plans VALUES
    ('standard', 'Standard', 0.00),
    ('plus',     'Plus',     3.99),
    ('premium',  'Premium',  9.99);

INSERT INTO reference.supported_countries
    (country_code, name, aliases, can_open_account, card_delivery_days_min, card_delivery_days_max, cash_top_up) VALUES
    ('AT', 'Austria',     '{}',                              true, 3, 5, false),
    ('CZ', 'Czechia',     '{"czech republic"}',              true, 3, 6, true),
    ('DE', 'Germany',     '{"deutschland"}',                 true, 2, 4, false),
    ('EE', 'Estonia',     '{}',                              true, 4, 7, true),
    ('ES', 'Spain',       '{"espana"}',                      true, 4, 6, false),
    ('FR', 'France',      '{}',                              true, 3, 5, false),
    ('IE', 'Ireland',     '{}',                              true, 4, 7, false),
    ('IT', 'Italy',       '{}',                              true, 4, 7, false),
    ('LT', 'Lithuania',   '{}',                              true, 3, 6, true),
    ('LV', 'Latvia',      '{}',                              true, 4, 7, true),
    ('NL', 'Netherlands', '{"holland", "the netherlands"}',  true, 2, 4, false),
    ('PL', 'Poland',      '{"polska"}',                      true, 3, 5, true),
    ('PT', 'Portugal',    '{}',                              true, 5, 8, false);

-- Countries where customers cannot open an account but can receive transfers.
INSERT INTO reference.supported_countries (country_code, name, aliases, can_open_account) VALUES
    ('CH', 'Switzerland',    '{}',                                       false),
    ('GB', 'United Kingdom', '{"uk", "great britain", "england"}',      false),
    ('NO', 'Norway',         '{}',                                       false),
    ('US', 'United States',  '{"usa", "us", "united states of america"}', false);

INSERT INTO reference.fees (plan_id, fee_type, fixed_eur, percent, monthly_free_eur, note) VALUES
    ('standard', 'physical_card_delivery', 5.99, NULL, NULL, 'Standard post'),
    ('plus',     'physical_card_delivery', 0.00, NULL, NULL, 'Standard post'),
    ('premium',  'physical_card_delivery', 0.00, NULL, NULL, 'Standard post'),
    ('standard', 'atm_withdrawal', NULL, 2.00,  200, 'Our fee above the monthly allowance; ATM operators may add their own'),
    ('plus',     'atm_withdrawal', NULL, 2.00,  400, 'Our fee above the monthly allowance; ATM operators may add their own'),
    ('premium',  'atm_withdrawal', NULL, 2.00,  800, 'Our fee above the monthly allowance; ATM operators may add their own'),
    ('standard', 'exchange', NULL, 0.50, 1000, 'Currency exchanges and card payments in another currency share this allowance'),
    ('plus',     'exchange', NULL, 0.50, 3000, 'Currency exchanges and card payments in another currency share this allowance'),
    ('premium',  'exchange', NULL, 0.00, NULL, 'No exchange fee'),
    ('standard', 'weekend_fx_markup', NULL, 1.00, NULL, 'Added to the rate when markets are closed'),
    ('plus',     'weekend_fx_markup', NULL, 0.50, NULL, 'Added to the rate when markets are closed'),
    ('premium',  'weekend_fx_markup', NULL, 0.00, NULL, 'No weekend markup'),
    ('standard', 'international_transfer', 3.00, NULL, NULL, 'Same-currency transfers to European banks are free'),
    ('plus',     'international_transfer', 1.50, NULL, NULL, 'Same-currency transfers to European banks are free'),
    ('premium',  'international_transfer', 0.00, NULL, NULL, 'Same-currency transfers to European banks are free'),
    ('standard', 'top_up_by_card', NULL, 0.70, NULL, 'Only for cards issued outside the EEA; EEA cards are free'),
    ('plus',     'top_up_by_card', NULL, 0.70, NULL, 'Only for cards issued outside the EEA; EEA cards are free'),
    ('premium',  'top_up_by_card', NULL, 0.00, NULL, 'No fee');

INSERT INTO reference.limits (plan_id, limit_type, value, unit, note) VALUES
    ('standard', 'active_physical_cards', 2, 'cards', NULL),
    ('plus',     'active_physical_cards', 3, 'cards', NULL),
    ('premium',  'active_physical_cards', 5, 'cards', NULL),
    ('standard', 'disposable_cards_per_day', 1, 'cards', NULL),
    ('plus',     'disposable_cards_per_day', 3, 'cards', NULL),
    ('premium',  'disposable_cards_per_day', 5, 'cards', NULL),
    ('standard', 'disposable_card_max_payment', 250, 'EUR', NULL),
    ('plus',     'disposable_card_max_payment', 500, 'EUR', NULL),
    ('premium',  'disposable_card_max_payment', 1000, 'EUR', NULL),
    ('standard', 'contactless_max_payment', 50, 'EUR', NULL),
    ('plus',     'contactless_max_payment', 50, 'EUR', NULL),
    ('premium',  'contactless_max_payment', 50, 'EUR', NULL),
    ('standard', 'top_up_per_transaction', 2000, 'EUR', 'Verified customers'),
    ('plus',     'top_up_per_transaction', 5000, 'EUR', 'Verified customers'),
    ('premium',  'top_up_per_transaction', 10000, 'EUR', 'Verified customers'),
    ('standard', 'top_up_per_day', 3000, 'EUR', 'Verified customers'),
    ('plus',     'top_up_per_day', 7500, 'EUR', 'Verified customers'),
    ('premium',  'top_up_per_day', 15000, 'EUR', 'Verified customers'),
    ('standard', 'top_up_per_month', 10000, 'EUR', 'Verified customers'),
    ('plus',     'top_up_per_month', 25000, 'EUR', 'Verified customers'),
    ('premium',  'top_up_per_month', 50000, 'EUR', 'Verified customers'),
    ('standard', 'atm_withdrawal_per_day', 500, 'EUR', NULL),
    ('plus',     'atm_withdrawal_per_day', 1000, 'EUR', NULL),
    ('premium',  'atm_withdrawal_per_day', 2000, 'EUR', NULL);

INSERT INTO reference.currencies (code, name, can_hold, can_top_up) VALUES
    ('EUR', 'Euro', true, true),
    ('USD', 'US dollar', true, true),
    ('GBP', 'Pound sterling', true, true),
    ('PLN', 'Polish zloty', true, true),
    ('CZK', 'Czech koruna', true, true),
    ('CHF', 'Swiss franc', true, false),
    ('SEK', 'Swedish krona', true, false),
    ('NOK', 'Norwegian krone', true, false),
    ('DKK', 'Danish krone', true, false),
    ('HUF', 'Hungarian forint', true, false),
    ('RON', 'Romanian leu', true, false),
    ('JPY', 'Japanese yen', true, false);

-- Sample rates for development; a scheduled job will refresh this table later.
INSERT INTO reference.exchange_rates (base, quote, rate) VALUES
    ('EUR', 'USD', 1.08), ('EUR', 'GBP', 0.85), ('EUR', 'PLN', 4.30), ('EUR', 'CZK', 25.20),
    ('EUR', 'CHF', 0.94), ('EUR', 'SEK', 11.30), ('EUR', 'NOK', 11.60), ('EUR', 'DKK', 7.46),
    ('EUR', 'HUF', 395.00), ('EUR', 'RON', 4.97), ('EUR', 'JPY', 162.00);

INSERT INTO reference.atms (city, location, operator, fee_free) VALUES
    ('Warsaw',  'Central railway station, main hall', 'Acme partner network', true),
    ('Warsaw',  'Old Town, market square',            'Independent operator', false),
    ('Krakow',  'Main railway station, east exit',    'Acme partner network', true),
    ('Vilnius', 'Cathedral square',                   'Acme partner network', true),
    ('Vilnius', 'Airport, arrivals hall',             'Independent operator', false),
    ('Riga',    'Central market, pavilion 2',         'Acme partner network', true),
    ('Berlin',  'Central station, lower level',       'Acme partner network', true),
    ('Berlin',  'Airport, terminal 1',                'Independent operator', false),
    ('Prague',  'Main railway station, hall A',       'Acme partner network', true);
