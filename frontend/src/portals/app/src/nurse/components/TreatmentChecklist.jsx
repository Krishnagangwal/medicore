import { useEffect, useState } from 'react'

// Surviving Sepsis Campaign "Sepsis Six" hour-1 bundle.
const BUNDLE_ITEMS = [
  { key: 'lactate', label: 'Measure serum lactate' },
  { key: 'bloodCultures', label: 'Obtain blood cultures before antibiotics' },
  { key: 'antibiotics', label: 'Administer broad-spectrum antibiotics' },
  { key: 'fluids', label: 'Begin 30 mL/kg crystalloid fluid resuscitation' },
  { key: 'vasopressors', label: 'Start vasopressors if hypotensive after fluids' },
  { key: 'remeasureLactate', label: 'Re-measure lactate if initial was elevated' },
]

function storageKey(encounterId) {
  return `medicore_bundle_${encounterId}`
}

export default function TreatmentChecklist({ encounterId }) {
  const [checked, setChecked] = useState({})

  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey(encounterId))
      setChecked(stored ? JSON.parse(stored) : {})
    } catch {
      setChecked({})
    }
  }, [encounterId])

  const toggle = (key) => {
    setChecked((prev) => {
      const next = { ...prev, [key]: !prev[key] }
      try {
        localStorage.setItem(storageKey(encounterId), JSON.stringify(next))
      } catch {
        // localStorage unavailable — checklist state just won't persist
      }
      return next
    })
  }

  const completedCount = BUNDLE_ITEMS.filter((item) => checked[item.key]).length
  const percent = Math.round((completedCount / BUNDLE_ITEMS.length) * 100)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500">Sepsis Six Bundle Compliance</p>
        <p className="text-sm font-semibold text-primary">
          {completedCount}/{BUNDLE_ITEMS.length} ({percent}%)
        </p>
      </div>
      <div className="w-full h-2 bg-surface rounded-full overflow-hidden mb-4">
        <div className="h-full bg-accent transition-all" style={{ width: `${percent}%` }} />
      </div>
      <ul className="space-y-2">
        {BUNDLE_ITEMS.map((item) => (
          <li key={item.key}>
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={Boolean(checked[item.key])}
                onChange={() => toggle(item.key)}
                className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-accent"
              />
              <span className={checked[item.key] ? 'line-through text-gray-400' : ''}>{item.label}</span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  )
}
