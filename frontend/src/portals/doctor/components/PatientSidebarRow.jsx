import RiskBadge from './RiskBadge.jsx'

function formatRelativeTime(dateStr) {
  if (!dateStr) return null
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.round(diffMs / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} hr ago`
  return `${Math.round(hours / 24)} d ago`
}

export default function PatientSidebarRow({ encounter, isSelected, onClick }) {
  const risk = encounter.latestRisk
  const updated = formatRelativeTime(risk?.predictedAt)

  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left rounded-xl p-3 transition border-l-4 ${
        isSelected ? 'border-primary bg-primary/5' : 'border-transparent hover:bg-surface'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold text-gray-800 truncate">{encounter.patientName}</p>
          <p className="text-xs text-gray-400">{encounter.patientCode}</p>
        </div>
        {risk && <RiskBadge level={risk.risk_level} />}
      </div>
      <p className="text-xs text-gray-500 mt-1.5">
        {encounter.ward || '—'}
        {encounter.bedId ? ` · ${encounter.bedId}` : ''}
      </p>
      <p className="text-[11px] text-gray-400 mt-0.5">{updated ? `Updated ${updated}` : 'No AI assessment yet'}</p>
    </button>
  )
}
