import React, { useEffect, useState } from 'react'
import { Menu, X, Bell } from 'lucide-react'
import { fiscalAPI } from '../services/api'
import { getSelectedFiscalYear } from '../utils/fiscal'
import notificationsAPI from '../services/notificationsAPI'
import NotificationDropdown from './NotificationDropdown'

export default function Header({ onUploadClick, onLogout, onNavigate, currentUser, activeTab = 'summary', refreshKey = 0 }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [selectedFY, setSelectedFY] = useState(() => getSelectedFiscalYear())
  const [notificationOpen, setNotificationOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loadingNotifications, setLoadingNotifications] = useState(false)

  // Load notifications
  const loadNotifications = async () => {
    try {
      setLoadingNotifications(true)
      const res = await notificationsAPI.getNotifications(0, 20)
      const countRes = await notificationsAPI.getUnreadCount()
      
      if (res?.data?.notifications) {
        setNotifications(res.data.notifications)
      }
      if (countRes?.data?.unread_count !== undefined) {
        setUnreadCount(countRes.data.unread_count)
      }
    } catch (err) {
      console.error('Error loading notifications:', err)
    } finally {
      setLoadingNotifications(false)
    }
  }

  const handleMarkRead = () => {
    // Reload notifications when one is marked read
    loadNotifications()
  }

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fiscalAPI.listYears()
        const list = (res?.data?.data || []).map((d) => d.value).filter(Boolean)
        const storedFY = getSelectedFiscalYear() || ''
        const nextFY = list.includes(storedFY) ? storedFY : (storedFY || list[0] || 'FY-2025-2026')
        setSelectedFY(nextFY)
        localStorage.setItem('selected_fiscal_year', nextFY)
      } catch (err) {
        // ignore
      }
    }
    load()
    // Load notifications on mount
    loadNotifications()
  }, [refreshKey])

  useEffect(() => {
    const handleFYChange = (event) => {
      const nextFY = event?.detail || getSelectedFiscalYear()
      if (nextFY) {
        setSelectedFY(nextFY)
        localStorage.setItem('selected_fiscal_year', nextFY)
      }
    }

    window.addEventListener('selected-fiscal-year-changed', handleFYChange)
    return () => window.removeEventListener('selected-fiscal-year-changed', handleFYChange)
  }, [])

  // Auto-refresh notifications every 45 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadNotifications()
    }, 45000)
    
    return () => clearInterval(interval)
  }, [])

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
          <span className="border border-gray-200 rounded-md px-3 py-1.5 text-sm text-gray-700 bg-gray-50">
            {selectedFY || 'No FY selected'}
          </span>
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

          {/* Notification Bell */}
          <div className="relative">
            <button
              onClick={() => setNotificationOpen(!notificationOpen)}
              className="relative text-gray-600 hover:text-gray-900 transition-colors p-2 hover:bg-gray-100 rounded-lg"
            >
              <Bell size={20} />
              {unreadCount > 0 && (
                <span className="absolute top-0 right-0 bg-red-600 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {/* Notification Dropdown */}
            {notificationOpen && (
              <NotificationDropdown
                notifications={notifications}
                onClose={() => setNotificationOpen(false)}
                onMarkRead={handleMarkRead}
              />
            )}
          </div>

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
          <div className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-700 bg-gray-50">
            {selectedFY || 'No FY selected'}
          </div>
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

          {/* Mobile Notification Bell */}
          <button
            onClick={() => {
              setNotificationOpen(!notificationOpen)
              setMenuOpen(false)
            }}
            className="w-full flex items-center justify-between bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg font-medium transition"
          >
            Notifications
            {unreadCount > 0 && (
              <span className="bg-red-600 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
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
