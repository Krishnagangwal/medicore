const express = require('express');
const { query } = require('../lib/db');
const { authenticate } = require('../middleware/auth');

const router = express.Router();
router.use(authenticate);

// GET /api/notifications
router.get('/', async (req, res, next) => {
  try {
    const result = await query(
      `SELECT * FROM notifications
       WHERE "recipientId" = $1
       ORDER BY "createdAt" DESC
       LIMIT 50`,
      [req.user.sub],
    );

    const unreadResult = await query(
      `SELECT COUNT(*)::int as count FROM notifications
       WHERE "recipientId" = $1 AND "isRead" = false`,
      [req.user.sub],
    );

    return res.status(200).json({
      data: result.rows,
      unreadCount: unreadResult.rows[0].count,
    });
  } catch (err) {
    return next(err);
  }
});

// PATCH /api/notifications/:id/read
router.patch('/:id/read', async (req, res, next) => {
  try {
    const result = await query(
      `UPDATE notifications SET "isRead" = true, "readAt" = NOW()
       WHERE id = $1 AND "recipientId" = $2
       RETURNING *`,
      [req.params.id, req.user.sub],
    );

    if (!result.rows[0]) {
      return res.status(404).json({
        error: 'Notification not found',
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
