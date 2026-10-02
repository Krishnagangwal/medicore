const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const cookieParser = require('cookie-parser');
const rateLimit = require('express-rate-limit');

const routes = require('./routes');
const { notFoundHandler, errorHandler } = require('./middleware/errorHandler');

const app = express();

// Render (and most PaaS hosts) sit the app behind a reverse proxy, so every
// request arrives with an X-Forwarded-For header. Without this, Express
// doesn't trust it, which breaks express-rate-limit's per-IP tracking and
// throws a validation warning on every request. `1` = trust exactly one
// hop (the platform's own proxy) — safe in production where that's always
// true; left untrusted in dev where there's no proxy in front at all.
if (process.env.NODE_ENV === 'production') {
  app.set('trust proxy', 1);
}

app.use(helmet());

// CORS_ORIGIN is a comma-separated list — one entry per deployed portal
// (app/nurse/doctor each live on their own Vercel URL). `credentials: true`
// means the Allow-Origin header must echo back a real origin, never a
// literal '*' (browsers reject credentialed responses against '*'), so this
// reflects the request's origin only when it's on the allowlist. No
// CORS_ORIGIN set at all (local dev hitting the backend directly, outside
// Vite's same-origin proxy) falls back to allowing any origin, matching the
// previous default.
const allowedOrigins = (process.env.CORS_ORIGIN || '')
  .split(',')
  .map((o) => o.trim())
  .filter(Boolean);

app.use(
  cors({
    origin: (origin, callback) => {
      // No Origin header at all = server-to-server / curl / Postman — let it through.
      if (!origin || allowedOrigins.length === 0 || allowedOrigins.includes(origin)) {
        return callback(null, true);
      }
      return callback(new Error(`CORS: origin ${origin} not allowed`));
    },
    credentials: true,
  }),
);
app.use(morgan(process.env.NODE_ENV === 'production' ? 'combined' : 'dev'));
app.use(express.json());
app.use(cookieParser());

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 300,
  standardHeaders: true,
  legacyHeaders: false,
});
app.use('/api', limiter);

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', service: 'medicore-backend' });
});

app.use('/api', routes);

app.use(notFoundHandler);
app.use(errorHandler);

module.exports = app;
