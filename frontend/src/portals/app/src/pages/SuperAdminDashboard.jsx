import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import {
  getHospitalRequests,
  getAllHospitals,
  approveHospital,
  rejectHospital,
  deleteHospital,
} from '../services/api.js'

function relativeTime(dateStr) {
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min${mins === 1 ? '' : 's'} ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  const days = Math.floor(hours / 24)
  return `${days} day${days === 1 ? '' : 's'} ago`
}

const STATUS_STYLES = {
  approved: 'bg-green-100 text-green-700',
  pending: 'bg-yellow-100 text-yellow-700',
  rejected: 'bg-gray-200 text-gray-600',
}

function StatusBadge({ status }) {
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${STATUS_STYLES[status] || 'bg-gray-100 text-gray-600'}`}>
      {status}
    </span>
  )
}

function HospitalRow({ hospital, onDelete }) {
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)

  const handleConfirmDelete = async () => {
    setBusy(true)
    try {
      await onDelete(hospital.id)
    } finally {
      setBusy(false)
    }
  }

  return (
    <tr className="border-b border-gray-50 last:border-0">
      <td className="px-5 py-3 font-medium text-gray-800">{hospital.name}</td>
      <td className="px-5 py-3 text-gray-600">{hospital.adminEmail}</td>
      <td className="px-5 py-3">
        <StatusBadge status={hospital.status} />
      </td>
      <td className="px-5 py-3 text-gray-500">
        {new Date(hospital.createdAt).toLocaleDateString()}
      </td>
      <td className="px-5 py-3">
        {confirming ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-red-600">Delete all data?</span>
            <button
              type="button"
              onClick={handleConfirmDelete}
              disabled={busy}
              className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-red-500 text-white hover:bg-red-600 transition disabled:opacity-60"
            >
              {busy ? 'Deleting...' : 'Confirm'}
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              disabled={busy}
              className="px-2.5 py-1 rounded-lg text-xs font-semibold text-gray-500 hover:text-gray-700 transition"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="px-2.5 py-1 rounded-lg text-xs font-semibold border-2 border-red-500 text-red-500 hover:bg-red-50 transition"
          >
            Delete
          </button>
        )}
      </td>
    </tr>
  )
}

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

function Toasts({ toasts }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
            t.type === 'success' ? 'bg-green-600' : 'bg-gray-600'
          }`}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}

