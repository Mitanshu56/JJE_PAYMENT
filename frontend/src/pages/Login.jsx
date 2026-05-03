import React, { useEffect, useState } from 'react'
import { getSelectedFiscalYear } from '../utils/fiscal'
import { Eye, EyeOff } from 'lucide-react'
import { authAPI, authStorage, fiscalAPI } from '../services/api'

function getCurrentFiscalYear() {
  // Use the requested fiscal year label by default rather than computing from date
  return 'FY-2025-2026'
}

export default function Login({ onLoginSuccess, refreshKey = 0 }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [fiscalYears, setFiscalYears] = useState([])
  const [selectedFY, setSelectedFY] = useState(() => {
    try {
      return localStorage.getItem('selected_fiscal_year') || 'FY-2025-2026'
    } catch (e) {
      return 'FY-2025-2026'
    }
  })
  const [loading, setLoading] = useState(false)
  const [loadingFYs, setLoadingFYs] = useState(false)
  const [sendingReset, setSendingReset] = useState(false)
  const [resetMessage, setResetMessage] = useState('')
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  useEffect(() => {
    const loadFiscalYears = async () => {
      try {
        setLoadingFYs(true)
        const res = await fiscalAPI.listYears()
        const years = (res?.data?.data || []).map((item) => item.value).filter(Boolean)
        setFiscalYears(years)
        const storedFY = getSelectedFiscalYear() || ''
        const nextFY = years.includes(storedFY) ? storedFY : (storedFY || years[0] || getCurrentFiscalYear())
        setSelectedFY(nextFY)
        localStorage.setItem('selected_fiscal_year', nextFY)
      } catch {
        const currentFY = getSelectedFiscalYear() || getCurrentFiscalYear()
        setSelectedFY(currentFY)
        localStorage.setItem('selected_fiscal_year', currentFY)
      } finally {
        setLoadingFYs(false)
      }
    }

    loadFiscalYears()
  }, [refreshKey])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setResetMessage('')

    if (!username.trim() || !password.trim()) {
      setError('Please enter username and password')
      return
    }

    try {
      const resolvedFY = selectedFY || getSelectedFiscalYear() || getCurrentFiscalYear()
      if (resolvedFY) {
        setSelectedFY(resolvedFY)
        localStorage.setItem('selected_fiscal_year', resolvedFY)
        window.dispatchEvent(new CustomEvent('selected-fiscal-year-changed', { detail: resolvedFY }))
      }
      setLoading(true)
      const res = await authAPI.login(username.trim(), password.trim())
      const token = res?.data?.token
      const loggedUser = res?.data?.username || username.trim()
      if (!token) {
        setError('Login failed. No token returned.')
        return
      }

      authStorage.setToken(token)
      onLoginSuccess?.(loggedUser, res?.data?.role || 'user')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  const handleForgotPassword = async () => {
    setError('')
    setResetMessage('')

    try {
      setSendingReset(true)
      const res = await authAPI.forgotPassword(username.trim())
      setResetMessage(res?.data?.message || 'Reset password link sent on mi******')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Unable to send reset password mail right now.')
    } finally {
      setSendingReset(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
        <div className="bg-slate-900 px-6 py-5 text-white">
          <h1 className="text-2xl font-bold tracking-wide">JJE Business Login</h1>
          <p className="text-sm text-slate-300 mt-1">Authorized users only</p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Fiscal Year</label>
            <select
              value={selectedFY}
              onChange={(e) => setSelectedFY(e.target.value)}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {!selectedFY && <option value="">Select fiscal year</option>}
              {fiscalYears.map((fy) => (
                <option key={fy} value={fy}>{fy}</option>
              ))}
              {fiscalYears.length === 0 && selectedFY && (
                <option value={selectedFY}>{selectedFY}</option>
              )}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              {loadingFYs ? 'Loading fiscal years...' : 'Choose the FY before signing in.'}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoComplete="username"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="w-full border border-slate-300 rounded-md px-3 py-2 pr-11 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoComplete="current-password"
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
            <div className="mt-2 text-right">
              <button
                type="button"
                onClick={handleForgotPassword}
                disabled={sendingReset}
                className="text-sm text-blue-700 hover:text-blue-800 disabled:text-slate-400"
              >
                {sendingReset ? 'Sending reset link...' : 'Forgot password?'}
              </button>
            </div>
          </div>

          {error && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
              {error}
            </div>
          )}

          {resetMessage && (
            <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
              {resetMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white font-medium py-2 rounded-md transition"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
