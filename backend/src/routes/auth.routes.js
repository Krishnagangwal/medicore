const express = require('express');
const bcrypt = require('bcrypt');
const { query } = require('../lib/db');
const { signAccessToken, signRefreshToken, verifyToken } = require('../utils/jwt');
const { authenticate } = require('../middleware/auth');

const router = express.Router();

const REFRESH_COOKIE_NAME = 'refreshToken';
const REFRESH_COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax',
  maxAge: 7 * 24 * 60 * 60 * 1000,
  path: '/api/auth',
};

const VALID_ROLES = ['NURSE', 'DOCTOR', 'ADMIN'];

// POST /api/auth/register
// Scaffold note: open for now so seeding/dev works end-to-end. A future
// session should gate this behind ADMIN auth once the admin portal exists.
router.post('/register', async (req, res) => {
  try {
    const { email, password, role, fullName, ward } = req.body;

    if (!email || !password || !role || !fullName) {
      return res.status(400).json({
        error: 'email, password, role, and fullName are required',
        code: 'VALIDATION_ERROR',
        statusCode: 400,
      });
    }

    if (!VALID_ROLES.includes(role)) {
      return res.status(400).json({
        error: `role must be one of ${VALID_ROLES.join(', ')}`,
        code: 'VALIDATION_ERROR',
        statusCode: 400,
      });
    }

    const existing = await query('SELECT id FROM users WHERE email = $1', [email]);
    if (existing.rows.length > 0) {
      return res.status(409).json({
        error: 'A user with this email already exists',
        code: 'CONFLICT',
        statusCode: 409,
      });
    }

    const passwordHash = await bcrypt.hash(password, 10);

    const result = await query(
      `INSERT INTO users (email, "passwordHash", role, "fullName", ward)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id, email, role, "fullName", ward, "isActive", "createdAt"`,
      [email, passwordHash, role, fullName, ward || null],
    );

    return res.status(201).json({ user: result.rows[0] });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      error: 'Failed to register user',
      code: 'INTERNAL_ERROR',
      statusCode: 500,
    });
  }
});

// POST /api/auth/login
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        error: 'email and password are required',
        code: 'VALIDATION_ERROR',
        statusCode: 400,
      });
    }

    const result = await query('SELECT * FROM users WHERE email = $1', [email]);
    const user = result.rows[0];

    if (!user || !user.isActive) {
      return res.status(401).json({
        error: 'Invalid credentials',
        code: 'UNAUTHORIZED',
        statusCode: 401,
      });
    }

    const passwordMatches = await bcrypt.compare(password, user.passwordHash);
    if (!passwordMatches) {
      return res.status(401).json({
        error: 'Invalid credentials',
        code: 'UNAUTHORIZED',
        statusCode: 401,
      });
    }

    await query('UPDATE users SET "lastLogin" = now() WHERE id = $1', [user.id]);

    const accessToken = signAccessToken(user);
    const refreshToken = signRefreshToken(user);

    res.cookie(REFRESH_COOKIE_NAME, refreshToken, REFRESH_COOKIE_OPTIONS);

    return res.status(200).json({
      accessToken,
      user: {
        id: user.id,
        email: user.email,
        role: user.role,
        fullName: user.fullName,
        ward: user.ward,
      },
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      error: 'Failed to log in',
      code: 'INTERNAL_ERROR',
      statusCode: 500,
    });
  }
});

// POST /api/auth/refresh
router.post('/refresh', async (req, res) => {
  try {
    const token = req.cookies?.[REFRESH_COOKIE_NAME];
    if (!token) {
      return res.status(401).json({
        error: 'Missing refresh token',
        code: 'UNAUTHORIZED',
        statusCode: 401,
      });
    }

    let decoded;
    try {
      decoded = verifyToken(token);
    } catch (err) {
      return res.status(401).json({
        error: 'Invalid or expired refresh token',
        code: 'UNAUTHORIZED',
        statusCode: 401,
      });
    }

    if (decoded.type !== 'refresh') {
      return res.status(401).json({
        error: 'Invalid refresh token',
        code: 'UNAUTHORIZED',
        statusCode: 401,
      });
    }

    const result = await query('SELECT * FROM users WHERE id = $1', [decoded.sub]);
    const user = result.rows[0];

    if (!user || !user.isActive) {
      return res.status(401).json({
        error: 'User not found or inactive',
        code: 'UNAUTHORIZED',
        statusCode: 401,
      });
    }

    const accessToken = signAccessToken(user);
    return res.status(200).json({ accessToken });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      error: 'Failed to refresh token',
      code: 'INTERNAL_ERROR',
      statusCode: 500,
    });
  }
});

// POST /api/auth/logout
router.post('/logout', (req, res) => {
  res.clearCookie(REFRESH_COOKIE_NAME, { path: '/api/auth' });
  return res.status(200).json({ message: 'Logged out' });
});

// GET /api/auth/me
router.get('/me', authenticate, async (req, res) => {
  try {
    const result = await query(
      'SELECT id, email, role, "fullName", ward, "isActive", "lastLogin", "createdAt" FROM users WHERE id = $1',
      [req.user.sub],
    );
    const user = result.rows[0];

    if (!user) {
      return res.status(404).json({
        error: 'User not found',
        code: 'NOT_FOUND',
        statusCode: 404,
      });
    }

    return res.status(200).json({ user });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      error: 'Failed to fetch current user',
      code: 'INTERNAL_ERROR',
      statusCode: 500,
    });
  }
});

module.exports = router;
