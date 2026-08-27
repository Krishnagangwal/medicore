import { useMemo } from 'react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'
import { HeartIcon, EyeDropperIcon, FireIcon, BoltIcon, CloudIcon } from '@heroicons/react/24/outline'

const LINES = [
  { key: 'heartRate', name: 'Heart Rate', color: '#ef4444' },
  { key: 'spo2', name: 'SpO2', color: '#3b82f6' },
  { key: 'systolicBp', name: 'Systolic BP', color: '#8b5cf6' },
  { key: 'temperature', name: 'Temperature', color: '#f97316' },
  { key: 'respiratoryRate', name: 'Resp Rate', color: '#22c55e' },
]

function formatTime(dateStr) {
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function VitalSummaryCard({ icon: Icon, label, value, unit, color }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm p-4 text-center">
      <Icon className={`w-5 h-5 mx-auto mb-1.5 ${color}`} />
      <p className="text-lg font-bold text-gray-800">{value ?? '—'}</p>
      <p className="text-[11px] text-gray-400">
        {label} {value !== null && value !== undefined ? unit : ''}
      </p>
    </div>
  )
}

export default function VitalsTab({ vitals }) {
  const chartData = useMemo(() => vitals.map((v) => ({ ...v, time: formatTime(v.recordedAt) })), [vitals])
  const latest = vitals[vitals.length - 1]

  if (vitals.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-sm p-10 text-center text-sm text-gray-400">
        No vitals recorded yet
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl shadow-sm p-5">
        <h3 className="font-bold text-gray-800 mb-4">Vital Signs Trend</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="time" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            {LINES.map((line) => (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                name={line.name}
                stroke={line.color}
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {latest && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <VitalSummaryCard icon={HeartIcon} label="HR" value={latest.heartRate} unit="bpm" color="text-red-500" />
          <VitalSummaryCard icon={EyeDropperIcon} label="SpO2" value={latest.spo2} unit="%" color="text-blue-500" />
          <VitalSummaryCard icon={FireIcon} label="Temp" value={latest.temperature} unit="°C" color="text-orange-500" />
          <VitalSummaryCard icon={BoltIcon} label="SBP" value={latest.systolicBp} unit="mmHg" color="text-purple-500" />
          <VitalSummaryCard icon={CloudIcon} label="RR" value={latest.respiratoryRate} unit="/min" color="text-green-500" />
        </div>
      )}
    </div>
  )
}
