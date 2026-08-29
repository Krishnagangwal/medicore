import axios from 'axios'

// `??` (not `||`) so an intentionally-empty VITE_API_URL (dev: same-origin,
// proxied by Vite — see vite.config.js) isn't clobbered by the fallback.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:5000',
  // Needed so the httpOnly refresh-token cookie (set by /api/auth/login,
  // scoped to /api/auth) actually gets sent to /api/auth/refresh — matches
  // the backend's cors({ credentials: true }).
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('medicore_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function logoutToLogin() {
  localStorage.removeItem('medicore_token')
  localStorage.removeItem('medicore_user')
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

// The access token is short-lived (24h) but the refresh cookie lasts 7d
// (backend/src/utils/jwt.js). Previously a 401 just logged the user out
// immediately, so sessions never actually lasted past 24h even though the
// refresh endpoint already existed — this makes a 401 try silently
// refreshing first, only falling back to a real logout if that also fails.
// `refreshPromise` dedupes concurrent 401s (e.g. several requests firing at
// once) into a single in-flight refresh instead of racing multiple calls.
let refreshPromise = null

function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(
        `${api.defaults.baseURL}/api/auth/refresh`,
        {},
        { withCredentials: true },
      )
      .then(({ data }) => {
        localStorage.setItem('medicore_token', data.accessToken)
        return data.accessToken
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error
    const isAuthEndpoint = config?.url?.includes('/api/auth/login') || config?.url?.includes('/api/auth/refresh')

    if (response?.status === 401 && !config?._retriedAfterRefresh && !isAuthEndpoint) {
      config._retriedAfterRefresh = true
      try {
        const newToken = await refreshAccessToken()
        config.headers.Authorization = `Bearer ${newToken}`
        return api(config)
      } catch {
        logoutToLogin()
        return Promise.reject(error)
      }
    }

    if (response?.status === 401) {
      logoutToLogin()
    }
    return Promise.reject(error)
  },
)

// Accepts either login shape the backend supports: { email, password }
// (super admin / plain email login) or { userId, password, hospitalId }
// (hospital staff dropdown login, see LoginPage.jsx's multi-step flow).
export const login = (credentials) => api.post('/api/auth/login', credentials)

// Self-service signup — POST /api/auth/register is intentionally open (no
// auth required) on the backend. payload: { email, password, role, fullName, ward }
// No longer used by any page (RequestPage.jsx uses requestHospitalAccess
// instead) but left in place — the backend route is still there too.
export const register = (payload) => api.post('/api/auth/register', payload)

// Public — approved hospitals for the login dropdown.
export const getHospitals = () => api.get('/api/hospitals')

// Public — active staff of one hospital for the login name dropdown.
export const getHospitalStaff = (hospitalId, role) =>
  api.get(`/api/hospitals/${hospitalId}/staff`, { params: { role } })

// Public — a prospective hospital's access request.
export const requestHospitalAccess = (payload) => api.post('/api/hospitals/request', payload)

export const getEncounters = () => api.get('/api/encounters')

export const getEncounter = (id) => api.get(`/api/encounters/${id}`)

// GET /api/patients/:id is the only source for dob/contactPhone — the
// encounter detail endpoint only embeds a partial patient record. Used by
// the doctor portal's OverviewTab.
export const getPatient = (id) => api.get(`/api/patients/${id}`)

export const getVitals = (encounterId) => api.get(`/api/encounters/${encounterId}/vitals`)

export const logVitals = (data) => api.post('/api/vitals', data)

export const getMedications = (encounterId) => api.get(`/api/encounters/${encounterId}/medications`)

export const prescribeMedication = (data) => api.post('/api/medications', data)

export const discontinueMedication = (id) => api.patch(`/api/medications/${id}/discontinue`)

export const getLatestPrediction = (encounterId) =>
  api.get(`/api/encounters/${encounterId}/predictions/latest`)

export const triggerAssessment = (encounterId) => api.post('/api/gateway/assess', { encounterId })

export const getNotifications = () => api.get('/api/notifications')

export const markNotificationRead = (id) => api.patch(`/api/notifications/${id}/read`)

export default api
