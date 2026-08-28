import RiskBadge from './RiskBadge.jsx'

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

function TrendIndicator({ trend }) {
  if (trend === 'worsening') return <span className="text-red-600 font-semibold">↑ worsening</span>
  if (trend === 'improving') return <span className="text-green-600 font-semibold">↓ improving</span>
  if (trend === 'stable') return <span className="text-gray-500">→ stable</span>
  return <span className="text-gray-400">—</span>
}

function riskScoreColor(risk) {
  if (!risk) return 'text-gray-400'
  if (risk.risk_level === 'high' || risk.risk_score > 0.85) return 'text-red-600'
  if (risk.risk_level === 'medium') return 'text-yellow-600'
  if (risk.risk_level === 'low') return 'text-green-600'
  return 'text-gray-600'
}

export default function PatientRiskRow({ encounter, onSelect, onLogVitals, isSelected }) {
  const risk = encounter.latestRisk
  const hasScore = risk?.risk_score !== undefined && risk?.risk_score !== null

  return (
    <tr
      onClick={() => onSelect(encounter)}
      className={`cursor-pointer border-b border-gray-100 last:border-0 hover:bg-surface/60 transition ${
        isSelected ? 'bg-surface/70' : ''
      }`}
    >
      <td className="py-3 px-4">
        <p className="font-medium text-gray-800">{encounter.patientName}</p>
        <p className="text-xs text-gray-400">{encounter.patientCode}</p>
      </td>
      <td className="py-3 px-4 text-sm text-gray-600 whitespace-nowrap">
        {encounter.ward || '—'}
        {encounter.bedId ? ` / ${encounter.bedId}` : ''}
      </td>
      <td className={`py-3 px-4 font-bold ${riskScoreColor(risk)}`}>
        {hasScore ? Number(risk.risk_score).toFixed(2) : '—'}
      </td>
      <td className="py-3 px-4">
        <RiskBadge level={risk?.risk_level} />
      </td>
      <td className="py-3 px-4 text-sm text-gray-600">{risk?.sofa_rounded ?? '—'}</td>
      <td className="py-3 px-4 text-sm">
        <TrendIndicator trend={risk?.trend} />
      </td>
      <td className="py-3 px-4 text-sm text-gray-500 whitespace-nowrap">
        {formatRelativeTime(encounter.lastVitalsAt)}
      </td>
      <td className="py-3 px-4">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onLogVitals(encounter)
          }}
          className="text-xs font-semibold bg-primary text-white rounded-full px-3 py-1.5 hover:bg-primary/90 transition whitespace-nowrap"
        >
          Log Vitals
        </button>
      </td>
    </tr>
  )
}
