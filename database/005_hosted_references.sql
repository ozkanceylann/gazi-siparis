-- Existing hosted install only. Fresh installs already use a composite key.
BEGIN;
ALTER TABLE gazi_ops.districts DROP CONSTRAINT districts_pkey;
ALTER TABLE gazi_ops.districts ADD PRIMARY KEY(city_code,code);
INSERT INTO gazi_ops.districts(code,city_code,name)
SELECT DISTINCT ON (city_id::int,code::int) code::int,city_id::int,name
FROM public.ilce WHERE code ~ '^[0-9]+$' AND city_id ~ '^[0-9]+$'
AND EXISTS(SELECT 1 FROM gazi_ops.cities WHERE cities.code=ilce.city_id::int)
ORDER BY city_id::int,code::int ON CONFLICT(city_code,code) DO UPDATE SET name=excluded.name;
COMMIT;
