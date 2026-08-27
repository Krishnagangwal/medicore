import PatientRiskRow from './PatientRiskRow.jsx'

// Encounters with an active alert first, then by risk score descending,
// then encounters with no prediction yet last.
function sortEncounters(encounters) {
  return [...encounters].sort((a, b) => {
    const aAlert = a.latestRisk?.alertTriggered ? 1 : 0
    const bAlert = b.latestRisk?.alertTriggered ? 1 : 0
    if (aAlert !== bAlert) return bAlert - aAlert

    const aScore = a.latestRisk?.risk_score
    const bScore = b.latestRisk?.risk_score
    const aHas = aScore !== undefined && aScore !== null
    const bHas = bScore !== undefined && bScore !== null
    if (aHas && !bHas) return -1
    if (!aHas && bHas) return 1
    if (aHas && bHas) return bScore - aScore
    return 0
  })
}

export default function PatientRiskQueue({ encounters, onSelectPatient, onLogVitals, selectedId, loading }) {
  const sorted = sortEncounters(encounters)

  return (
    <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="font-bold text-gray-800">Patient Risk Queue</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="text-xs uppercase text-gray-400 border-b border-gray-100">
              <th className="py-2 px-4 font-medium">Patient</th>
              <th className="py-2 px-4 font-medium">Ward/Bed</th>
              <th className="py-2 px-4 font-medium">Risk Score</th>
              <th className="py-2 px-4 font-medium">Risk Level</th>
              <th className="py-2 px-4 font-medium">SOFA</th>
              <th className="py-2 px-4 font-medium">Trend</th>
              <th className="py-2 px-4 font-medium">Last Vitals</th>
              <th className="py-2 px-4 font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-sm text-gray-400">
                  Loading patients...
                </td>
              </tr>
            ) : sorted.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-sm text-gray-400">
                  No active patients in ICU
                </td>
              </tr>
            ) : (
              sorted.map((encounter) => (
                <PatientRiskRow
                  key={encounter.id}
                  encounter={encounter}
                  isSelected={selectedId === encounter.id}
                  onSelect={onSelectPatient}
                  onLogVitals={onLogVitals}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
