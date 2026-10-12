BEGIN;
ALTER TABLE gazi_live.shipments ADD COLUMN reference_verified boolean NOT NULL DEFAULT false;
UPDATE gazi_live.shipments SET state_at=NULL WHERE NOT EXISTS(SELECT 1 FROM gazi_live.events e WHERE e.order_id=shipments.order_id AND event_key LIKE 'carrier:%');
COMMIT;
