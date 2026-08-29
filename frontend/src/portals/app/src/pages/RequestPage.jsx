import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeftIcon } from '@heroicons/react/24/outline'
import { requestHospitalAccess } from '../services/api.js'

export default function RequestPage() {
  const [hospitalName, setHospitalName] = useState('')
  const [adminName, setAdminName] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await requestHospitalAccess({
        hospitalName: hospitalName.trim(),
        adminName: adminName.trim(),
        adminEmail: adminEmail.trim(),
      })
      setSubmitted(true)
    } catch (err) {
      if (err.response?.status === 409) {
        setError('This email already submitted a request.')
      } else {
        setError(err.response?.data?.error || 'Failed to submit request. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-[500px] bg-white rounded-[20px] shadow-lg p-8 relative">
        <Link
          to="/"
          className="absolute left-6 top-6 text-gray-400 hover:text-primary transition"
          aria-label="Back to home"
        >
          <ArrowLeftIcon className="w-5 h-5" />
        </Link>

        {submitted ? (
          <div className="text-center py-6">
            <div className="mb-4 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3">
              Request submitted. We'll contact {adminEmail}.
            </div>
            <Link to="/" className="text-primary font-semibold hover:underline text-sm">
              Back to home
            </Link>
          </div>
        ) : (
          <>
            <div className="text-center mb-6 mt-4">
              <h1 className="text-xl font-bold text-gray-900">Request Hospital Access</h1>
              <p className="text-sm text-gray-500 mt-2">
                We'll verify your hospital and send login credentials.
              </p>
            </div>

            {error && (
              <div className="mb-4 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Hospital Name</label>
                <input
                  type="text"
                  value={hospitalName}
                  onChange={(e) => setHospitalName(e.target.value)}
                  required
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Your Name</label>
                <input
                  type="text"
                  value={adminName}
                  onChange={(e) => setAdminName(e.target.value)}
                  required
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Admin Email</label>
                <input
                  type="email"
                  value={adminEmail}
                  onChange={(e) => setAdminEmail(e.target.value)}
                  required
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition disabled:opacity-60"
              >
                {loading ? 'Submitting...' : 'Submit Request'}
              </button>
            </form>

            <p className="text-center text-sm text-gray-500 mt-5">
              Already have an account?{' '}
              <Link to="/login" className="text-primary font-semibold hover:underline">
                Sign in
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  )
}
