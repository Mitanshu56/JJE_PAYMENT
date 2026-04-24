import React, { useState } from 'react'
import { Menu, X } from 'lucide-react'

export default function Header({ onUploadClick, onLogout, onNavigate, currentUser, activeTab = 'summary' }) {
  const [menuOpen, setMenuOpen] = useState(false)

  const navClass = (tab, mobile = false) => {
    const base = mobile
      ? 'block w-full text-left font-medium'
      : 'font-medium'
    const tone = activeTab === tab
      ? 'text-blue-700'
      : 'text-gray-600 hover:text-gray-900'
    return `${base} ${tone}`
  }

  const handleNavigate = (tab) => {
    onNavigate?.(tab)
    setMenuOpen(false)
  }

  const handleUpload = () => {
    onUploadClick?.()
    setMenuOpen(false)
  }

  const handleLogout = () => {
    onLogout?.()
    setMenuOpen(false)
  }

  return (
    <header className="bg-white shadow-md">
      <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">
            P
          </div>
          <h1 className="text-xl font-bold text-gray-900">Payment Dashboard</h1>
        </div>

        <nav className="hidden md:flex items-center gap-6">
          <button type="button" onClick={() => handleNavigate('summary')} className={navClass('summary')}>
            Dashboard
          </button>
          <button type="button" onClick={() => handleNavigate('invoices')} className={navClass('invoices')}>
            Invoices
          </button>
          <button type="button" onClick={() => handleNavigate('manage-payments')} className={navClass('manage-payments')}>
            Payments
          </button>
          <button
            onClick={handleUpload}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition"
          >
            Upload
          </button>
          <span className="text-sm text-gray-500">{currentUser || 'User'}</span>
          <button
            onClick={handleLogout}
            className="border border-gray-300 hover:bg-gray-100 text-gray-700 px-4 py-2 rounded-lg font-medium transition"
          >
            Logout
          </button>
        </nav>

        {/* Mobile Menu */}
        <button className="md:hidden" onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t border-gray-200 p-4 space-y-3">
          <button type="button" onClick={() => handleNavigate('summary')} className={navClass('summary', true)}>
            Dashboard
          </button>
          <button type="button" onClick={() => handleNavigate('invoices')} className={navClass('invoices', true)}>
            Invoices
          </button>
          <button type="button" onClick={() => handleNavigate('manage-payments')} className={navClass('manage-payments', true)}>
            Payments
          </button>
          <button
            onClick={handleUpload}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition"
          >
            Upload
          </button>
          <div className="text-sm text-gray-500">{currentUser || 'User'}</div>
          <button
            onClick={handleLogout}
            className="w-full border border-gray-300 hover:bg-gray-100 text-gray-700 px-4 py-2 rounded-lg font-medium transition"
          >
            Logout
          </button>
        </div>
      )}
    </header>
  )
}
