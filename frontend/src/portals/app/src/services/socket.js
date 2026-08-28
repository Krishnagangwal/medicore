import { io } from 'socket.io-client'

let socket = null
let connectedNamespace = null

// `??` (not `||`) so an intentionally-empty VITE_SOCKET_URL (dev: same-origin,
// proxied by Vite — see vite.config.js) isn't clobbered by the fallback.
const SOCKET_URL = import.meta.env.VITE_SOCKET_URL ?? 'http://localhost:5000'

// The backend namespaces sockets via io.of('/nurse' | '/doctor' | '/admin'),
// gated by role via authenticateSocket(requiredRole) — unlike the old
// separate nurse/doctor portals (which each hardcoded their own namespace),
// this merged app serves every role, so the namespace is derived from the
// logged-in user's role instead.
export function connectSocket(token, role) {
  const namespace = role ? role.toLowerCase() : null

  // Guard on existence + namespace match (not just `.connected`) so callers
  // racing during the handshake — e.g. AuthContext on restore vs. a
  // dashboard's mount effect — reuse the in-flight socket instead of opening
  // a second connection. If the namespace doesn't match (e.g. a different
  // role logged in), tear down the stale socket and reconnect.
  if (socket && connectedNamespace === namespace) return socket
  if (socket) disconnectSocket()

  if (!namespace) return null

  // socket.io-client joins a namespace through the URL path, not a
  // `namespace` option.
  socket = io(`${SOCKET_URL}/${namespace}`, {
    path: '/socket.io',
    auth: { token },
    transports: ['websocket'],
    reconnection: true,
    reconnectionDelay: 2000,
  })
  connectedNamespace = namespace

  socket.on('connect', () => {
    console.log(`[Socket] Connected to /${namespace} namespace`)
  })

  socket.on('connect_error', (err) => {
    console.error('[Socket] Connection error:', err.message)
  })

  return socket
}

export function disconnectSocket() {
  socket?.disconnect()
  socket = null
  connectedNamespace = null
}

export function getSocket() {
  return socket
}
