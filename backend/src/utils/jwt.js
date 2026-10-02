const jwt = require('jsonwebtoken');

const ISSUER = 'medicore-api';
const ACCESS_TOKEN_TTL = '24h';
const REFRESH_TOKEN_TTL = '7d';

function getSecret() {
  const secret = process.env.JWT_SECRET;
  if (!secret) {
    throw new Error('JWT_SECRET is not set');
  }
  return secret;
}

function basePayload(user) {
  return {
    sub: user.id,
    email: user.email,
    role: user.role,
    fullName: user.fullName,
    patientId: user.patientId || null,
    // hospitalName isn't a column on users — callers (auth.routes.js) must
    // look it up via the hospitals table and attach it to `user` before
    // signing, since this function stays DB-free/synchronous.
    hospitalId: user.hospitalId || null,
    hospitalName: user.hospitalName || null,
  };
}

function signAccessToken(user) {
  return jwt.sign(basePayload(user), getSecret(), {
    issuer: ISSUER,
    expiresIn: ACCESS_TOKEN_TTL,
  });
}

function signRefreshToken(user) {
  return jwt.sign({ sub: user.id, type: 'refresh' }, getSecret(), {
    issuer: ISSUER,
    expiresIn: REFRESH_TOKEN_TTL,
  });
}

// Set-password link sent in approval/invite emails (and reused for a future
// self-service "forgot password" flow). Stateless — no DB row to revoke —
// so the short TTL is what bounds how long a leaked link stays usable.
const RESET_TOKEN_TTL = '1h';

function signResetToken(user) {
  return jwt.sign({ sub: user.id, type: 'reset' }, getSecret(), {
    issuer: ISSUER,
    expiresIn: RESET_TOKEN_TTL,
  });
}

function verifyToken(token) {
  return jwt.verify(token, getSecret(), { issuer: ISSUER });
}

// Short-lived token for server-to-server calls (e.g. the scoring cron job
// calling the AI Gateway, which requires a Bearer token on every request).
function signServiceToken() {
  return jwt.sign(
    {
      sub: 'system-scoring-job',
      email: 'system@medicore.local',
      role: 'ADMIN',
      fullName: 'MediCore Scoring Job',
      patientId: null,
    },
    getSecret(),
    { issuer: ISSUER, expiresIn: '5m' },
  );
}

module.exports = { signAccessToken, signRefreshToken, signResetToken, signServiceToken, verifyToken, ISSUER };
