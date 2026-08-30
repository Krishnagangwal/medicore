import { useEffect, useState } from 'react'
import { XMarkIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { useAuth } from '../../context/AuthContext.jsx'
import { createPatient, createEncounter, getHospitalStaff } from '../../services/api.js'

const GENDERS = ['Male', 'Female', 'Other']
const BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

export default function AdmitPatientModal({ onClose, onSuccess }) {
  const { user } = useAuth()

  const [fullName, setFullName] = useState('')
  const [dob, setDob] = useState('')
  const [gender, setGender] = useState('')
  const [bloodType, setBloodType] = useState('')
  const [contactPhone, setContactPhone] = useState('')
  const [ward, setWard] = useState(user?.ward || '')
  const [bedId, setBedId] = useState('')
  const [treatingDoctorId, setTreatingDoctorId] = useState('')

  const [doctors, setDoctors] = useState([])

  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!user?.hospitalId) return
    getHospitalStaff(user.hospitalId, 'DOCTOR')
      .then(({ data }) => setDoctors(data.data))
      .catch(() => {
        // Non-critical — treating doctor is optional, dropdown just stays empty.
      })
  }, [user?.hospitalId])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!fullName.trim() || !dob || !gender) {
      setError('Full name, date of birth, and gender are required.')
      return
    }

    setLoading(true)
    try {
      const { data: patientRes } = await createPatient({
        fullName: fullName.trim(),
        dob,
        gender,
        bloodType: bloodType || undefined,
        contactPhone: contactPhone.trim() || undefined,
      })

      await createEncounter({
        patientId: patientRes.data.id,
        ward: ward.trim() || undefined,
        bedId: bedId.trim() || undefined,
        treatingDoctorId: treatingDoctorId || undefined,
      })

      setSuccess(true)
      setTimeout(() => {
        onSuccess?.()
        onClose()
      }, 1000)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to admit patient. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-[480px] max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between p-5 border-b border-gray-100">
          <h2 className="font-bold text-gray-800">Admit New Patient</h2>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Close">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {success ? (
          <div className="py-12 flex flex-col items-center gap-2">
            <CheckCircleIcon className="w-12 h-12 text-accent" />
            <p className="text-sm text-gray-600">Patient admitted successfully</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-5 space-y-4">
            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2">
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Full Name *</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Date of Birth *</label>
                <input
                  type="date"
                  value={dob}
                  onChange={(e) => setDob(e.target.value)}
                  required
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Gender *</label>
                <select
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  required
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  <option value="">Select</option>
                  {GENDERS.map((g) => (
                    <option key={g} value={g}>
                      {g}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Blood Type</label>
                <select
                  value={bloodType}
                  onChange={(e) => setBloodType(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  <option value="">Unknown</option>
                  {BLOOD_TYPES.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Contact Phone</label>
                <input
                  type="tel"
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Ward</label>
                <input
                  type="text"
                  value={ward}
                  onChange={(e) => setWard(e.target.value)}
                  placeholder="e.g. ICU-B"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Bed ID</label>
                <input
                  type="text"
                  value={bedId}
                  onChange={(e) => setBedId(e.target.value)}
                  placeholder="e.g. B4"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Treating Doctor</label>
              <select
                value={treatingDoctorId}
                onChange={(e) => setTreatingDoctorId(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="">Unassigned</option>
                {doctors.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.fullName}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition disabled:opacity-60"
            >
              {loading ? 'Admitting...' : 'Admit Patient'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
