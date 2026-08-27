import { ExclamationTriangleIcon } from '@heroicons/react/24/solid'

function severityClass(severity) {
  if (severity === 'major') return 'bg-red-100 text-red-600'
  if (severity === 'moderate') return 'bg-orange-100 text-orange-600'
  return 'bg-yellow-100 text-yellow-600'
}

export default function DrugInteractionAlert({ alert, onDismiss }) {
  const interactions = alert?.interactions || []

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-[60]">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-[520px] max-h-[90vh] overflow-y-auto">
        <div className="p-5 border-b border-gray-100 flex items-center gap-2.5">
          <ExclamationTriangleIcon className="w-6 h-6 text-red-500 shrink-0" />
          <h2 className="font-bold text-gray-800">Drug Interaction Detected</h2>
        </div>

        <div className="p-5 space-y-4">
          {interactions.map((interaction, idx) => (
            <div key={`${interaction.drug_a}-${interaction.drug_b}-${idx}`} className="rounded-lg border border-red-100 bg-red-50/50 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="font-bold text-sm text-gray-800">
                  {interaction.drug_a} + {interaction.drug_b}
                </p>
                <span
                  className={`text-[11px] font-semibold rounded-full px-2 py-0.5 shrink-0 ${severityClass(
                    interaction.severity,
                  )}`}
                >
                  {interaction.severity?.toUpperCase()}
                </span>
              </div>
              {interaction.mechanism && <p className="text-xs italic text-gray-500 mt-1.5">{interaction.mechanism}</p>}
              {interaction.recommendation && (
                <p className="text-xs font-semibold text-gray-700 mt-1.5">{interaction.recommendation}</p>
              )}
            </div>
          ))}
        </div>

        <div className="p-5 border-t border-gray-100 flex justify-end">
          <button
            type="button"
            onClick={onDismiss}
            className="bg-primary text-white text-sm font-semibold rounded-lg px-5 py-2.5 hover:bg-primary/90 transition"
          >
            Acknowledge
          </button>
        </div>
      </div>
    </div>
  )
}
