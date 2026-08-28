import { useState } from 'react'
import { PlusIcon } from '@heroicons/react/24/outline'

function formatDate(dateStr) {
  return dateStr ? new Date(dateStr).toLocaleString() : '—'
}

export default function MedicationsTab({ medications, onPrescribe, onDiscontinue }) {
  const [showDiscontinued, setShowDiscontinued] = useState(false)
  const active = medications.filter((m) => m.status === 'ACTIVE')
  const discontinued = medications.filter((m) => m.status === 'DISCONTINUED')

  return (
    <div className="bg-white rounded-2xl shadow-sm p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-gray-800">Active Medications</h3>
        <button
          type="button"
          onClick={onPrescribe}
          className="flex items-center gap-1.5 bg-primary text-white text-sm font-semibold rounded-lg px-3.5 py-2 hover:bg-primary/90 transition"
        >
          <PlusIcon className="w-4 h-4" />
          Prescribe
        </button>
      </div>

      {active.length === 0 ? (
        <p className="text-sm text-gray-400 py-6 text-center">No active medications</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase text-gray-400 border-b border-gray-100">
                <th className="py-2 px-3 font-medium">Drug Name</th>
                <th className="py-2 px-3 font-medium">Generic</th>
                <th className="py-2 px-3 font-medium">Dosage</th>
                <th className="py-2 px-3 font-medium">Frequency</th>
                <th className="py-2 px-3 font-medium">Route</th>
                <th className="py-2 px-3 font-medium">Prescribed</th>
                <th className="py-2 px-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {active.map((med) => (
                <tr key={med.id} className="border-b border-gray-50 last:border-0">
                  <td className="py-2.5 px-3 font-medium text-gray-800">{med.drugName}</td>
                  <td className="py-2.5 px-3 text-gray-500">{med.genericName || '—'}</td>
                  <td className="py-2.5 px-3 text-gray-500">{med.dosage || '—'}</td>
                  <td className="py-2.5 px-3 text-gray-500">{med.frequency || '—'}</td>
                  <td className="py-2.5 px-3 text-gray-500">{med.route || '—'}</td>
                  <td className="py-2.5 px-3 text-gray-500">{formatDate(med.createdAt)}</td>
                  <td className="py-2.5 px-3">
                    <button
                      type="button"
                      onClick={() => onDiscontinue(med.id)}
                      className="text-xs font-semibold text-red-600 border border-red-200 rounded-full px-3 py-1 hover:bg-red-50 transition"
                    >
                      Discontinue
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {discontinued.length > 0 && (
        <div className="mt-5 pt-4 border-t border-gray-100">
          <button
            type="button"
            onClick={() => setShowDiscontinued((v) => !v)}
            className="text-xs font-semibold text-gray-400 hover:text-gray-600 transition"
          >
            {showDiscontinued ? 'Hide' : 'Show'} discontinued medications ({discontinued.length})
          </button>
          {showDiscontinued && (
            <div className="mt-3 space-y-1.5">
              {discontinued.map((med) => (
                <div
                  key={med.id}
                  className="flex items-center justify-between text-xs text-gray-400 bg-surface rounded-lg px-3 py-2"
                >
                  <span>
                    {med.drugName} {med.dosage ? `· ${med.dosage}` : ''}
                  </span>
                  <span>{formatDate(med.createdAt)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
