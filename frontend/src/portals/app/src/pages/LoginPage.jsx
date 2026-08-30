import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PlusIcon, EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'
import { useAuth } from '../context/AuthContext.jsx'
import { getHospitals, getHospitalStaff } from '../services/api.js'

const ROLES = [
  { value: 'NURSE', label: 'Nurse' },
  { value: 'DOCTOR', label: 'Doctor' },
  { value: 'ADMIN', label: 'Admin' },
]

// Kept in sync with the same-named function in App.jsx (duplicated rather
// than imported since they're both small and App.jsx doesn't export it) —
// out of sync once already: ADMIN login worked but silently fell through
// to the "coming soon" message here because this copy didn't know about
// ADMIN/SUPER_ADMIN yet after App.jsx's was updated to add /admin and
// /superadmin routes.
function dashboardPathForRole(role) {
  if (role === 'NURSE') return '/nurse/dashboard'
  if (role === 'DOCTOR') return '/doctor'
  if (role === 'SUPER_ADMIN') return '/superadmin'
  if (role === 'ADMIN') return '/admin'
  return null
}

function StepDots({ step }) {
  return (
    <div className="flex justify-center gap-2 mb-6">
      {[1, 2, 3].map((n) => (
        <span
          key={n}
          className={`h-2 rounded-full transition-all ${
            n === step ? 'w-6 bg-primary' : 'w-2 bg-gray-200'
          }`}
        />
      ))}
    </div>
  )
}

