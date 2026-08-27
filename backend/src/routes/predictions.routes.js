const express = require('express');
const { authenticate } = require('../middleware/auth');

const router = express.Router();
router.use(authenticate);

// GET /api/predictions/encounter/:encounterId
router.get('/encounter/:encounterId', async (req, res) => {
  res.status(200).json({ message: `TODO: list predictions for encounter ${req.params.encounterId}`, data: [] });
});

// GET /api/predictions/encounter/:encounterId/latest
router.get('/encounter/:encounterId/latest', async (req, res) => {
  res.status(200).json({ message: `TODO: fetch latest prediction for encounter ${req.params.encounterId}`, data: null });
});

module.exports = router;
