import { useCallback, useEffect, useState } from 'react'
import { ArrowPathIcon } from '@heroicons/react/24/outline'
import OverviewTab from './tabs/OverviewTab.jsx'
import VitalsTab from './tabs/VitalsTab.jsx'
import AIInsightsTab from './tabs/AIInsightsTab.jsx'
import MedicationsTab from './tabs/MedicationsTab.jsx'
import PrescribeModal from './PrescribeModal.jsx'
import {
  getEncounter,
  getPatient,
  getVitals,
  getMedications,
  getLatestPrediction,
  triggerAssessment,
  discontinueMedication,
} from '../services/api.js'

const TABS = ['Overview', 'Vitals', 'AI Insights', 'Medications']

function formatRelativeTime(dateStr) {
  if (!dateStr) return '—'
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.round(diffMs / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} hr ago`
  return `${Math.round(hours / 24)} d ago`
}

export default function PatientDetail({ encounterId, onAssessmentComplete }) {
  const [encounter, setEncounter] = useState(null)
  const [patient, setPatient] = useState(null)
  const [vitals, setVitals] = useState([])
  const [medications, setMedications] = useState([])
  const [prediction, setPrediction] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('Overview')
  const [assessing, setAssessing] = useState(false)
  const [showPrescribeModal, setShowPrescribeModal] = useState(false)

  const fetchAll = useCallback(async () => {
    setLoading(true)
    try {
      const encRes = await getEncounter(encounterId)
      const enc = encRes.data.data

      // GET /api/encounters/:id only embeds a partial patient record (no
      // dob/contactPhone) — fetch the full patient row for the Overview tab.
      const [vitalsRes, medsRes, predRes, patientRes] = await Promise.all([
        getVitals(encounterId),
        getMedications(encounterId),
        getLatestPrediction(encounterId),
        getPatient(enc.patientId),
      ])

      setEncounter(enc)
      setVitals(vitalsRes.data.data)
      setMedications(medsRes.data.data)
      setPrediction(predRes.data.data)
      setPatient(patientRes.data.data)
      setError('')
    } catch {
      setError('Failed to load patient details.')
    } finally {
      setLoading(false)
    }
  }, [encounterId])

  useEffect(() => {
    setActiveTab('Overview')
    fetchAll()
  }, [fetchAll])

  const refreshMedications = useCallback(async () => {
    try {
      const { data } = await getMedications(encounterId)
      setMedications(data.data)
    } catch {
      // non-critical — table just stays stale until next successful refresh
    }
  }, [encounterId])

  const refreshPrediction = useCallback(async () => {
    try {
      const { data } = await getLatestPrediction(encounterId)
      setPrediction(data.data)
    } catch {
      // non-critical
    }
  }, [encounterId])

  const handleRunAssessment = async () => {
    setAssessing(true)
    setError('')
    try {
      await triggerAssessment(encounterId)
      await refreshPrediction()
      onAssessmentComplete?.()
    } catch {
      setError('AI assessment failed. Please try again.')
    } finally {
      setAssessing(false)
    }
  }

  const handleDiscontinue = async (medicationId) => {
    if (!window.confirm('Discontinue this medication?')) return
    try {
      await discontinueMedication(medicationId)
      await refreshMedications()
    } catch {
      setError('Failed to discontinue medication.')
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center py-20">
        <ArrowPathIcon className="w-8 h-8 text-primary animate-spin" />
      </div>
    )
  }

  if (!encounter || !patient) {
    return <p className="text-center text-sm text-gray-400 py-10">Patient not found.</p>
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2.5 flex items-center justify-between">
          <span>{error}</span>
          <button type="button" onClick={() => setError('')} className="text-red-400 hover:text-red-600" aria-label="Dismiss">
            ✕
          </button>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-sm p-5">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-800">{patient.fullName}</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {patient.patientCode} · {patient.gender || '—'} · {patient.bloodType || '—'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Ward: {encounter.ward || '—'} / Bed: {encounter.bedId || '—'}
            </p>
            <p className="text-xs text-gray-400 mt-1">Admitted {formatRelativeTime(encounter.admittedAt)}</p>
          </div>
          <button
            type="button"
            onClick={handleRunAssessment}
            disabled={assessing}
            className="shrink-0 bg-primary text-white text-sm font-semibold rounded-lg px-4 py-2.5 hover:bg-primary/90 transition disabled:opacity-60 flex items-center gap-2"
          >
            {assessing && <ArrowPathIcon className="w-4 h-4 animate-spin" />}
            {assessing ? 'Running Assessment...' : 'Run AI Assessment'}
          </button>
        </div>

        <div className="flex gap-1 mt-5 bg-surface rounded-full p-1 w-fit">
          {TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
                activeTab === tab ? 'bg-primary text-white' : 'text-gray-600 hover:text-primary'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'Overview' && <OverviewTab encounter={encounter} patient={patient} />}
      {activeTab === 'Vitals' && <VitalsTab vitals={vitals} />}
      {activeTab === 'AI Insights' && (
        <AIInsightsTab
          prediction={prediction}
          encounterId={encounterId}
          onRefresh={handleRunAssessment}
          assessing={assessing}
        />
      )}
      {activeTab === 'Medications' && (
        <MedicationsTab
          medications={medications}
          encounterId={encounterId}
          onPrescribe={() => setShowPrescribeModal(true)}
          onDiscontinue={handleDiscontinue}
        />
      )}

      {showPrescribeModal && (
        <PrescribeModal
          encounterId={encounterId}
          onClose={() => setShowPrescribeModal(false)}
          onSuccess={() => {
            setShowPrescribeModal(false)
            refreshMedications()
          }}
        />
      )}
    </div>
  )
}