export default function LoginPage() {
  const [step, setStep] = useState(1)

  const [hospitals, setHospitals] = useState([])
  const [hospitalsLoading, setHospitalsLoading] = useState(true)
  const [hospitalId, setHospitalId] = useState('')

  const [role, setRole] = useState(null)
  const [staff, setStaff] = useState([])
  const [staffLoading, setStaffLoading] = useState(false)
  const [staffId, setStaffId] = useState('')
  const [adminEmail, setAdminEmail] = useState('')

  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingAdminNotice, setPendingAdminNotice] = useState(false)

  // SUPER_ADMIN has no hospital, so the hospital-first wizard below can
  // never reach them — this is a parallel, simplified path out of Step 1.
  const [platformAdminMode, setPlatformAdminMode] = useState(false)
  const [platformEmail, setPlatformEmail] = useState('')
  const [platformPassword, setPlatformPassword] = useState('')

  const { login, logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    getHospitals()
      .then(({ data }) => setHospitals(data.data))
      .catch(() => setError('Failed to load hospitals. Please refresh and try again.'))
      .finally(() => setHospitalsLoading(false))
  }, [])

  const selectedHospital = hospitals.find((h) => h.id === hospitalId)
  const selectedStaff = staff.find((s) => s.id === staffId)

  const handleSelectRole = async (value) => {
    setRole(value)
    setStaffId('')
    setAdminEmail('')
    setError('')
    if (value === 'NURSE' || value === 'DOCTOR') {
      setStaffLoading(true)
      try {
        const { data } = await getHospitalStaff(hospitalId, value)
        setStaff(data.data)
      } catch {
        setError('Failed to load staff list. Please try again.')
      } finally {
        setStaffLoading(false)
      }
    }
  }

  const canContinueStep2 =
    role === 'ADMIN' ? adminEmail.trim().length > 0 : role && staffId

  const step3Name =
    role === 'ADMIN' ? adminEmail.trim() : selectedStaff?.fullName || ''

  const handleSubmitPassword = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const credentials =
        role === 'ADMIN'
          ? { email: adminEmail.trim(), password }
          : { userId: staffId, password, hospitalId }
      const { user } = await login(credentials)
      const path = dashboardPathForRole(user.role)
      if (path) {
        navigate(path)
      } else {
        setPendingAdminNotice(true)
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid credentials. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitPlatformAdmin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { user } = await login({ email: platformEmail.trim(), password: platformPassword })
      if (user.role !== 'SUPER_ADMIN') {
        logout()
        setError('This account is not a platform admin.')
        return
      }
      navigate('/superadmin')
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid credentials. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white rounded-[20px] shadow-lg p-8">
        <div className="text-center mb-6">
          <div className="mx-auto mb-3 w-12 h-12 rounded-full bg-primary flex items-center justify-center">
            <PlusIcon className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold text-primary">MediCore</h1>
        </div>

        {!platformAdminMode && <StepDots step={step} />}

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2">
            {error}
          </div>
        )}

        {platformAdminMode ? (
          <form onSubmit={handleSubmitPlatformAdmin} className="space-y-4">
            <p className="text-center font-semibold text-gray-800">Platform Admin Sign In</p>
            <input
              type="email"
              value={platformEmail}
              onChange={(e) => setPlatformEmail(e.target.value)}
              required
              autoFocus
              placeholder="Email"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <input
              type="password"
              value={platformPassword}
              onChange={(e) => setPlatformPassword(e.target.value)}
              required
              placeholder="Password"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition disabled:opacity-60"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
            <button
              type="button"
              onClick={() => {
                setPlatformAdminMode(false)
                setError('')
              }}
              className="w-full text-center text-sm text-gray-500 hover:text-primary transition"
            >
              ← Back
            </button>
          </form>
        ) : pendingAdminNotice ? (
          <div className="text-center py-6">
            <p className="font-semibold text-gray-800 mb-2">Hospital Admin portal — coming soon</p>
            <p className="text-sm text-gray-500 mb-5">
              You're signed in, but the admin dashboard isn't built yet in this app.
            </p>
            <Link to="/" className="text-primary font-semibold hover:underline text-sm">
              Back to home
            </Link>
          </div>
        ) : (
          <>
            {/* STEP 1 — hospital */}
            {step === 1 && (
              <div className="space-y-4">
                <p className="text-center font-semibold text-gray-800">Select your hospital</p>
                <select
                  value={hospitalId}
                  onChange={(e) => setHospitalId(e.target.value)}
                  disabled={hospitalsLoading}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent bg-white disabled:opacity-60"
                >
                  <option value="">{hospitalsLoading ? 'Loading hospitals...' : 'Choose a hospital'}</option>
                  {hospitals.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={!hospitalId}
                  onClick={() => setStep(2)}
                  className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Continue
                </button>
                <p className="text-center text-sm text-gray-500">
                  MediCore platform admin?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setError('')
                      setPlatformAdminMode(true)
                    }}
                    className="text-primary font-semibold hover:underline"
                  >
                    Sign in here →
                  </button>
                </p>
              </div>
            )}

            {/* STEP 2 — role + name */}
            {step === 2 && (
              <div className="space-y-4">
                <p className="text-center font-semibold text-gray-800">Who are you?</p>
                <div className="grid grid-cols-3 gap-2">
                  {ROLES.map((r) => (
                    <button
                      key={r.value}
                      type="button"
                      onClick={() => handleSelectRole(r.value)}
                      className={`rounded-lg border-2 py-3 text-sm font-semibold transition ${
                        role === r.value
                          ? 'border-primary bg-green-50 text-primary'
                          : 'border-gray-200 text-gray-600 hover:border-gray-300'
                      }`}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>

                {(role === 'NURSE' || role === 'DOCTOR') && (
                  <select
                    value={staffId}
                    onChange={(e) => setStaffId(e.target.value)}
                    disabled={staffLoading}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent bg-white disabled:opacity-60"
                  >
                    <option value="">{staffLoading ? 'Loading...' : 'Select your name'}</option>
                    {staff.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.fullName}
                      </option>
                    ))}
                  </select>
                )}

                {role === 'ADMIN' && (
                  <input
                    type="email"
                    value={adminEmail}
                    onChange={(e) => setAdminEmail(e.target.value)}
                    placeholder="Admin email"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                )}

                <button
                  type="button"
                  disabled={!canContinueStep2}
                  onClick={() => setStep(3)}
                  className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Continue
                </button>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="w-full text-center text-sm text-gray-500 hover:text-primary transition"
                >
                  ← Back
                </button>
              </div>
            )}

            {/* STEP 3 — password */}
            {step === 3 && (
              <form onSubmit={handleSubmitPassword} className="space-y-4">
                <div className="text-center">
                  <p className="font-semibold text-gray-800">Welcome, {step3Name}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {selectedHospital?.name} · {ROLES.find((r) => r.value === role)?.label}
                  </p>
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoFocus
                    placeholder="Password"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeSlashIcon className="w-4 h-4" /> : <EyeIcon className="w-4 h-4" />}
                  </button>
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition disabled:opacity-60"
                >
                  {loading ? 'Signing in...' : 'Sign In'}
                </button>
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="w-full text-center text-sm text-gray-500 hover:text-primary transition"
                >
                  ← Back
                </button>
              </form>
            )}
          </>
        )}

        {!platformAdminMode && !pendingAdminNotice && (
          <p className="text-center text-sm text-gray-500 mt-5">
            Hospital not registered yet?{' '}
            <Link to="/request" className="text-primary font-semibold hover:underline">
              Request access
            </Link>
          </p>
        )}
      </div>
    </div>
  )
}
