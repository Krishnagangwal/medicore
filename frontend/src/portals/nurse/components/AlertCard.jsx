import { useEffect, useState } from 'react'
import RiskBadge from './RiskBadge.jsx'

function formatTime(dateStr) {
  const date = dateStr ? new Date(dateStr) : new Date()
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function AlertCard({ alert, isNewest = false }) {
  const [pulsing, setPulsing] = useState(isNewest)

  useEffect(() => {
    if (!isNewest) return
    setPulsing(true)
    const timer = setTimeout(() => setPulsing(false), 3000)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isNewest, alert.receivedAt])

  const borderColor =
    alert.risk_score > 0.8 ? 'border-red-500' : alert.risk_score > 0.65 ? 'border-orange-500' : 'border-gray-300'
  const bg = alert.risk_score > 0.8 ? 'bg-red-50' : 'bg-orange-50'

  return (
    <div className={`rounded-xl border-l-4 ${borderColor} ${bg} p-3 ${pulsing ? 'animate-pulse' : ''}`}>
      <div className="flex items-start justify-between gap-2">
        <p className="font-semibold text-gray-800 text-sm">{alert.patient_name}</p>
        <span className="text-[11px] text-gray-400 whitespace-nowrap">{formatTime(alert.receivedAt)}</span>
      </div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-lg font-bold text-gray-800">
          {alert.risk_score !== undefined && alert.risk_score !== null ? Number(alert.risk_score).toFixed(2) : '—'}
        </span>
        <RiskBadge level={alert.risk_level} />
      </div>
      <p className="text-xs text-gray-600 mt-1">SOFA: {alert.sofa_rounded ?? '—'}</p>
      {alert.alert_text && <p className="text-xs italic text-gray-500 mt-1">{alert.alert_text}</p>}
      <p className="text-[11px] text-gray-400 mt-1">
        {alert.ward || '—'}
        {alert.bed_id ? ` / ${alert.bed_id}` : ''}
      </p>
    </div>
  )
}
