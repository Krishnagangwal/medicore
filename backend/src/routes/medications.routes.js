const express = require('express');
const axios = require('axios');
const { query } = require('../lib/db');
const { authenticate, requireRole } = require('../middleware/auth');
const { emitDrugInteraction } = require('../sockets/index');
const { signServiceToken } = require('../utils/jwt');

// mergeParams so this router also works nested under
// /api/encounters/:encounterId/medications (see routes/index.js)
const router = express.Router({ mergeParams: true });
router.use(authenticate);

// GET /api/encounters/:encounterId/medications
router.get('/', async (req, res, next) => {
  try {
    const encounterId = req.params.encounterId;
    const result = await query(
      `SELECT * FROM medications WHERE "encounterId" = $1 ORDER BY "createdAt" DESC`,
      [encounterId],
    );
    return res.status(200).json({ data: result.rows });
  } catch (err) {
    return next(err);
  }
});

// POST /api/medications
router.post('/', requireRole('DOCTOR'), async (req, res, next) => {
  try {
    const { encounterId, drugName, genericName, dosage, frequency, route } = req.body;

    if (!encounterId || !drugName) {
      return res.status(400).json({
        error: 'encounterId and drugName are required',
        code: 'VALIDATION_ERROR',
        statusCode: 400,
      });
    }

    const encounterResult = await query(
      `SELECT id, "patientId" FROM encounters WHERE id = $1`,
      [encounterId],
    );
    const encounter = encounterResult.rows[0];
    if (!encounter) {
      return res.status(404).json({
        error: 'Encounter not found',
        code: 'NOT_FOUND',
        statusCode: 404,
      });
    }

    const inserted = await query(
      `INSERT INTO medications
         ("encounterId", "patientId", "prescribedBy", "drugName", "genericName", dosage, frequency, route, status)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'ACTIVE')
       RETURNING *`,
      [
        encounterId,
        encounter.patientId,
        req.user.sub,
        drugName,
        genericName || null,
        dosage || null,
        frequency || null,
        route || null,
      ],
    );
    const medication = inserted.rows[0];

    // Fire-and-forget drug interaction check — do not block the response on it.
    setImmediate(async () => {
      try {
        const allMeds = await query(
          `SELECT "drugName" FROM medications
           WHERE "encounterId" = $1 AND status = 'ACTIVE'`,
          [encounterId],
        );
        const medications = allMeds.rows.map((m) => m.drugName);
        if (medications.length < 2) return;

        const token = signServiceToken();
        const { data } = await axios.post(
          `${process.env.AI_GATEWAY_URL}/gateway/predict`,
          {
            patient_id: encounter.patientId,
            encounter_id: encounterId,
            vitals_readings: [],
            medications,
          },
          { headers: { Authorization: `Bearer ${token}` }, timeout: 10000 },
        );

        const drugResult = data?.drug_interaction?.result;
        if (!drugResult) return;

        if (drugResult.interaction_count > 0) {
          const major = drugResult.interactions.filter((i) => i.severity_code >= 3);

          if (major.length > 0) {
            emitDrugInteraction({
              encounter_id: encounterId,
              patient_id: encounter.patientId,
              interactions: major,
            });
          }
        }
      } catch (err) {
        console.error('[MedRoute] Drug check error:', err.message);
      }
    });

    return res.status(201).json({ data: medication });
  } catch (err) {
    return next(err);
  }
});

// PATCH /api/medications/:id/discontinue
router.patch('/:id/discontinue', requireRole('DOCTOR'), async (req, res, next) => {
  try {
    const result = await query(
      `UPDATE medications SET status = 'DISCONTINUED' WHERE id = $1 RETURNING *`,
      [req.params.id],
    );

    if (!result.rows[0]) {
      return res.status(404).json({
        error: 'Medication not found',
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
