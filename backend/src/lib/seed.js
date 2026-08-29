require('dotenv').config();
const bcrypt = require('bcrypt');
const { pool, query } = require('./db');

const HOSPITAL_ID = 'a1b2c3d4-0000-0000-0000-000000000001';

const SEED_HOSPITAL = {
  id: HOSPITAL_ID,
  name: 'TCET Memorial Hospital',
  adminEmail: 'admin@tcet.hospital',
  adminName: 'Hospital Admin',
};

// `upsertHospitalId: true` mirrors the spec's `ON CONFLICT (email) DO
// UPDATE SET "hospitalId" = EXCLUDED."hospitalId"` for nurse/doctor, so
// existing pre-multi-hospital rows get linked to the demo hospital on a
// re-run. Super admin / hospital admin use `DO NOTHING`, per spec — a
// fresh install creates them once; already-existing accounts are left
// exactly as they are.
const SEED_USERS = [
  {
    email: 'superadmin@medicore.platform',
    password: 'SuperAdmin123!',
    role: 'SUPER_ADMIN',
    fullName: 'Super Admin',
    ward: null,
    hospitalId: null,
    upsertHospitalId: false,
  },
  {
    email: SEED_HOSPITAL.adminEmail,
    password: 'Admin123!',
    role: 'ADMIN',
    fullName: SEED_HOSPITAL.adminName,
    ward: null,
    hospitalId: HOSPITAL_ID,
    upsertHospitalId: false,
  },
  {
    email: 'nurse@medicore.local',
    password: 'password123',
    role: 'NURSE',
    fullName: 'Nurse Priya',
    ward: 'ICU-B',
    hospitalId: HOSPITAL_ID,
    upsertHospitalId: true,
  },
  {
    email: 'doctor@medicore.local',
    password: 'password123',
    role: 'DOCTOR',
    // NOTE: this only takes effect if the row doesn't already exist. This
    // DB already has doctor@medicore.local seeded as "Dr. Rao" from before
    // multi-hospital support existed, and the spec's ON CONFLICT clause
    // for this user only updates "hospitalId" (not fullName) — so an
    // already-existing row stays "Dr. Rao", not "Dr. Arjun Sharma".
    // Implemented literally as specified; say the word if you actually
    // want the rename applied too.
    fullName: 'Dr. Arjun Sharma',
    ward: 'ICU-B',
    hospitalId: HOSPITAL_ID,
    upsertHospitalId: true,
  },
];

const SEED_PATIENTS = [
  {
    patientCode: 'MED-SEED01',
    fullName: 'Mrs. Priya Sharma',
    dob: '1961-03-15',
    gender: 'female',
    bloodType: 'O+',
    chronicConditions: ['Hypertension', 'Type 2 Diabetes'],
  },
  {
    patientCode: 'MED-SEED02',
    fullName: 'Mr. Raj Mehta',
    dob: '1974-07-22',
    gender: 'male',
    bloodType: 'A+',
    chronicConditions: ['COPD'],
  },
];

// Hour-by-hour, simulating deterioration toward sepsis.
const SEED_VITALS = [
  { hr: 85, sbp: 118, temp: 37.2, spo2: 97, resp: 16 },
  { hr: 90, sbp: 112, temp: 37.5, spo2: 96, resp: 17 },
  { hr: 98, sbp: 104, temp: 37.9, spo2: 95, resp: 19 },
  { hr: 106, sbp: 96, temp: 38.3, spo2: 93, resp: 22 },
  { hr: 112, sbp: 90, temp: 38.6, spo2: 92, resp: 24 },
  { hr: 118, sbp: 86, temp: 38.9, spo2: 91, resp: 26 },
];

const SEED_MEDICATIONS = ['Vancomycin', 'Piperacillin-Tazobactam'];

async function seedHospital() {
  await query(
    `INSERT INTO hospitals (id, name, "adminEmail", "adminName", status, "approvedAt")
     VALUES ($1, $2, $3, $4, 'approved', NOW())
     ON CONFLICT ("adminEmail") DO NOTHING`,
    [SEED_HOSPITAL.id, SEED_HOSPITAL.name, SEED_HOSPITAL.adminEmail, SEED_HOSPITAL.adminName],
  );
  console.log(`Seeded hospital: ${SEED_HOSPITAL.name} (approved)`);
}

async function seedUsers() {
  for (const user of SEED_USERS) {
    const passwordHash = await bcrypt.hash(user.password, 10);
    const conflictClause = user.upsertHospitalId
      ? 'ON CONFLICT (email) DO UPDATE SET "hospitalId" = EXCLUDED."hospitalId"'
      : 'ON CONFLICT (email) DO NOTHING';
    await query(
      `INSERT INTO users (email, "passwordHash", role, "fullName", ward, "hospitalId")
       VALUES ($1, $2, $3, $4, $5, $6)
       ${conflictClause}`,
      [user.email, passwordHash, user.role, user.fullName, user.ward, user.hospitalId],
    );
    console.log(`Seeded ${user.role}: ${user.email} / ${user.password}`);
  }

  const result = await query('SELECT id, email, role FROM users WHERE email = ANY($1)', [
    SEED_USERS.map((u) => u.email),
  ]);
  const byRole = {};
  result.rows.forEach((row) => {
    byRole[row.role] = row.id;
  });
  return byRole;
}

