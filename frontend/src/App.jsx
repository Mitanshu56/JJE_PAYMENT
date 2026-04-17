import React, { useEffect, useRef, useState } from 'react'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import FileUpload from './components/FileUpload'
import Header from './components/Header'
import { authAPI, authStorage } from './services/api'
import './index.css'

function App() {
  const dashboardRef = useRef(null)
  const [authReady, setAuthReady] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [currentUser, setCurrentUser] = useState('')

  useEffect(() => {
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
      } catch {
        authStorage.clearToken()
        setIsAuthenticated(false)
        setCurrentUser('')
      } finally {
        setAuthReady(true)
      }
    }

    verifyAuth()
  }, [])

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

  const handleLoginSuccess = (username) => {
    setIsAuthenticated(true)
    setCurrentUser(username || '')
  }

  const handleLogout = () => {
    authStorage.clearToken()
    setIsAuthenticated(false)
    setCurrentUser('')
  }

  if (!authReady) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center">
        <div className="text-slate-600 text-sm">Checking login session...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header onUploadClick={handleUploadClick} onLogout={handleLogout} currentUser={currentUser} />

      <main className="max-w-7xl mx-auto p-4 md:p-6">
        <Dashboard ref={dashboardRef} />
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
