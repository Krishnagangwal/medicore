require('dotenv').config();
const bcrypt = require('bcrypt');
const { pool, query } = require('./db');

const SEED_USERS = [
  { email: 'admin@medicore.local', password: 'password123', role: 'ADMIN', fullName: 'Admin User', ward: null },
  { email: 'nurse@medicore.local', password: 'password123', role: 'NURSE', fullName: 'Nurse Priya', ward: 'ICU-B' },
  { email: 'doctor@medicore.local', password: 'password123', role: 'DOCTOR', fullName: 'Dr. Rao', ward: 'ICU-B' },
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

async function seedUsers() {
  for (const user of SEED_USERS) {
    const passwordHash = await bcrypt.hash(user.password, 10);
    await query(
      `INSERT INTO users (email, "passwordHash", role, "fullName", ward)
       VALUES ($1, $2, $3, $4, $5)
       ON CONFLICT (email) DO NOTHING`,
      [user.email, passwordHash, user.role, user.fullName, user.ward],
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

async function seedPatients() {
  for (const patient of SEED_PATIENTS) {
    await query(
      `INSERT INTO patients ("patientCode", "fullName", dob, gender, "bloodType", "chronicConditions")
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT ("patientCode") DO NOTHING`,
      [patient.patientCode, patient.fullName, patient.dob, patient.gender, patient.bloodType, patient.chronicConditions],
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
    return 0;
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
  const users = await seedUsers();
  const patients = await seedPatients();

  const priya = patients['MED-SEED01'];
  const encounterId = await seedEncounter(priya.id, users.DOCTOR);
  const vitalsCount = await seedVitals(encounterId, priya.id, users.NURSE);
  const medsCount = await seedMedications(encounterId, priya.id, users.DOCTOR);

  console.log('Seed complete', {
    users: SEED_USERS.length,
    patients: SEED_PATIENTS.length,
    encounters: 1,
    vitals: vitalsCount,
    medications: medsCount,
  });
}

seed()
  .catch((err) => {
    console.error('Seeding failed:', err);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
