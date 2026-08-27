function severityInfo(sofa) {
  if (sofa === null || sofa === undefined) return { label: '—', className: 'bg-gray-100 text-gray-500' }
  if (sofa <= 1) return { label: 'Normal', className: 'bg-green-100 text-green-600' }
  if (sofa <= 3) return { label: 'Mild dysfunction', className: 'bg-yellow-100 text-yellow-600' }
  if (sofa <= 5) return { label: 'Moderate dysfunction', className: 'bg-orange-100 text-orange-600' }
  return { label: 'Severe dysfunction', className: 'bg-red-100 text-red-600' }
}

function TrendBadge({ trend }) {
  if (trend === 'worsening') return <span className="text-red-600 font-semibold text-sm">↑ Worsening</span>
  if (trend === 'improving') return <span className="text-green-600 font-semibold text-sm">↓ Improving</span>
  if (trend === 'stable') return <span className="text-gray-500 font-semibold text-sm">→ Stable</span>
  return <span className="text-gray-400 text-sm">—</span>
}

export default function SofaCard({ sepsisResult }) {
  const severity = severityInfo(sepsisResult?.sofa_rounded)

  return (
    <div className="bg-white rounded-2xl shadow-sm p-5">
      <h3 className="font-bold text-gray-800 mb-3">SOFA Score</h3>
      <div className="flex items-center gap-3">
        <span className="text-4xl font-bold text-gray-800">{sepsisResult?.sofa_rounded ?? '—'}</span>
        <span className={`text-xs font-semibold rounded-full px-2.5 py-1 ${severity.className}`}>
          {severity.label}
        </span>
      </div>
      <div className="mt-2">
        <TrendBadge trend={sepsisResult?.trend} />
      </div>
      <p className="text-xs text-gray-400 mt-3">
        SOFA auto-computed from vital signs. Includes respiratory and cardiovascular components.
      </p>
    </div>
  )
}
