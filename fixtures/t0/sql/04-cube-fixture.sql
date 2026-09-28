-- The upstream the Cube model reads (Phase 6, WP-6.2).
--
-- Deliberately small and deliberately NOT the crm fixture: the point of this
-- tier is the seam between Matrix and a semantic layer that owns its own
-- metric definitions, and reusing `crm.opportunities` would tangle it with
-- the mode-B/C fixtures whose traps mean something else. Three statuses, two
-- regions, and one decimal whose trailing zero is the property that must
-- survive the JSON round trip.
--
-- Cube reads it as the `matrix` role (compose's CUBEJS_DB_USER), so the grant
-- is explicit rather than inherited.

CREATE SCHEMA IF NOT EXISTS cube_fixture;

CREATE TABLE IF NOT EXISTS cube_fixture.orders (
    id      BIGINT PRIMARY KEY,
    status  TEXT           NOT NULL,
    region  TEXT           NOT NULL,
    amount  NUMERIC(18, 2) NOT NULL
);

TRUNCATE cube_fixture.orders;
INSERT INTO cube_fixture.orders (id, status, region, amount) VALUES
    (1, 'new',      'EMEA', 1500000.00),
    (2, 'shipped',  'EMEA',  250000.50),
    (3, 'shipped',  'EMEA',  900000.50),
    (4, 'returned', 'AMER',  120000.00);

GRANT USAGE ON SCHEMA cube_fixture TO matrix;
GRANT SELECT ON ALL TABLES IN SCHEMA cube_fixture TO matrix;
