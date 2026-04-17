import React, { useRef } from 'react'
import Dashboard from './pages/Dashboard'
import FileUpload from './components/FileUpload'
import Header from './components/Header'
import './index.css'

function App() {
  const dashboardRef = useRef(null)

  const handleUploadClick = () => {
    const uploadModal = document.getElementById('upload-modal')
    if (uploadModal) {
      uploadModal.showModal?.() || (uploadModal.style.display = 'flex')
    }
  }

  const handleUploadComplete = () => {
    const uploadModal = document.getElementById('upload-modal')
    if (uploadModal) {
      uploadModal.close?.() || (uploadModal.style.display = 'none')
    }
    // Reload dashboard
    dashboardRef.current?.reload?.()
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header onUploadClick={handleUploadClick} />

      <main className="max-w-7xl mx-auto p-4 md:p-6">
        <Dashboard ref={dashboardRef} />
      </main>

      {/* Upload Modal */}
      <dialog id="upload-modal" className="w-full max-w-md rounded-lg shadow-xl backdrop:bg-black backdrop:bg-opacity-50">
        <div className="p-6 space-y-4">
          <h2 className="text-2xl font-bold text-gray-900">Upload Files</h2>
          <FileUpload onUploadComplete={handleUploadComplete} />
          <button
            onClick={() => {
              const modal = document.getElementById('upload-modal')
              modal.close?.()
            }}
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
