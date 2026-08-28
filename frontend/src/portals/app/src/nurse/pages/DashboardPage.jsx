import { useCallback, useEffect, useState } from 'react'
import {
  UserGroupIcon,
  ExclamationTriangleIcon,
  FireIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import Navbar from '../components/Navbar.jsx'
import StatCard from '../components/StatCard.jsx'
import PatientRiskQueue from '../components/PatientRiskQueue.jsx'
import AlertPanel from '../components/AlertPanel.jsx'
import LogVitalsModal from '../components/LogVitalsModal.jsx'
import TreatmentChecklist from '../components/TreatmentChecklist.jsx'
import { useAuth } from '../../context/AuthContext.jsx'
import { connectSocket } from '../../services/socket.js'
import { getEncounters, getLatestPrediction, getNotifications } from '../../services/api.js'

function playAlertSound() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()
    const oscillator = ctx.createOscillator()
    const gain = ctx.createGain()
    oscillator.type = 'sine'
    oscillator.frequency.value = 880
    gain.gain.setValueAtTime(0.15, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4)
    oscillator.connect(gain)
    gain.connect(ctx.destination)
    oscillator.start()
    oscillator.stop(ctx.currentTime + 0.4)
  } catch {
    // audio playback blocked/unavailable — non-critical
  }
}

export default function DashboardPage() {
  const { user, token } = useAuth()
  const [encounters, setEncounters] = useState([])
  const [alerts, setAlerts] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [selectedEncounter, setSelectedEncounter] = useState(null)
  const [vitalsTarget, setVitalsTarget] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [flash, setFlash] = useState(false)

  const fetchEncounters = useCallback(async () => {
    try {
      const { data } = await getEncounters()
      const base = data.data

      // GET /api/encounters doesn't carry AI scores, so — same as the
      // doctor portal's MainPage — backfill each encounter's latest
      // persisted prediction on load instead of relying solely on
      // Socket.io events (which only fire for NEW updates, leaving a
      // freshly-loaded page stuck on "PENDING" for existing scores).
      const withRisk = await Promise.all(
        base.map(async (enc) => {
          try {
            const predRes = await getLatestPrediction(enc.id)
            const pred = predRes.data.data
            const sepsisResult = pred?.result?.sepsis?.result
            return {
              ...enc,
              latestRisk: sepsisResult ? { ...sepsisResult, predictedAt: pred.predictedAt } : null,
              lastVitalsAt: null,
            }
          } catch {
            return { ...enc, latestRisk: null, lastVitalsAt: null }
          }
        }),
      )

      setEncounters((prev) => {
        const prevById = new Map(prev.map((e) => [e.id, e]))
        return withRisk.map((enc) => {
          const prevEnc = prevById.get(enc.id)
          return {
            ...enc,
            // Prefer the freshly-fetched prediction, but keep a
            // socket-derived lastVitalsAt if we already had one and the
            // fetch didn't provide a newer value.
            lastVitalsAt: enc.lastVitalsAt ?? prevEnc?.lastVitalsAt ?? null,
          }
        })
      })
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
    const socket = connectSocket(token, user?.role)

    const handleAlert = (data) => {
      const withTimestamp = { ...data, receivedAt: new Date().toISOString() }
      setAlerts((prev) => [withTimestamp, ...prev].slice(0, 10))
      setEncounters((prev) =>
        prev.map((enc) =>
          enc.id === data.encounter_id
            ? { ...enc, latestRisk: { ...enc.latestRisk, ...data, alertTriggered: true } }
            : enc,
        ),
      )
      playAlertSound()
      setFlash(true)
      setTimeout(() => setFlash(false), 3000)
      fetchNotifications()
    }

    const handleScoreUpdated = (data) => {
      setEncounters((prev) =>
        prev.map((enc) =>
          enc.id === data.encounter_id ? { ...enc, latestRisk: { ...enc.latestRisk, ...data } } : enc,
        ),
      )
    }

    const handleVitalsLogged = (data) => {
      setEncounters((prev) =>
        prev.map((enc) => (enc.id === data.encounter_id ? { ...enc, lastVitalsAt: data.recorded_at } : enc)),
      )
      fetchEncounters()
    }

    socket?.on('sepsis:alert', handleAlert)
    socket?.on('sepsis:score_updated', handleScoreUpdated)
    socket?.on('vitals:logged', handleVitalsLogged)

    return () => {
      socket?.off('sepsis:alert', handleAlert)
      socket?.off('sepsis:score_updated', handleScoreUpdated)
      socket?.off('vitals:logged', handleVitalsLogged)
    }
  }, [token, user?.role, fetchEncounters, fetchNotifications])

  const totalActive = encounters.length
  const highRisk = encounters.filter((e) => e.latestRisk?.risk_level === 'high').length
  const critical = encounters.filter((e) => e.latestRisk?.risk_score > 0.85).length
  const stable = encounters.filter((e) => !e.latestRisk || e.latestRisk.risk_level === 'low').length

  const today = new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <div className="min-h-screen bg-surface">
      <Navbar unreadCount={unreadCount} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <header className="mb-6 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
          <div>
            <h1 className="text-2xl font-bold text-primary">ICU Nurse Station</h1>
            <p className="text-sm text-gray-500 mt-1">Manage sepsis patients, log vitals, monitor alerts</p>
          </div>
          <div className="text-left sm:text-right text-sm">
            <p className="font-medium text-gray-700">MediCore General Hospital</p>
            <p className="text-gray-500">{today}</p>
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard icon={UserGroupIcon} label="Total Patients" value={totalActive} color="primary" />
              <StatCard icon={ExclamationTriangleIcon} label="High Risk" value={highRisk} color="orange" />
              <StatCard icon={FireIcon} label="Critical" value={critical} color="red" />
              <StatCard icon={CheckCircleIcon} label="Stable" value={stable} color="green" />
            </div>

            <PatientRiskQueue
              encounters={encounters}
              loading={loading}
              selectedId={selectedEncounter?.id}
              onSelectPatient={setSelectedEncounter}
              onLogVitals={(encounter) => {
                setSelectedEncounter(encounter)
                setVitalsTarget(encounter)
              }}
            />

            {selectedEncounter && (
              <div className="bg-white rounded-2xl shadow-sm p-5">
                <h2 className="font-bold text-gray-800 mb-4">
                  Sepsis Bundle Compliance — {selectedEncounter.patientName}
                </h2>
                <TreatmentChecklist encounterId={selectedEncounter.id} />
              </div>
            )}
          </div>

          <div className="space-y-6">
            <AlertPanel alerts={alerts} totalPatients={totalActive} flash={flash} />

            <div className="bg-white rounded-2xl shadow-sm p-5">
              <h3 className="font-bold text-gray-800 mb-3">Shift Info</h3>
              <dl className="space-y-1.5 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Ward</dt>
                  <dd className="text-gray-700 font-medium">{user?.ward || '—'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Shift</dt>
                  <dd className="text-gray-700 font-medium">Day</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Nurse</dt>
                  <dd className="text-gray-700 font-medium">{user?.fullName || '—'}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </main>

      {vitalsTarget && (
        <LogVitalsModal encounter={vitalsTarget} onClose={() => setVitalsTarget(null)} onSuccess={() => {}} />
      )}
    </div>
  )
}
