import { useCallback, useEffect, useMemo, useState } from 'react'
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import Navbar from '../components/Navbar.jsx'
import PatientRiskQueue from '../components/PatientRiskQueue.jsx'
import LogVitalsModal from '../components/LogVitalsModal.jsx'
import AdmitPatientModal from '../components/AdmitPatientModal.jsx'
import { getEncounters, getLatestPrediction, getNotifications } from '../../services/api.js'

export default function PatientsPage() {
  const [encounters, setEncounters] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [selectedEncounter, setSelectedEncounter] = useState(null)
  const [vitalsTarget, setVitalsTarget] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [admitting, setAdmitting] = useState(false)

  const fetchEncounters = useCallback(async () => {
    try {
      const { data } = await getEncounters()
      const base = data.data

      // Same backfill pattern as the dashboard/doctor MainPage: the list
      // endpoint doesn't carry AI scores, so fetch each encounter's latest
      // persisted prediction individually.
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

  const filtered = useMemo(() => {
    if (!search.trim()) return encounters
    const q = search.trim().toLowerCase()
    return encounters.filter(
      (e) => e.patientName?.toLowerCase().includes(q) || e.patientCode?.toLowerCase().includes(q),
    )
  }, [encounters, search])

  return (
    <div className="min-h-screen bg-surface">
      <Navbar unreadCount={unreadCount} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <header className="mb-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-primary">Patients</h1>
            <p className="text-sm text-gray-500 mt-1">All active patient encounters in your ward</p>
          </div>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <MagnifyingGlassIcon className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search patients..."
                className="w-full rounded-lg border border-gray-200 bg-white pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
            <button
              type="button"
              onClick={() => setAdmitting(true)}
              className="shrink-0 bg-primary text-white text-sm font-semibold rounded-lg px-4 py-2 hover:bg-primary/90 transition"
            >
              + Admit Patient
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-6 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2.5 flex items-center justify-between">
            <span>{error}</span>
            <button type="button" onClick={() => setError('')} className="text-red-400 hover:text-red-600" aria-label="Dismiss">
              ✕
            </button>
          </div>
        )}

        <PatientRiskQueue
          encounters={filtered}
          loading={loading}
          selectedId={selectedEncounter?.id}
          onSelectPatient={setSelectedEncounter}
          onLogVitals={(encounter) => {
            setSelectedEncounter(encounter)
            setVitalsTarget(encounter)
          }}
        />
      </main>

      {vitalsTarget && (
        <LogVitalsModal
          encounter={vitalsTarget}
          onClose={() => setVitalsTarget(null)}
          onSuccess={fetchEncounters}
        />
      )}

      {admitting && (
        <AdmitPatientModal onClose={() => setAdmitting(false)} onSuccess={fetchEncounters} />
      )}
    </div>
  )
}
