import React, { useEffect, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { authAPI } from '../services/api'

export default function ResetPassword({ token, onResetComplete }) {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [resetComplete, setResetComplete] = useState(false)

  useEffect(() => {
    const validate = async () => {
      if (!token) {
        setError('Reset link is missing')
        setValidating(false)
        return
      }

      try {
        await authAPI.validateResetToken(token)
      } catch (err) {
        setError(err?.response?.data?.detail || 'Reset link is invalid or expired')
      } finally {
        setValidating(false)
      }
    }

    validate()
  }, [token])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')

    if (!password.trim() || !confirmPassword.trim()) {
      setError('Please enter and confirm the new password')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    try {
      setLoading(true)
      const res = await authAPI.resetPassword({
        token,
        password: password.trim(),
        confirm_password: confirmPassword.trim(),
      })
      setMessage(res?.data?.message || 'Password updated successfully')
      setResetComplete(true)
      window.history.replaceState({}, '', window.location.pathname)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Unable to reset password right now')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
        <div className="bg-slate-900 px-6 py-5 text-white">
          <h1 className="text-2xl font-bold tracking-wide">Reset Password</h1>
          <p className="text-sm text-slate-300 mt-1">Set a new password for your account</p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {validating ? (
            <div className="text-sm text-slate-600">Validating reset link...</div>
          ) : resetComplete ? (
            <div className="space-y-4">
              <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
                {message || 'Password updated successfully'}
              </div>
              <button
                type="button"
                onClick={() => onResetComplete?.()}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-md transition"
              >
                Go to Dashboard
              </button>
              <p className="text-xs text-slate-500 text-center">
                You can now sign in with your new password and continue to the dashboard.
              </p>
            </div>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">New Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter new password"
                    className="w-full border border-slate-300 rounded-md px-3 py-2 pr-11 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    className="absolute inset-y-0 right-0 px-3 text-slate-500 hover:text-slate-700"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Confirm Password</label>
                <div className="relative">
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm new password"
                    className="w-full border border-slate-300 rounded-md px-3 py-2 pr-11 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword((value) => !value)}
                    className="absolute inset-y-0 right-0 px-3 text-slate-500 hover:text-slate-700"
                    aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                  >
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {error && (
                <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
                  {error}
                </div>
              )}

              {message && (
                <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
                  {message}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !token}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white font-medium py-2 rounded-md transition"
              >
                {loading ? 'Updating password...' : 'Reset Password'}
              </button>
            </>
          )}
        </form>
      </div>
    </div>
  )
}