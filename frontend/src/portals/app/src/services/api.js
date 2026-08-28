import axios from 'axios'

// `??` (not `||`) so an intentionally-empty VITE_API_URL (dev: same-origin,
// proxied by Vite — see vite.config.js) isn't clobbered by the fallback.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:5000',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('medicore_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('medicore_token')
      localStorage.removeItem('medicore_user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export const login = (email, password) => api.post('/api/auth/login', { email, password })

// Self-service signup — POST /api/auth/register is intentionally open (no
// auth required) on the backend. payload: { email, password, role, fullName, ward }
export const register = (payload) => api.post('/api/auth/register', payload)

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
