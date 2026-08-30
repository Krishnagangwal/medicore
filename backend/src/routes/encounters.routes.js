const express = require('express');
const { query } = require('../lib/db');
const { authenticate, requireRole } = require('../middleware/auth');

const router = express.Router();
router.use(authenticate);

// Duplicated in each route file that needs it, per this session's task —
// verifies an encounter belongs to a hospital before any encounter-scoped
// read/write. Pass hospitalId=null (SUPER_ADMIN) to bypass entirely.
async function verifyHospitalOwnership(encounterId, hospitalId) {
  if (!hospitalId) return true;
  const result = await query(
    `SELECT e.id FROM encounters e
     JOIN patients p ON p.id = e."patientId"
     WHERE e.id = $1 AND p."hospitalId" = $2`,
    [encounterId, hospitalId],
  );
  return result.rows.length > 0;
}

// GET /api/encounters
router.get('/', async (req, res, next) => {
  try {
    const isSuperAdmin = req.user.role === 'SUPER_ADMIN';
    const params = isSuperAdmin ? [] : [req.user.hospitalId];
    const result = await query(
      `SELECT e.*, p."fullName" as "patientName", p."patientCode"
       FROM encounters e
       JOIN patients p ON p.id = e."patientId"
       WHERE e.status = 'ACTIVE' ${isSuperAdmin ? '' : 'AND p."hospitalId" = $1'}
       ORDER BY e."admittedAt" DESC`,
      params,
    );
    return res.status(200).json({ data: result.rows });
  } catch (err) {
    return next(err);
  }
});

// GET /api/encounters/:id
router.get('/:id', async (req, res, next) => {
  try {
    const owns = await verifyHospitalOwnership(
      req.params.id,
      req.user.role === 'SUPER_ADMIN' ? null : req.user.hospitalId,
    );
    if (!owns) {
      return res.status(403).json({ error: 'Access denied', code: 'HOSPITAL_SCOPE_VIOLATION' });
    }

    const encounterResult = await query(
      `SELECT e.*, p."fullName", p."patientCode", p.gender,
              p."bloodType", p."chronicConditions", p.allergies
       FROM encounters e
       JOIN patients p ON p.id = e."patientId"
       WHERE e.id = $1`,
      [req.params.id],
    );
    const row = encounterResult.rows[0];

    if (!row) {
      return res.status(404).json({
        error: 'Encounter not found',
        code: 'NOT_FOUND',
        statusCode: 404,
      });
    }

    const vitalsResult = await query(
      `SELECT * FROM vitals WHERE "encounterId" = $1 ORDER BY "recordedAt" DESC LIMIT 5`,
      [req.params.id],
    );

    const {
      fullName,
      patientCode,
      gender,
      bloodType,
      chronicConditions,
      allergies,
      ...encounter
    } = row;

    encounter.patient = { fullName, patientCode, gender, bloodType, chronicConditions, allergies };
    encounter.recentVitals = vitalsResult.rows;

    return res.status(200).json({ data: encounter });
  } catch (err) {
    return next(err);
  }
});

// POST /api/encounters
router.post('/', requireRole('NURSE', 'DOCTOR', 'ADMIN'), async (req, res, next) => {
  try {
    const { patientId, ward, bedId, treatingDoctorId } = req.body;

    if (!patientId) {
      return res.status(400).json({
        error: 'patientId is required',
        code: 'VALIDATION_ERROR',
        statusCode: 400,
      });
    }

    // POST is NURSE/DOCTOR/ADMIN only (never SUPER_ADMIN), so
    // req.user.hospitalId is always a real hospital — this doubles as the
    // "patientId belongs to hospital" check: a patient from another
    // hospital just won't match, and comes back as the same 404 as a
    // genuinely nonexistent patientId (no need to distinguish the two).
    const patientResult = await query(
      'SELECT id FROM patients WHERE id = $1 AND "hospitalId" = $2',
      [patientId, req.user.hospitalId],
    );
    if (!patientResult.rows[0]) {
      return res.status(404).json({
        error: 'Patient not found',
        code: 'NOT_FOUND',
        statusCode: 404,
      });
    }

    const activeResult = await query(
      `SELECT id FROM encounters WHERE "patientId" = $1 AND status = 'ACTIVE'`,
      [patientId],
    );
    if (activeResult.rows[0]) {
      return res.status(409).json({
        error: 'Patient already has active encounter',
        code: 'CONFLICT',
        statusCode: 409,
      });
    }

    const result = await query(
      `INSERT INTO encounters ("patientId", status, ward, "bedId", "treatingDoctorId")
       VALUES ($1, 'ACTIVE', $2, $3, $4)
       RETURNING *`,
      [patientId, ward || null, bedId || null, treatingDoctorId || null],
    );

    return res.status(201).json({ data: result.rows[0] });
  } catch (err) {
    return next(err);
  }
});

// PATCH /api/encounters/:id/discharge
router.patch('/:id/discharge', requireRole('DOCTOR', 'ADMIN'), async (req, res, next) => {
  try {
    const owns = await verifyHospitalOwnership(req.params.id, req.user.hospitalId);
    if (!owns) {
      return res.status(403).json({ error: 'Access denied', code: 'HOSPITAL_SCOPE_VIOLATION' });
    }

    const result = await query(
      `UPDATE encounters SET status = 'DISCHARGED', "dischargedAt" = NOW()
       WHERE id = $1
       RETURNING *`,
      [req.params.id],
    );

    if (!result.rows[0]) {
      return res.status(404).json({
        error: 'Encounter not found',
        code: 'NOT_FOUND',
        statusCode: 404,
      });
    }

    return res.status(200).json({ data: result.rows[0], message: 'Patient discharged' });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