function PendingRequestCard({ request, tempPassword, onApprove, onReject }) {
  const [rejecting, setRejecting] = useState(false)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  const handleApprove = async () => {
    setBusy(true)
    try {
      await onApprove(request.id)
    } finally {
      setBusy(false)
    }
  }

  const handleConfirmReject = async () => {
    setBusy(true)
    try {
      await onReject(request.id, note)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm p-5">
      <h3 className="font-bold text-lg text-gray-900">{request.name}</h3>
      <p className="text-sm text-gray-600 mt-1">
        {request.adminName} · {request.adminEmail}
      </p>
      <p className="text-xs text-gray-400 mt-1">Submitted: {relativeTime(request.createdAt)}</p>

      {tempPassword ? (
        <div className="mt-4">
          <p className="text-sm text-gray-600 mb-2">Temporary password (for testing):</p>
          <CopyableCode value={tempPassword} />
        </div>
      ) : (
        <>
          <div className="flex gap-3 mt-4">
            <button
              type="button"
              onClick={handleApprove}
              disabled={busy}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-primary text-white hover:bg-primary/90 transition disabled:opacity-60"
            >
              Approve
            </button>
            <button
              type="button"
              onClick={() => setRejecting((v) => !v)}
              disabled={busy}
              className="px-4 py-2 rounded-lg text-sm font-semibold border-2 border-red-500 text-red-500 hover:bg-red-50 transition disabled:opacity-60"
            >
              Reject
            </button>
          </div>

          {rejecting && (
            <div className="mt-3 flex gap-2">
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Reason for rejection (optional)"
                className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <button
                type="button"
                onClick={handleConfirmReject}
                disabled={busy}
                className="px-3 py-1.5 rounded-lg text-sm font-semibold bg-red-500 text-white hover:bg-red-600 transition disabled:opacity-60"
              >
                Confirm
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default function SuperAdminDashboard() {
  const { user, logout } = useAuth()
  const [tab, setTab] = useState('pending')

  const [requests, setRequests] = useState([])
  const [requestsLoading, setRequestsLoading] = useState(true)
  // Keyed by hospital id — an approved card stays visible (in its
  // success state) so the temp password can actually be read/copied,
  // instead of being yanked from the list the instant it's approved.
  const [approvedPasswords, setApprovedPasswords] = useState({})

  const [hospitals, setHospitals] = useState([])
  const [hospitalsLoading, setHospitalsLoading] = useState(true)

  const [toasts, setToasts] = useState([])
  const toastId = useRef(0)

  const addToast = useCallback((message, type) => {
    const id = toastId.current++
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  const fetchRequests = useCallback(async () => {
    setRequestsLoading(true)
    try {
      const { data } = await getHospitalRequests()
      setRequests(data.data)
    } catch {
      addToast('Failed to load pending requests.', 'error')
    } finally {
      setRequestsLoading(false)
    }
  }, [addToast])

  const fetchHospitals = useCallback(async () => {
    setHospitalsLoading(true)
    try {
      const { data } = await getAllHospitals()
      setHospitals(data.data)
    } catch {
      addToast('Failed to load hospitals.', 'error')
    } finally {
      setHospitalsLoading(false)
    }
  }, [addToast])

  useEffect(() => {
    fetchRequests()
    fetchHospitals()
  }, [fetchRequests, fetchHospitals])

  const handleApprove = async (id) => {
    const { data } = await approveHospital(id)
    setApprovedPasswords((prev) => ({ ...prev, [id]: data.tempPassword }))
    addToast('Hospital approved. Admin account created.', 'success')
    fetchHospitals()
  }

  const handleReject = async (id, note) => {
    await rejectHospital(id, note)
    addToast('Hospital rejected.', 'default')
    setRequests((prev) => prev.filter((r) => r.id !== id))
    fetchHospitals()
  }

  const handleDelete = async (id) => {
    try {
      await deleteHospital(id)
      addToast('Hospital and all related data deleted.', 'success')
      setHospitals((prev) => prev.filter((h) => h.id !== id))
    } catch {
      addToast('Failed to delete hospital.', 'error')
    }
  }

  return (
    <div className="min-h-screen bg-surface">
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div>
            <h1 className="font-bold text-lg text-gray-900">MediCore Platform Admin</h1>
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
            { key: 'pending', label: 'Pending Requests' },
            { key: 'all', label: 'All Hospitals' },
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

        {tab === 'pending' && (
          <div className="space-y-4">
            {requestsLoading ? (
              <p className="text-sm text-gray-400">Loading...</p>
            ) : requests.length === 0 ? (
              <p className="text-sm text-gray-400">No pending requests</p>
            ) : (
              requests.map((r) => (
                <PendingRequestCard
                  key={r.id}
                  request={r}
                  tempPassword={approvedPasswords[r.id]}
                  onApprove={handleApprove}
                  onReject={handleReject}
                />
              ))
            )}
          </div>
        )}

        {tab === 'all' && (
          <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-400 uppercase border-b border-gray-100">
                    <th className="px-5 py-3 font-medium">Hospital Name</th>
                    <th className="px-5 py-3 font-medium">Admin Email</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium">Date</th>
                    <th className="px-5 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {hospitalsLoading ? (
                    <tr>
                      <td className="px-5 py-4 text-gray-400" colSpan={5}>
                        Loading...
                      </td>
                    </tr>
                  ) : hospitals.length === 0 ? (
                    <tr>
                      <td className="px-5 py-4 text-gray-400" colSpan={5}>
                        No hospitals yet
                      </td>
                    </tr>
                  ) : (
                    hospitals.map((h) => (
                      <HospitalRow key={h.id} hospital={h} onDelete={handleDelete} />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      <Toasts toasts={toasts} />
    </div>
  )
}
