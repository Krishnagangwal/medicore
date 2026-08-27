-- MediCore backend schema (plain PostgreSQL, no ORM)
-- Mirrors the field-for-field contract originally specified as a Prisma schema.
-- Apply with: npm run db:migrate

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN
  CREATE TYPE role AS ENUM ('NURSE', 'DOCTOR', 'ADMIN');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE encounter_status AS ENUM ('ACTIVE', 'DISCHARGED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE med_status AS ENUM ('ACTIVE', 'DISCONTINUED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE notif_severity AS ENUM ('INFO', 'WARNING', 'CRITICAL');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW."updatedAt" = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ─────────────────────────────────────────────────────────────────────────
-- users
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT NOT NULL UNIQUE,
  "passwordHash" TEXT NOT NULL,
  role          role NOT NULL,
  "fullName"    TEXT NOT NULL,
  ward          TEXT,
  "isActive"    BOOLEAN NOT NULL DEFAULT true,
  "lastLogin"   TIMESTAMPTZ,
  "createdAt"   TIMESTAMPTZ NOT NULL DEFAULT now(),
  "updatedAt"   TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─────────────────────────────────────────────────────────────────────────
-- patients
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patients (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "patientCode"       TEXT NOT NULL UNIQUE,
  "fullName"          TEXT NOT NULL,
  dob                 TIMESTAMPTZ NOT NULL,
  gender              TEXT NOT NULL,
  "bloodType"         TEXT,
  "contactPhone"      TEXT,
  "chronicConditions" TEXT[] NOT NULL DEFAULT '{}',
  allergies           JSONB NOT NULL DEFAULT '[]',
  "createdAt"         TIMESTAMPTZ NOT NULL DEFAULT now(),
  "updatedAt"         TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_patients_updated_at ON patients;
CREATE TRIGGER trg_patients_updated_at BEFORE UPDATE ON patients
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─────────────────────────────────────────────────────────────────────────
-- encounters
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS encounters (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "patientId"        UUID NOT NULL REFERENCES patients(id),
  status             encounter_status NOT NULL DEFAULT 'ACTIVE',
  "admittedAt"       TIMESTAMPTZ NOT NULL DEFAULT now(),
  "dischargedAt"     TIMESTAMPTZ,
  ward               TEXT,
  "bedId"            TEXT,
  "treatingDoctorId" UUID REFERENCES users(id),
  "createdAt"        TIMESTAMPTZ NOT NULL DEFAULT now(),
  "updatedAt"        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_encounters_patient ON encounters ("patientId");
CREATE INDEX IF NOT EXISTS idx_encounters_status_admitted ON encounters (status, "admittedAt" DESC);

DROP TRIGGER IF EXISTS trg_encounters_updated_at ON encounters;
CREATE TRIGGER trg_encounters_updated_at BEFORE UPDATE ON encounters
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─────────────────────────────────────────────────────────────────────────
-- vitals
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vitals (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "encounterId"     UUID NOT NULL REFERENCES encounters(id),
  "patientId"       UUID NOT NULL REFERENCES patients(id),
  "recordedBy"      UUID NOT NULL REFERENCES users(id),
  "recordedAt"      TIMESTAMPTZ NOT NULL DEFAULT now(),
  "heartRate"       DOUBLE PRECISION,
  "systolicBp"      DOUBLE PRECISION,
  "diastolicBp"     DOUBLE PRECISION,
  temperature       DOUBLE PRECISION,
  "respiratoryRate" DOUBLE PRECISION,
  spo2              DOUBLE PRECISION,
  map               DOUBLE PRECISION,
  notes             TEXT
);

CREATE INDEX IF NOT EXISTS idx_vitals_encounter_recorded ON vitals ("encounterId", "recordedAt" DESC);

-- ─────────────────────────────────────────────────────────────────────────
-- medications
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS medications (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "encounterId"  UUID NOT NULL REFERENCES encounters(id),
  "patientId"    UUID NOT NULL REFERENCES patients(id),
  "prescribedBy" UUID NOT NULL REFERENCES users(id),
  "drugName"     TEXT NOT NULL,
  "genericName"  TEXT,
  dosage         TEXT,
  frequency      TEXT,
  route          TEXT,
  status         med_status NOT NULL DEFAULT 'ACTIVE',
  "createdAt"    TIMESTAMPTZ NOT NULL DEFAULT now(),
  "updatedAt"    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_medications_encounter_status ON medications ("encounterId", status);

DROP TRIGGER IF EXISTS trg_medications_updated_at ON medications;
CREATE TRIGGER trg_medications_updated_at BEFORE UPDATE ON medications
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─────────────────────────────────────────────────────────────────────────
-- predictions
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predictions (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "encounterId"    UUID NOT NULL REFERENCES encounters(id),
  "patientId"      UUID NOT NULL REFERENCES patients(id),
  "modelType"      TEXT NOT NULL,
  "predictedAt"    TIMESTAMPTZ NOT NULL DEFAULT now(),
  result           JSONB NOT NULL,
  "alertTriggered" BOOLEAN NOT NULL DEFAULT false,
  "latencyMs"      INTEGER,
  "createdAt"      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_predictions_encounter_model_predicted
  ON predictions ("encounterId", "modelType", "predictedAt" DESC);

-- Sessions 2+: nightly cron deletes predictions older than 90 days (see CLAUDE.md).

-- ─────────────────────────────────────────────────────────────────────────
-- notifications
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "recipientId" UUID NOT NULL REFERENCES users(id),
  type          TEXT NOT NULL,
  title         TEXT NOT NULL,
  body          TEXT NOT NULL,
  "patientId"   UUID REFERENCES patients(id),
  "encounterId" UUID,
  severity      notif_severity NOT NULL DEFAULT 'INFO',
  "isRead"      BOOLEAN NOT NULL DEFAULT false,
  "readAt"      TIMESTAMPTZ,
  "createdAt"   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_recipient_read_created
  ON notifications ("recipientId", "isRead", "createdAt" DESC);

-- Sessions 2+: nightly cron deletes notifications older than 30 days (see CLAUDE.md).
