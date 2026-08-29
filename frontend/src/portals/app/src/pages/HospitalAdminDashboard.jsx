import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { getMyStaff, inviteStaff, deactivateStaff } from '../services/api.js'

function CopyableCode({ value }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard API unavailable — the code is still visible to copy manually
    }
  }
  return (
    <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 font-mono text-sm">
      <code className="flex-1 break-all">{value}</code>
      <button
        type="button"
        onClick={handleCopy}
        className="shrink-0 text-xs font-semibold text-primary hover:underline"
      >
        {copied ? 'Copied!' : 'Copy'}
      </button>
    </div>
  )
}

function StaffStatusBadge({ isActive }) {
  return (
    <span
      className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
        isActive ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-500'
      }`}
    >
      {isActive ? 'Active' : 'Inactive'}
    </span>
  )
}

function StaffSection({ title, members, onDeactivate }) {
  if (members.length === 0) return null
  return (
    <div className="bg-white rounded-2xl shadow-sm overflow-hidden mb-6">
      <h3 className="px-5 py-3 font-semibold text-gray-800 border-b border-gray-100">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 uppercase border-b border-gray-100">
              <th className="px-5 py-2 font-medium">Full Name</th>
              <th className="px-5 py-2 font-medium">Email</th>
              <th className="px-5 py-2 font-medium">Ward</th>
              <th className="px-5 py-2 font-medium">Status</th>
              <th className="px-5 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id} className="border-b border-gray-50 last:border-0">
                <td className="px-5 py-3 font-medium text-gray-800">{m.fullName}</td>
                <td className="px-5 py-3 text-gray-600">{m.email}</td>
                <td className="px-5 py-3 text-gray-500">{m.ward || '—'}</td>
                <td className="px-5 py-3">
                  <StaffStatusBadge isActive={m.isActive} />
                </td>
                <td className="px-5 py-3">
                  {m.isActive && (
                    <button
                      type="button"
                      onClick={() => onDeactivate(m.id, m.fullName)}
                      className="text-xs font-semibold text-red-500 hover:underline"
                    >
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function InviteStaffForm() {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('NURSE')
  const [ward, setWard] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await inviteStaff({
        fullName: fullName.trim(),
        email: email.trim(),
        role,
        ward: ward.trim() || undefined,
      })
      setResult({ email: data.user.email, tempPassword: data.tempPassword })
      setFullName('')
      setEmail('')
      setRole('NURSE')
      setWard('')
    } catch (err) {
      if (err.response?.status === 409) {
        setError('This email is already registered')
      } else {
        setError('Something went wrong')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg">
      {result && (
        <div className="mb-5 rounded-lg bg-green-50 border border-green-200 p-4">
          <p className="font-semibold text-green-800 mb-2">Staff invited successfully</p>
          <p className="text-sm text-green-700 mb-2">Temporary password:</p>
          <CopyableCode value={result.tempPassword} />
          <p className="text-sm text-green-700 mt-2">An email has been sent to {result.email}</p>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent bg-white"
          >
            <option value="NURSE">Nurse</option>
            <option value="DOCTOR">Doctor</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Ward <span className="text-gray-400">(optional)</span>
          </label>
          <input
            type="text"
            value={ward}
            onChange={(e) => setWard(e.target.value)}
            placeholder="e.g. ICU-B"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition disabled:opacity-60"
        >
          {loading ? 'Inviting...' : 'Invite Staff'}
        </button>
      </form>
    </div>
  )
}

export default function HospitalAdminDashboard() {
  const { user, logout } = useAuth()
  const [tab, setTab] = useState('staff')
  const [staff, setStaff] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchStaff = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await getMyStaff()
      setStaff(data.data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStaff()
  }, [fetchStaff])

  const handleDeactivate = async (userId, fullName) => {
    if (!window.confirm(`Deactivate ${fullName}? They will no longer be able to log in.`)) return
    await deactivateStaff(userId)
    fetchStaff()
  }

  const nurses = staff.filter((s) => s.role === 'NURSE')
  const doctors = staff.filter((s) => s.role === 'DOCTOR')

  return (
    <div className="min-h-screen bg-surface">
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div>
            <h1 className="font-bold text-lg text-gray-900">
              Hospital Admin — {user?.hospitalName || 'your hospital'}
            </h1>
            <p className="text-sm text-gray-500">{user?.email}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="px-4 py-2 rounded-lg text-sm font-semibold border-2 border-primary text-primary hover:bg-primary/5 transition"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-6 border-b border-gray-200 mb-6">
          {[
            { key: 'staff', label: 'Our Staff' },
            { key: 'invite', label: 'Invite Staff' },
          ].map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`pb-3 text-sm font-semibold border-b-2 transition ${
                tab === t.key ? 'border-primary text-primary' : 'border-transparent text-gray-400 hover:text-gray-600'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'staff' &&
          (loading ? (
            <p className="text-sm text-gray-400">Loading...</p>
          ) : staff.length === 0 ? (
            <p className="text-sm text-gray-400">No staff yet — invite your first nurse or doctor.</p>
          ) : (
            <>
              <StaffSection title="Nurses" members={nurses} onDeactivate={handleDeactivate} />
              <StaffSection title="Doctors" members={doctors} onDeactivate={handleDeactivate} />
            </>
          ))}

        {tab === 'invite' && <InviteStaffForm />}
      </main>
    </div>
  )
}
