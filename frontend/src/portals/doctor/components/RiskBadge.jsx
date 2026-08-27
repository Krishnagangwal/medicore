const LEVELS = {
  critical: { label: 'CRITICAL', className: 'bg-red-100 text-red-600 border border-red-200' },
  high: { label: 'HIGH', className: 'bg-orange-100 text-orange-600' },
  medium: { label: 'MEDIUM', className: 'bg-yellow-100 text-yellow-600' },
  low: { label: 'LOW', className: 'bg-green-100 text-green-600' },
}

export default function RiskBadge({ level }) {
  const config = LEVELS[level] || { label: 'PENDING', className: 'bg-gray-100 text-gray-500' }

  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${config.className}`}>
      {config.label}
    </span>
  )
}
