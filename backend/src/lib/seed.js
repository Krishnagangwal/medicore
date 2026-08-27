require('dotenv').config();
const bcrypt = require('bcrypt');
const { pool, query } = require('./db');

const SEED_USERS = [
  { email: 'admin@medicore.local', password: 'password123', role: 'ADMIN', fullName: 'Admin User', ward: null },
  { email: 'nurse@medicore.local', password: 'password123', role: 'NURSE', fullName: 'Nurse Priya', ward: 'ICU-B' },
  { email: 'doctor@medicore.local', password: 'password123', role: 'DOCTOR', fullName: 'Dr. Rao', ward: 'ICU-B' },
];

async function seed() {
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
}

seed()
  .catch((err) => {
    console.error('Seeding failed:', err);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
