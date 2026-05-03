import React, { useEffect, useRef, useState } from 'react'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import ResetPassword from './pages/ResetPassword'
import FileUpload from './components/FileUpload'
import Header from './components/Header'
import { authAPI, authStorage } from './services/api'
import './index.css'

function App() {
  const dashboardRef = useRef(null)
  const [authReady, setAuthReady] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [currentUser, setCurrentUser] = useState('')
  const [currentRole, setCurrentRole] = useState('user')
  const [activeTab, setActiveTab] = useState('summary')
  const [fiscalYearsVersion, setFiscalYearsVersion] = useState(0)
  const [resetToken, setResetToken] = useState(() => new URLSearchParams(window.location.search).get('reset_token') || '')

  useEffect(() => {
    const handleLocationChange = () => {
      setResetToken(new URLSearchParams(window.location.search).get('reset_token') || '')
    }

    window.addEventListener('popstate', handleLocationChange)
    return () => window.removeEventListener('popstate', handleLocationChange)
  }, [])

  useEffect(() => {
    if (resetToken) {
      setAuthReady(true)
      return
    }

    const verifyAuth = async () => {
      const token = authStorage.getToken()
      if (!token) {
        setAuthReady(true)
        return
      }

      try {
        const res = await authAPI.me()
        setIsAuthenticated(true)
        setCurrentUser(res?.data?.username || '')
        setCurrentRole(res?.data?.role || 'user')
      } catch {
        authStorage.clearToken()
        setIsAuthenticated(false)
        setCurrentUser('')
        setCurrentRole('user')
      } finally {
        setAuthReady(true)
      }
    }

    verifyAuth()
  }, [resetToken])

  const handleUploadClick = () => {
    const uploadModal = document.getElementById('upload-modal')
    if (uploadModal) {
      uploadModal.showModal?.() || (uploadModal.style.display = 'flex')
    }
  }

  const handleUploadClose = () => {
    const uploadModal = document.getElementById('upload-modal')
    if (uploadModal) {
      uploadModal.close?.() || (uploadModal.style.display = 'none')
    }
  }

  const handleUploadComplete = () => {
    handleUploadClose()
    // Reload dashboard
    dashboardRef.current?.reload?.()
  }

  const handleHeaderNavigate = (tab) => {
    setActiveTab(tab)
    dashboardRef.current?.setActiveTab?.(tab)
  }

  const handleLoginSuccess = (username, role = 'user') => {
    setIsAuthenticated(true)
    setCurrentUser(username || '')
    setCurrentRole(role || 'user')
  }

  const handleLogout = () => {
    authStorage.clearToken()
    setIsAuthenticated(false)
    setCurrentUser('')
    setCurrentRole('user')
  }

  const handleResetComplete = () => {
    authStorage.clearToken()
    setResetToken('')
    setIsAuthenticated(false)
    setCurrentUser('')
    setCurrentRole('user')
    setActiveTab('summary')
    setAuthReady(true)
  }

  const handleFiscalYearsChanged = () => {
    setFiscalYearsVersion((value) => value + 1)
  }

  if (!authReady) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center">
        <div className="text-slate-600 text-sm">Checking login session...</div>
      </div>
    )
  }

  if (resetToken) {
    return <ResetPassword token={resetToken} onResetComplete={handleResetComplete} />
  }

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} refreshKey={fiscalYearsVersion} />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header
        onUploadClick={handleUploadClick}
        onLogout={handleLogout}
        onNavigate={handleHeaderNavigate}
        currentUser={currentUser}
        activeTab={activeTab}
        refreshKey={fiscalYearsVersion}
      />

      <main className="max-w-7xl mx-auto p-4 md:p-6">
        <Dashboard
          ref={dashboardRef}
          onActiveTabChange={setActiveTab}
          currentRole={currentRole}
          onFiscalYearsChanged={handleFiscalYearsChanged}
        />
      </main>

      {/* Upload Modal */}
      <dialog
        id="upload-modal"
        className="w-full max-w-md rounded-lg shadow-xl backdrop:bg-black backdrop:bg-opacity-50"
        onCancel={(e) => {
          e.preventDefault()
          handleUploadClose()
        }}
      >
        <div className="p-6 space-y-4">
          <h2 className="text-2xl font-bold text-gray-900">Upload Files</h2>
          <FileUpload onUploadComplete={handleUploadComplete} />
          <button
            onClick={handleUploadClose}
            className="w-full mt-4 px-4 py-2 text-gray-600 hover:text-gray-900 font-medium border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            Close
          </button>
        </div>
      </dialog>
    </div>
  )
}

export default App
