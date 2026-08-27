const express = require('express');
const { query } = require('../lib/db');
const { authenticate } = require('../middleware/auth');

// mergeParams — mounted at /api/encounters/:encounterId/predictions (see routes/index.js)
const router = express.Router({ mergeParams: true });
router.use(authenticate);

// GET /api/encounters/:encounterId/predictions
router.get('/', async (req, res, next) => {
  try {
    const encounterId = req.params.encounterId;
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
