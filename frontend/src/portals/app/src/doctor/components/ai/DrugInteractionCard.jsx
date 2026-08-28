import { ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

function severityClass(severity) {
  if (severity === 'major') return 'bg-red-100 text-red-600'
  if (severity === 'moderate') return 'bg-orange-100 text-orange-600'
  return 'bg-yellow-100 text-yellow-600'
}

export default function DrugInteractionCard({ drugInteraction }) {
  const result = drugInteraction?.result
  const interactions = result?.interactions || []

  return (
    <div className="bg-white rounded-2xl shadow-sm p-5">
      <h3 className="font-bold text-gray-800 mb-3">Drug Interaction Safety</h3>

      {!result || result.interaction_count === 0 ? (
        <div className="flex items-center gap-2 text-green-600">
          <CheckCircleIcon className="w-5 h-5" />
          <p className="text-sm">No interactions detected</p>
        </div>
      ) : (
        <div className="space-y-3">
          {interactions.map((interaction, idx) => (
            <div key={`${interaction.drug_a}-${interaction.drug_b}-${idx}`} className="rounded-lg border border-red-100 bg-red-50/50 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <ExclamationTriangleIcon className="w-4 h-4 text-red-500 shrink-0" />
                  <p className="font-semibold text-sm text-gray-800">
                    {interaction.drug_a} + {interaction.drug_b}
                  </p>
                </div>
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
                <p className="text-xs text-gray-700 font-medium mt-1">{interaction.recommendation}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
