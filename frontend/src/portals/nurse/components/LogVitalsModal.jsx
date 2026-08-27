import { useState } from 'react'
import { XMarkIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { logVitals } from '../services/api.js'

const FIELDS = [
  { key: 'heartRate', label: 'Heart Rate', unit: 'bpm' },
  { key: 'spo2', label: 'SpO2', unit: '%' },
  { key: 'temperature', label: 'Temperature', unit: '°C' },
  { key: 'respiratoryRate', label: 'Resp Rate', unit: 'breaths/min' },
  { key: 'systolicBp', label: 'Systolic BP', unit: 'mmHg' },
  { key: 'map', label: 'MAP', unit: 'mmHg' },
]

export default function LogVitalsModal({ encounter, onClose, onSuccess }) {
  const [values, setValues] = useState({})
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleChange = (key, value) => {
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    const hasValue = FIELDS.some((f) => values[f.key] !== undefined && values[f.key] !== '')
    if (!hasValue) {
      setError('At least one vital value is required.')
      return
    }

    setLoading(true)
    try {
      const payload = { encounterId: encounter.id }
      FIELDS.forEach((f) => {
        if (values[f.key] !== undefined && values[f.key] !== '') {
          payload[f.key] = Number(values[f.key])
        }
      })
      if (notes.trim()) payload.notes = notes.trim()

      await logVitals(payload)
      setSuccess(true)
      // The AI-triggered risk score arrives separately via Socket.io —
      // this modal only confirms the vitals were saved.
      setTimeout(() => {
        onSuccess?.()
        onClose()
      }, 1000)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to log vitals. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-[480px] max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between p-5 border-b border-gray-100">
          <div>
            <h2 className="font-bold text-gray-800">Log Vitals — {encounter.patientName}</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Ward {encounter.ward || '—'} / Bed {encounter.bedId || '—'}
            </p>
          </div>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Close">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {success ? (
          <div className="py-12 flex flex-col items-center gap-2">
            <CheckCircleIcon className="w-12 h-12 text-accent" />
            <p className="text-sm text-gray-600">Vitals logged successfully</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-5 space-y-4">
            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2">
                {error}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              {FIELDS.map((f) => (
                <div key={f.key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {f.label} <span className="text-gray-400">({f.unit})</span>
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={values[f.key] ?? ''}
                    onChange={(e) => handleChange(f.key, e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>
              ))}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition disabled:opacity-60"
            >
              {loading ? 'Logging...' : 'Log Vitals & Trigger AI Assessment'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
