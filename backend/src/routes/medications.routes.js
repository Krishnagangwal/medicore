const express = require('express');
const { authenticate } = require('../middleware/auth');

const router = express.Router();
router.use(authenticate);

// GET /api/medications/encounter/:encounterId
router.get('/encounter/:encounterId', async (req, res) => {
  res.status(200).json({ message: `TODO: list medications for encounter ${req.params.encounterId}`, data: [] });
});

// POST /api/medications
// Next session: persist prescription, call the drug-interaction model via
// the AI Gateway, and emit `drug:interaction` on the /doctor namespace if a
// major interaction is flagged.
router.post('/', async (req, res) => {
  res.status(200).json({ message: 'TODO: prescribe medication', data: null });
});

// PATCH /api/medications/:id/discontinue
router.patch('/:id/discontinue', async (req, res) => {
  res.status(200).json({ message: `TODO: discontinue medication ${req.params.id}`, data: null });
});

module.exports = router;
