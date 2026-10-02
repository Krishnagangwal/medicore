import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { PlusIcon, EyeIcon, EyeSlashIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { resetPassword } from '../services/api.js'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)
    try {
      await resetPassword(token, password)
      setSuccess(true)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to set password. Please try again.')
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

        {!token ? (
          <div className="text-center py-4">
            <p className="font-semibold text-gray-800 mb-2">Link is missing a token</p>
            <p className="text-sm text-gray-500 mb-5">
              Open this page from the link in your invite or approval email.
            </p>
            <Link to="/login" className="text-primary font-semibold hover:underline text-sm">
              Back to login
            </Link>
          </div>
        ) : success ? (
          <div className="text-center py-4">
            <CheckCircleIcon className="w-12 h-12 text-accent mx-auto mb-3" />
            <p className="font-semibold text-gray-800 mb-2">Password set</p>
            <p className="text-sm text-gray-500 mb-5">You can now log in with your new password.</p>
            <Link to="/login" className="text-primary font-semibold hover:underline text-sm">
              Go to login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <p className="text-center font-semibold text-gray-800">Set your password</p>

            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2">
                {error}
              </div>
            )}

            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoFocus
                placeholder="New password"
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

            <input
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              placeholder="Confirm password"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-white font-semibold rounded-lg py-2.5 hover:bg-primary/90 transition disabled:opacity-60"
            >
              {loading ? 'Setting password...' : 'Set Password'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
