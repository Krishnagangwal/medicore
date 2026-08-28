import RiskBadge from '../RiskBadge.jsx'

export default function SepsisRiskCard({ sepsis }) {
  const result = sepsis?.result
  if (!result) return null

  const scoreColor =
    result.risk_score > 0.65 ? 'text-red-600' : result.risk_score > 0.4 ? 'text-yellow-600' : 'text-green-600'

  return (
    <div className="bg-white rounded-2xl shadow-sm p-5">
      <div className="flex items-start justify-between">
        <h3 className="font-bold text-gray-800">Sepsis Risk</h3>
        {result.alert && (
          <span className="flex items-center gap-1.5 text-xs font-semibold text-red-600">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            ALERT ACTIVE
          </span>
        )}
      </div>

      <div className="flex items-center gap-3 mt-3">
        <span className={`text-4xl font-bold ${scoreColor}`}>{Number(result.risk_score).toFixed(2)}</span>
        <RiskBadge level={result.risk_level} />
      </div>

      {result.alert_text && <p className="text-sm italic text-gray-500 mt-3">{result.alert_text}</p>}

      <p className="text-xs text-gray-400 mt-3">Model response: {sepsis.latency_ms ?? '—'}ms</p>
    </div>
  )
}
