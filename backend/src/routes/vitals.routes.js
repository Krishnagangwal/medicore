const express = require('express');
const { authenticate } = require('../middleware/auth');

const router = express.Router();
router.use(authenticate);

// GET /api/vitals/encounter/:encounterId
router.get('/encounter/:encounterId', async (req, res) => {
  res.status(200).json({ message: `TODO: list vitals for encounter ${req.params.encounterId}`, data: [] });
});

// POST /api/vitals
// Next session: persist to DB, then emit `vitals:logged` on the /nurse
// namespace (see src/sockets/index.js) so the nurse station updates live.
router.post('/', async (req, res) => {
  res.status(200).json({ message: 'TODO: log vitals', data: null });
});

module.exports = router;
