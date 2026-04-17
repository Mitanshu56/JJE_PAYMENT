import React, { useState } from 'react'
import { Menu, X } from 'lucide-react'

export default function Header({ onUploadClick }) {
  const [menuOpen, setMenuOpen] = useState(false)

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
          <a href="#dashboard" className="text-gray-600 hover:text-gray-900 font-medium">
            Dashboard
          </a>
          <a href="#invoices" className="text-gray-600 hover:text-gray-900 font-medium">
            Invoices
          </a>
          <a href="#payments" className="text-gray-600 hover:text-gray-900 font-medium">
            Payments
          </a>
          <button
            onClick={onUploadClick}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition"
          >
            Upload
          </button>
        </nav>

        {/* Mobile Menu */}
        <button className="md:hidden" onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t border-gray-200 p-4 space-y-3">
          <a href="#dashboard" className="block text-gray-600 hover:text-gray-900 font-medium">
            Dashboard
          </a>
          <a href="#invoices" className="block text-gray-600 hover:text-gray-900 font-medium">
            Invoices
          </a>
          <a href="#payments" className="block text-gray-600 hover:text-gray-900 font-medium">
            Payments
          </a>
          <button
            onClick={onUploadClick}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition"
          >
            Upload
          </button>
        </div>
      )}
    </header>
  )
}
