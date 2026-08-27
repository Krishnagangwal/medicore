const express = require('express');
const { query } = require('../lib/db');
const { authenticate, requireRole } = require('../middleware/auth');

const router = express.Router();
router.use(authenticate);

const UPDATABLE_FIELDS = [
  'fullName',
  'dob',
  'gender',
  'bloodType',
  'contactPhone',
  'chronicConditions',
  'allergies',
];

// GET /api/patients
router.get('/', requireRole('NURSE', 'DOCTOR', 'ADMIN'), async (req, res, next) => {
  try {
    const result = await query('SELECT * FROM patients ORDER BY "fullName" ASC');
    return res.status(200).json({ data: result.rows });
  } catch (err) {
    return next(err);
  }
});

// GET /api/patients/:id
router.get('/:id', async (req, res, next) => {
  try {
    const result = await query(
      `SELECT p.*,
         e.id as encounter_id, e.status, e."admittedAt",
         e.ward, e."bedId", e."treatingDoctorId"
       FROM patients p
       LEFT JOIN encounters e ON e."patientId" = p.id
         AND e.status = 'ACTIVE'
       WHERE p.id = $1`,
      [req.params.id],
    );
    const row = result.rows[0];

    if (!row) {
      return res.status(404).json({
        error: 'Patient not found',
        code: 'NOT_FOUND',
        statusCode: 404,
      });
    }

    const {
      encounter_id: encounterId,
      status,
      admittedAt,
      ward,
      bedId,
      treatingDoctorId,
      ...patient
    } = row;

    patient.activeEncounter = encounterId
      ? { id: encounterId, status, admittedAt, ward, bedId, treatingDoctorId }
      : null;

    return res.status(200).json({ data: patient });
  } catch (err) {
    return next(err);
  }
});

// POST /api/patients
router.post('/', requireRole('NURSE', 'ADMIN'), async (req, res, next) => {
  try {
    const {
      fullName,
      dob,
      gender,
      bloodType,
      contactPhone,
      chronicConditions,
      allergies,
    } = req.body;

    if (!fullName || !dob || !gender) {
      return res.status(400).json({
        error: 'fullName, dob, and gender are required',
        code: 'VALIDATION_ERROR',
        statusCode: 400,
      });
    }

    const patientCode = `MED-${Date.now().toString().slice(-6)}`;

    const result = await query(
      `INSERT INTO patients
         ("patientCode", "fullName", dob, gender, "bloodType", "contactPhone", "chronicConditions", allergies)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       RETURNING *`,
      [
        patientCode,
        fullName,
        dob,
        gender,
        bloodType || null,
        contactPhone || null,
        chronicConditions || [],
        JSON.stringify(allergies || []),
      ],
    );

    return res.status(201).json({ data: result.rows[0] });
  } catch (err) {
    return next(err);
  }
});

// PATCH /api/patients/:id
router.patch('/:id', requireRole('NURSE', 'ADMIN'), async (req, res, next) => {
  try {
    const fields = Object.keys(req.body).filter((key) => UPDATABLE_FIELDS.includes(key));

    if (fields.length === 0) {
      return res.status(400).json({
        error: 'No updatable fields provided',
        code: 'VALIDATION_ERROR',
        statusCode: 400,
      });
    }

    const setClause = fields.map((field, idx) => `"${field}" = $${idx + 1}`).join(', ');
    const values = fields.map((field) =>
      field === 'allergies' ? JSON.stringify(req.body[field]) : req.body[field],
    );

    const result = await query(
      `UPDATE patients SET ${setClause} WHERE id = $${fields.length + 1} RETURNING *`,
      [...values, req.params.id],
    );

    if (!result.rows[0]) {
      return res.status(404).json({
        error: 'Patient not found',
        code: 'NOT_FOUND',
        statusCode: 404,
      });
    }

    return res.status(200).json({ data: result.rows[0] });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
