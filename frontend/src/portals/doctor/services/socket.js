import { io } from 'socket.io-client'

let socket = null

// `??` (not `||`) so an intentionally-empty VITE_SOCKET_URL (dev: same-origin,
// proxied by Vite — see vite.config.js) isn't clobbered by the fallback.
const SOCKET_URL = import.meta.env.VITE_SOCKET_URL ?? 'http://localhost:5000'

export function connectSocket(token) {
  // Guard on existence (not just `.connected`) so callers racing during the
  // handshake — e.g. AuthContext on restore vs. MainPage on mount — reuse
  // the in-flight socket instead of opening a second connection.
  if (socket) return socket

  // The backend namespaces sockets via io.of('/doctor'); socket.io-client
  // joins a namespace through the URL path, not a `namespace` option.
  socket = io(`${SOCKET_URL}/doctor`, {
    path: '/socket.io',
    auth: { token },
    transports: ['websocket'],
    reconnection: true,
    reconnectionDelay: 2000,
  })

  socket.on('connect', () => {
    console.log('[Socket] Connected to /doctor namespace')
  })

  socket.on('connect_error', (err) => {
    console.error('[Socket] Connection error:', err.message)
  })

  return socket
}

export function disconnectSocket() {
  socket?.disconnect()
  socket = null
}

export function getSocket() {
  return socket
}
