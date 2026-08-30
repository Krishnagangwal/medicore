const express = require('express');
const { query } = require('../lib/db');
const { authenticate } = require('../middleware/auth');

// mergeParams — mounted at /api/encounters/:encounterId/predictions (see routes/index.js)
const router = express.Router({ mergeParams: true });
router.use(authenticate);

// Duplicated in each route file that needs it, per this session's task.
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

// GET /api/encounters/:encounterId/predictions
router.get('/', async (req, res, next) => {
  try {
    const encounterId = req.params.encounterId;
    const owns = await verifyHospitalOwnership(
      encounterId,
      req.user.role === 'SUPER_ADMIN' ? null : req.user.hospitalId,
    );
    if (!owns) {
      return res.status(403).json({ error: 'Access denied', code: 'HOSPITAL_SCOPE_VIOLATION' });
    }

    const result = await query(
      `SELECT * FROM predictions WHERE "encounterId" = $1 ORDER BY "predictedAt" DESC`,
      [encounterId],
    );
    return res.status(200).json({ data: result.rows });
  } catch (err) {
    return next(err);
  }
});

// GET /api/encounters/:encounterId/predictions/latest
router.get('/latest', async (req, res, next) => {
  try {
    const encounterId = req.params.encounterId;
    const owns = await verifyHospitalOwnership(
      encounterId,
      req.user.role === 'SUPER_ADMIN' ? null : req.user.hospitalId,
    );
    if (!owns) {
      return res.status(403).json({ error: 'Access denied', code: 'HOSPITAL_SCOPE_VIOLATION' });
    }

    const result = await query(
      `SELECT * FROM predictions
       WHERE "encounterId" = $1
       ORDER BY "predictedAt" DESC
       LIMIT 1`,
      [encounterId],
    );
    return res.status(200).json({ data: result.rows[0] || null });
  } catch (err) {
    return next(err);
  }
});

module.exports = router;
