import React, { useState } from 'react'
import { authAPI, authStorage } from '../services/api'

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [sendingReset, setSendingReset] = useState(false)
  const [resetMessage, setResetMessage] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setResetMessage('')

    if (!username.trim() || !password.trim()) {
      setError('Please enter username and password')
      return
    }

    try {
      setLoading(true)
      const res = await authAPI.login(username.trim(), password.trim())
      const token = res?.data?.token
      const loggedUser = res?.data?.username || username.trim()
      if (!token) {
        setError('Login failed. No token returned.')
        return
      }

      authStorage.setToken(token)
      onLoginSuccess?.(loggedUser)
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
      setResetMessage(res?.data?.message || 'Reset password mail sent on mi******')
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
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoComplete="current-password"
            />
            <div className="mt-2 text-right">
              <button
                type="button"
                onClick={handleForgotPassword}
                disabled={sendingReset}
                className="text-sm text-blue-700 hover:text-blue-800 disabled:text-slate-400"
              >
                {sendingReset ? 'Sending reset mail...' : 'Forgot password?'}
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