async function ensurePatientsHospitalColumn() {
  // Scoped to this task ("email service + updated seed data" only, no
  // schema.sql edit) — added here defensively so `node src/lib/seed.js`
  // works standalone. Same idempotent ADD COLUMN pattern as schema.sql.
  await query(`ALTER TABLE patients ADD COLUMN IF NOT EXISTS "hospitalId" UUID REFERENCES hospitals(id)`);
}

async function seedPatients() {
  await ensurePatientsHospitalColumn();

  for (const patient of SEED_PATIENTS) {
    await query(
      `INSERT INTO patients ("patientCode", "fullName", dob, gender, "bloodType", "chronicConditions", "hospitalId")
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       ON CONFLICT ("patientCode") DO UPDATE SET "hospitalId" = EXCLUDED."hospitalId"`,
      [
        patient.patientCode,
        patient.fullName,
        patient.dob,
        patient.gender,
        patient.bloodType,
        patient.chronicConditions,
        HOSPITAL_ID,
      ],
    );
  }

  const result = await query('SELECT id, "patientCode", "fullName" FROM patients WHERE "patientCode" = ANY($1)', [
    SEED_PATIENTS.map((p) => p.patientCode),
  ]);
  const byCode = {};
  result.rows.forEach((row) => {
    byCode[row.patientCode] = row;
  });
  return byCode;
}

async function seedEncounter(priyaPatientId, doctorId) {
  const existing = await query(
    `SELECT id FROM encounters WHERE "patientId" = $1 AND status = 'ACTIVE'`,
    [priyaPatientId],
  );
  if (existing.rows[0]) {
    console.log(`Active encounter already exists for Priya Sharma: ${existing.rows[0].id}`);
    return existing.rows[0].id;
  }

  const result = await query(
    `INSERT INTO encounters ("patientId", status, ward, "bedId", "treatingDoctorId")
     VALUES ($1, 'ACTIVE', 'ICU-B', 'B4', $2)
     RETURNING id`,
    [priyaPatientId, doctorId],
  );
  console.log(`Created active encounter for Priya Sharma: ${result.rows[0].id}`);
  return result.rows[0].id;
}

async function seedVitals(encounterId, patientId, nurseId) {
  const existing = await query('SELECT COUNT(*)::int as count FROM vitals WHERE "encounterId" = $1', [encounterId]);
  if (existing.rows[0].count > 0) {
    console.log(`Vitals already seeded for encounter ${encounterId} (${existing.rows[0].count} rows)`);
    return existing.rows[0].count;
  }

  const hoursAgo = SEED_VITALS.length;
  for (let i = 0; i < SEED_VITALS.length; i += 1) {
    const v = SEED_VITALS[i];
    const recordedAt = new Date(Date.now() - (hoursAgo - i) * 60 * 60 * 1000);
    await query(
      `INSERT INTO vitals
         ("encounterId", "patientId", "recordedBy", "recordedAt", "heartRate", "systolicBp", temperature, spo2, "respiratoryRate")
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
      [encounterId, patientId, nurseId, recordedAt, v.hr, v.sbp, v.temp, v.spo2, v.resp],
    );
  }
  console.log(`Seeded ${SEED_VITALS.length} vitals readings for encounter ${encounterId}`);
  return SEED_VITALS.length;
}

async function seedMedications(encounterId, patientId, doctorId) {
  let count = 0;
  for (const drugName of SEED_MEDICATIONS) {
    const existing = await query(
      `SELECT id FROM medications WHERE "encounterId" = $1 AND "drugName" = $2`,
      [encounterId, drugName],
    );
    if (existing.rows[0]) continue;

    await query(
      `INSERT INTO medications ("encounterId", "patientId", "prescribedBy", "drugName", route, status)
       VALUES ($1, $2, $3, $4, 'IV', 'ACTIVE')`,
      [encounterId, patientId, doctorId, drugName],
    );
    count += 1;
  }
  console.log(`Seeded ${count} medication(s) for encounter ${encounterId}`);
  return count;
}

async function seed() {
  await seedHospital();
  const users = await seedUsers();
  const patients = await seedPatients();

  const priya = patients['MED-SEED01'];
  const encounterId = await seedEncounter(priya.id, users.DOCTOR);
  const vitalsCount = await seedVitals(encounterId, priya.id, users.NURSE);
  const medsCount = await seedMedications(encounterId, priya.id, users.DOCTOR);

  console.log('\nSeed complete:');
  console.log(`  Super admin: superadmin@medicore.platform / SuperAdmin123!`);
  console.log(`  Hospital: ${SEED_HOSPITAL.name} (approved)`);
  console.log(`  Hospital admin: ${SEED_HOSPITAL.adminEmail} / Admin123!`);
  console.log(`  Nurse: nurse@medicore.local / password123`);
  console.log(`  Doctor: doctor@medicore.local / password123`);
  console.log(
    `  Demo patients: ${SEED_PATIENTS.length} | Encounters: 1 | Vitals: ${vitalsCount} | Medications: ${medsCount}`,
  );
}

seed()
  .catch((err) => {
    console.error('Seeding failed:', err);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
