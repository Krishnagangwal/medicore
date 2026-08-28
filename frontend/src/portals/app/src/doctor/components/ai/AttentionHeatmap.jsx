import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, CartesianGrid } from 'recharts'

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const { hour, attention, vitals } = payload[0].payload
  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-100 px-3 py-2 text-xs">
      <p className="font-semibold text-gray-800">Hour {hour}</p>
      <p className="text-gray-500">attention {attention.toFixed(3)}</p>
      {vitals && (
        <p className="text-gray-500">
          HR={vitals.hr ?? '—'}, SpO2={vitals.o2sat ?? '—'}
        </p>
      )}
    </div>
  )
}

export default function AttentionHeatmap({ sepsisResult }) {
  const weights = sepsisResult?.attention_weights || []
  const peakHour = sepsisResult?.attention_peak_hour
  const topHours = sepsisResult?.top_attended_hours || []
  const topIndexSet = new Set(topHours.map((h) => h.hour_index))

  if (weights.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-sm p-5">
        <h3 className="font-bold text-gray-800">Temporal Attention</h3>
        <p className="text-sm text-gray-400 mt-3">No attention data available for this prediction.</p>
      </div>
    )
  }

  // attention_peak_hour / hour_index are 0-based array positions; the chart
  // displays them as hour 1-24 per the design brief.
  const chartData = weights.map((w, idx) => ({
    hour: idx + 1,
    attention: w,
    vitals: topHours.find((h) => h.hour_index === idx)?.vitals || null,
    isPeak: idx === peakHour,
    isTop: topIndexSet.has(idx),
  }))

  const peakVitals = topHours.find((h) => h.hour_index === peakHour)?.vitals

  return (
    <div className="bg-white rounded-2xl shadow-sm p-5">
      <h3 className="font-bold text-gray-800">Temporal Attention — Which hours drove this prediction</h3>
      <p className="text-xs text-gray-500 mt-1 mb-4">Higher bars = more influential for the risk score</p>

      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
          <XAxis dataKey="hour" tick={{ fontSize: 11 }} interval={1} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="attention" radius={[3, 3, 0, 0]}>
            {chartData.map((entry) => (
              <Cell key={entry.hour} fill={entry.isPeak ? '#ef4444' : entry.isTop ? '#f97316' : '#d1d5db'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {peakHour !== undefined && peakHour !== null && (
        <p className="text-sm text-gray-600 mt-3">
          Peak attention at hour {peakHour + 1}
          {peakVitals && ` (HR: ${peakVitals.hr ?? '—'}, SpO2: ${peakVitals.o2sat ?? '—'})`}
        </p>
      )}

      <p className="text-xs text-gray-400 mt-2">
        Attention weights show which time steps the model weighted most heavily when computing this risk score.
        High attention on recent hours indicates acute change.
      </p>
    </div>
  )
}
