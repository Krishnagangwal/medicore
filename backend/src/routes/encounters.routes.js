const express = require('express');
const { authenticate } = require('../middleware/auth');

const router = express.Router();
router.use(authenticate);

// GET /api/encounters
router.get('/', async (req, res) => {
  res.status(200).json({ message: 'TODO: list encounters', data: [] });
});

// GET /api/encounters/:id
router.get('/:id', async (req, res) => {
  res.status(200).json({ message: `TODO: fetch encounter ${req.params.id}`, data: null });
});

// POST /api/encounters
router.post('/', async (req, res) => {
  res.status(200).json({ message: 'TODO: admit patient / create encounter', data: null });
});

// PATCH /api/encounters/:id/discharge
router.patch('/:id/discharge', async (req, res) => {
  res.status(200).json({ message: `TODO: discharge encounter ${req.params.id}`, data: null });
});

module.exports = router;
