const express = require('express');
const { authenticate } = require('../middleware/auth');

const router = express.Router();
router.use(authenticate);

// GET /api/patients
router.get('/', async (req, res) => {
  res.status(200).json({ message: 'TODO: list patients', data: [] });
});

// GET /api/patients/:id
router.get('/:id', async (req, res) => {
  res.status(200).json({ message: `TODO: fetch patient ${req.params.id}`, data: null });
});

// POST /api/patients
router.post('/', async (req, res) => {
  res.status(200).json({ message: 'TODO: create patient', data: null });
});

// PATCH /api/patients/:id
router.patch('/:id', async (req, res) => {
  res.status(200).json({ message: `TODO: update patient ${req.params.id}`, data: null });
});

module.exports = router;
