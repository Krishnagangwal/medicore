function computeAge(dob) {
  if (!dob) return null
  const birth = new Date(dob)
  if (Number.isNaN(birth.getTime())) return null
  const now = new Date()
  let age = now.getFullYear() - birth.getFullYear()
  const m = now.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age -= 1
  return age
}

function formatDuration(admittedAt) {
  if (!admittedAt) return '—'
  const diffMs = Date.now() - new Date(admittedAt).getTime()
  const days = Math.floor(diffMs / (24 * 60 * 60 * 1000))
  const hours = Math.floor((diffMs % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000))
  const parts = []
  if (days > 0) parts.push(`${days} day${days === 1 ? '' : 's'}`)
  parts.push(`${hours} hour${hours === 1 ? '' : 's'}`)
  return parts.join(', ')
}

export default function OverviewTab({ encounter, patient }) {
  const age = computeAge(patient.dob)
  const chronicConditions = patient.chronicConditions || []
  const allergies = patient.allergies || []

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-white rounded-2xl shadow-sm p-5">
        <h3 className="font-bold text-gray-800 mb-4">Patient Info</h3>
        <dl className="space-y-2.5 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500">Full Name</dt>
            <dd className="text-gray-800 font-medium">{patient.fullName || '—'}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Date of Birth</dt>
            <dd className="text-gray-800 font-medium">
              {patient.dob ? new Date(patient.dob).toLocaleDateString() : '—'}
              {age !== null ? ` (${age} yrs)` : ''}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Gender</dt>
            <dd className="text-gray-800 font-medium capitalize">{patient.gender || '—'}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Blood Type</dt>
            <dd className="text-gray-800 font-medium">{patient.bloodType || '—'}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Contact Phone</dt>
            <dd className="text-gray-800 font-medium">{patient.contactPhone || '—'}</dd>
          </div>
        </dl>

        <div className="mt-4">
          <p className="text-xs font-semibold text-gray-500 mb-1.5">Chronic Conditions</p>
          {chronicConditions.length === 0 ? (
            <p className="text-sm text-gray-400">None recorded</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {chronicConditions.map((c) => (
                <span key={c} className="text-xs font-medium bg-surface text-gray-700 rounded-full px-2.5 py-1">
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="mt-4">
          <p className="text-xs font-semibold text-gray-500 mb-1.5">Allergies</p>
          {allergies.length === 0 ? (
            <p className="text-sm text-gray-400">None recorded</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {allergies.map((a) => (
                <span
                  key={typeof a === 'string' ? a : JSON.stringify(a)}
                  className="text-xs font-medium bg-red-50 text-red-600 rounded-full px-2.5 py-1"
                >
                  {typeof a === 'string' ? a : a.name || JSON.stringify(a)}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm p-5">
        <h3 className="font-bold text-gray-800 mb-4">Encounter Info</h3>
        <dl className="space-y-2.5 text-sm">
          <div className="flex justify-between items-center">
            <dt className="text-gray-500">Status</dt>
            <dd>
              <span
                className={`text-xs font-semibold rounded-full px-2 py-0.5 ${
                  encounter.status === 'ACTIVE' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-500'
                }`}
              >
                {encounter.status}
              </span>
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Admitted</dt>
            <dd className="text-gray-800 font-medium">
              {encounter.admittedAt ? new Date(encounter.admittedAt).toLocaleString() : '—'}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Ward / Bed</dt>
            <dd className="text-gray-800 font-medium">
              {encounter.ward || '—'} / {encounter.bedId || '—'}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Treating Doctor</dt>
            <dd className="text-gray-800 font-medium">
              {encounter.treatingDoctorId ? `Dr. ${encounter.treatingDoctorId.slice(0, 8)}` : '—'}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Duration</dt>
            <dd className="text-gray-800 font-medium">{formatDuration(encounter.admittedAt)}</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
