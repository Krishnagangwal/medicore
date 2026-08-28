import { useMemo, useState } from 'react'
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import PatientSidebarRow from './PatientSidebarRow.jsx'

// High risk first, then most recently admitted; encounters with no
// prediction yet sort after ones with a known score.
function sortEncounters(encounters) {
  return [...encounters].sort((a, b) => {
    const aScore = a.latestRisk?.risk_score
    const bScore = b.latestRisk?.risk_score
    const aHas = aScore !== undefined && aScore !== null
    const bHas = bScore !== undefined && bScore !== null
    if (aHas && !bHas) return -1
    if (!aHas && bHas) return 1
    if (aHas && bHas && aScore !== bScore) return bScore - aScore
    return new Date(b.admittedAt) - new Date(a.admittedAt)
  })
}

export default function PatientSidebar({ encounters, selectedId, onSelect, loading, open = false, onClose }) {
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    const sorted = sortEncounters(encounters)
    if (!search.trim()) return sorted
    const q = search.trim().toLowerCase()
    return sorted.filter((e) => e.patientName?.toLowerCase().includes(q))
  }, [encounters, search])

  const handleSelect = (id) => {
    onSelect(id)
    // On mobile this is an off-canvas drawer over the content — close it
    // after picking a patient so the detail view is visible. On desktop
    // (md+) the sidebar ignores `open`/onClose, so this is a no-op there.
    onClose?.()
  }

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-30 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-[280px] shrink-0 bg-white border-r border-gray-100 flex flex-col h-full transition-transform duration-200 ease-out md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-gray-800">Active Patients</h2>
            <span className="text-xs font-semibold bg-surface text-gray-600 rounded-full px-2 py-0.5">
              {encounters.length}
            </span>
          </div>
          <div className="relative">
            <MagnifyingGlassIcon className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search patients..."
              className="w-full rounded-lg border border-gray-200 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loading ? (
            <p className="text-center text-sm text-gray-400 py-8">Loading patients...</p>
          ) : filtered.length === 0 ? (
            <p className="text-center text-sm text-gray-400 py-8">No patients found</p>
          ) : (
            filtered.map((encounter) => (
              <PatientSidebarRow
                key={encounter.id}
                encounter={encounter}
                isSelected={selectedId === encounter.id}
                onClick={() => handleSelect(encounter.id)}
              />
            ))
          )}
        </div>
      </aside>
    </>
  )
}
