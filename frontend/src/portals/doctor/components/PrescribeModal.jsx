import { useState } from 'react'
import { XMarkIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { prescribeMedication } from '../services/api.js'

const ROUTES = ['IV', 'Oral', 'IM', 'Subcutaneous', 'Inhaled']

export default function PrescribeModal({ encounterId, onClose, onSuccess }) {
  const [drugName, setDrugName] = useState('')
  const [genericName, setGenericName] = useState('')
  const [dosage, setDosage] = useState('')
  const [frequency, setFrequency] = useState('')
  const [route, setRoute] = useState(ROUTES[0])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!drugName.trim()) {
      setError('Drug name is required.')
      return
    }

    setLoading(true)
    try {
      await prescribeMedication({
        encounterId,
        drugName: drugName.trim(),
        genericName: genericName.trim() || undefined,
        dosage: dosage.trim() || undefined,
        frequency: frequency.trim() || undefined,
        route: route || undefined,
      })
      setSuccess(true)
      // The drug:interaction Socket.io event (if a major interaction is
      // found) arrives separately — this modal only confirms the Rx saved.
      setTimeout(() => {
        onSuccess?.()
      }, 800)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to prescribe medication.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-[480px] max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between p-5 border-b border-gray-100">
          <div>
            <h2 className="font-bold text-gray-800">Prescribe Medication</h2>
            <p className="text-xs text-gray-500 mt-0.5">Drug interaction check will run automatically.</p>
          </div>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Close">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {success ? (
          <div className="py-12 flex flex-col items-center gap-2">
            <CheckCircleIcon className="w-12 h-12 text-accent" />
            <p className="text-sm text-gray-600">Medication prescribed</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-5 space-y-4">
            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2">{error}</div>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Drug Name *</label>
              <input
                type="text"
                value={drugName}
                onChange={(e) => setDrugName(e.target.value)}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Generic Name</label>
              <input
                type="text"
                value={genericName}
                onChange={(e) => setGenericName(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Dosage</label>
                <input
                  type="text"
                  value={dosage}
                  onChange={(e) => setDosage(e.target.value)}
                  placeholder="e.g. 500mg"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Frequency</label>
                <input
                  type="text"
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value)}
                  placeholder="e.g. Every 8 hours"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Route</label>
              <select
                value={route}
                onChange={(e) => setRoute(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent bg-white"
              >
                {ROUTES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition disabled:opacity-60"
            >
              {loading ? 'Prescribing...' : 'Prescribe & Check Interactions'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
