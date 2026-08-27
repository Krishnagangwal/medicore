const { Server } = require('socket.io');
const { verifyToken } = require('../utils/jwt');

const NAMESPACE_ROLE = {
  '/nurse': 'NURSE',
  '/doctor': 'DOCTOR',
  '/admin': 'ADMIN',
};

let io = null;

function authenticateSocket(requiredRole) {
  return (socket, next) => {
    const token =
      socket.handshake.auth?.token ||
      (socket.handshake.headers.authorization || '').replace(/^Bearer\s+/i, '');

    if (!token) {
      return next(new Error('Missing auth token'));
    }

    try {
      const decoded = verifyToken(token);
      if (decoded.role !== requiredRole) {
        return next(new Error('Insufficient role for this namespace'));
      }
      socket.user = decoded;
      return next();
    } catch (err) {
      return next(new Error('Invalid or expired token'));
    }
  };
}

function initSockets(httpServer) {
  io = new Server(httpServer, {
    cors: {
      origin: process.env.CORS_ORIGIN || '*',
      credentials: true,
    },
  });

  Object.entries(NAMESPACE_ROLE).forEach(([namespace, role]) => {
    const nsp = io.of(namespace);
    nsp.use(authenticateSocket(role));

    nsp.on('connection', (socket) => {
      // Ward-scoped rooms let emitters target e.g. only ICU-B nurses.
      if (socket.user.ward) {
        socket.join(`ward:${socket.user.ward}`);
      }
      socket.join(`user:${socket.user.sub}`);

      console.log(`[socket] ${role} connected: ${socket.user.email} (${namespace})`);

      socket.on('disconnect', () => {
        console.log(`[socket] ${role} disconnected: ${socket.user.email} (${namespace})`);
      });
    });
  });

  return io;
}

function getIO() {
  if (!io) {
    throw new Error('Socket.io has not been initialized. Call initSockets(httpServer) first.');
  }
  return io;
}

// Event emitters — one per event in the CLAUDE.md Socket.io contract table.

function emitSepsisAlert(payload) {
  getIO().of('/nurse').emit('sepsis:alert', payload);
}

function emitScoreUpdated(payload) {
  getIO().of('/nurse').emit('sepsis:score_updated', payload);
}

function emitDrugInteraction(payload) {
  getIO().of('/doctor').emit('drug:interaction', payload);
}

function emitVitalsLogged(payload) {
  getIO().of('/nurse').emit('vitals:logged', payload);
}

function emitBedUpdated(payload) {
  getIO().of('/admin').emit('bed:updated', payload);
}

module.exports = {
  initSockets,
  getIO,
  emitSepsisAlert,
  emitScoreUpdated,
  emitDrugInteraction,
  emitVitalsLogged,
  emitBedUpdated,
};
