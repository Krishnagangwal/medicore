const express = require('express');
const { authenticate } = require('../middleware/auth');

const router = express.Router();
router.use(authenticate);

// GET /api/notifications
router.get('/', async (req, res) => {
  res.status(200).json({ message: 'TODO: list notifications for current user', data: [] });
});

// PATCH /api/notifications/:id/read
router.patch('/:id/read', async (req, res) => {
  res.status(200).json({ message: `TODO: mark notification ${req.params.id} read`, data: null });
});

module.exports = router;
