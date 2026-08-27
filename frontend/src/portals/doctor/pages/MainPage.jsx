import { useCallback, useEffect, useState } from 'react'
import Navbar from '../components/Navbar.jsx'
import PatientSidebar from '../components/PatientSidebar.jsx'
import PatientDetail from '../components/PatientDetail.jsx'
import DrugInteractionAlert from '../components/DrugInteractionAlert.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { connectSocket } from '../services/socket.js'
import { getEncounters, getLatestPrediction, getNotifications } from '../services/api.js'

export default function MainPage() {
  const { token } = useAuth()
  const [encounters, setEncounters] = useState([])
  const [selectedEncounterId, setSelectedEncounterId] = useState(null)
  const [drugAlerts, setDrugAlerts] = useState([])
  const [activeAlert, setActiveAlert] = useState(null)
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchEncounters = useCallback(async () => {
    try {
      const { data } = await getEncounters()
      const base = data.data

      // The list endpoint doesn't carry AI scores, and the /doctor socket
      // only pushes drug alerts (see backend sockets/index.js) — so the
      // sidebar's risk badges need each encounter's latest prediction
      // fetched individually. Active ICU counts are small, so N+1 here is fine.
      const withRisk = await Promise.all(
        base.map(async (enc) => {
          try {
            const predRes = await getLatestPrediction(enc.id)
            const pred = predRes.data.data
            const sepsisResult = pred?.result?.sepsis?.result
            return {
              ...enc,
              latestRisk: sepsisResult ? { ...sepsisResult, predictedAt: pred.predictedAt } : null,
            }
          } catch {
            return { ...enc, latestRisk: null }
          }
        }),
      )

      setEncounters(withRisk)
      setError('')
    } catch {
      setError('Failed to load patient encounters.')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchNotifications = useCallback(async () => {
    try {
      const { data } = await getNotifications()
      setUnreadCount(data.unreadCount || 0)
    } catch {
      // non-critical — leave unread count as-is
    }
  }, [])

  useEffect(() => {
    fetchEncounters()
    fetchNotifications()
    const interval = setInterval(fetchEncounters, 60000)
    return () => clearInterval(interval)
  }, [fetchEncounters, fetchNotifications])

  useEffect(() => {
    const socket = connectSocket(token)

    const handleDrugInteraction = (data) => {
      setDrugAlerts((prev) => [data, ...prev])
      setActiveAlert(data)
    }

    socket.on('drug:interaction', handleDrugInteraction)

    return () => {
      socket.off('drug:interaction', handleDrugInteraction)
    }
  }, [token])

  return (
    <div className="h-screen flex flex-col bg-surface">
      <Navbar unreadCount={unreadCount} />

      {error && (
        <div className="bg-red-50 border-b border-red-200 text-red-600 text-sm px-4 py-2 flex items-center justify-between shrink-0">
          <span>{error}</span>
          <button type="button" onClick={() => setError('')} className="text-red-400 hover:text-red-600" aria-label="Dismiss">
            ✕
          </button>
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        <PatientSidebar
          encounters={encounters}
          selectedId={selectedEncounterId}
          onSelect={setSelectedEncounterId}
          loading={loading}
        />

        <main className="flex-1 overflow-y-auto p-6">
          {selectedEncounterId ? (
            <PatientDetail encounterId={selectedEncounterId} onAssessmentComplete={fetchEncounters} />
          ) : (
            <div className="h-full flex items-center justify-center text-center">
              <p className="text-gray-400 text-sm">Select a patient from the list</p>
            </div>
          )}
        </main>
      </div>

      {activeAlert && (
        <DrugInteractionAlert
          alert={activeAlert}
          onDismiss={() => setActiveAlert(null)}
        />
      )}
    </div>
  )
}
