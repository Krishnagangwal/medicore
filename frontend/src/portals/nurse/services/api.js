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

export const getEncounters = () => api.get('/api/encounters')

export const getEncounter = (id) => api.get(`/api/encounters/${id}`)

export const getVitals = (encounterId) => api.get(`/api/encounters/${encounterId}/vitals`)

export const logVitals = (data) => api.post('/api/vitals', data)

export const getLatestPrediction = (encounterId) =>
  api.get(`/api/encounters/${encounterId}/predictions/latest`)

export const getNotifications = () => api.get('/api/notifications')

export const markNotificationRead = (id) => api.patch(`/api/notifications/${id}/read`)

export default api
