import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Bell, ChevronDown, Menu, X } from 'lucide-react'
import { fiscalAPI } from '../services/api'
import notificationsAPI from '../services/notificationsAPI'
import NotificationDropdown from './NotificationDropdown'
import { getSelectedFiscalYear, setSelectedFiscalYear } from '../utils/fiscal'
import { useAdminFY } from '../context/AdminFYContext'

export default function Header({
  onUploadClick,
  onLogout,
  onNavigate,
  currentUser,
  activeTab = 'summary',
  refreshKey = 0,
  currentRole = 'user',
}) {
  const isAdminUser = currentRole === 'admin'
  const { adminSelectedFY, setAdminSelectedFY } = useAdminFY()

  const [menuOpen, setMenuOpen] = useState(false)
  const [availableFYs, setAvailableFYs] = useState([])
  const [fyDropdownOpen, setFyDropdownOpen] = useState(false)
  const [displayFY, setDisplayFY] = useState(getSelectedFiscalYear() || 'FY-2025-2026')

  const [notificationOpen, setNotificationOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loadingNotifications, setLoadingNotifications] = useState(false)

  const fyDropdownRef = useRef(null)
  const notificationRef = useRef(null)

  const effectiveFY = useMemo(() => {
    if (isAdminUser) {
      return adminSelectedFY || displayFY
    }
    return displayFY
  }, [isAdminUser, adminSelectedFY, displayFY])

  const loadNotifications = async () => {
    try {
      setLoadingNotifications(true)
      const [notificationsRes, unreadRes] = await Promise.all([
        notificationsAPI.getNotifications(0, 20, true),
        notificationsAPI.getUnreadCount(),
      ])

      setNotifications(notificationsRes?.data?.notifications || [])
      setUnreadCount(unreadRes?.data?.unread_count || 0)
    } catch (err) {
      console.error('Error loading notifications:', err)
    } finally {
      setLoadingNotifications(false)
    }
  }

  const refreshUnreadCount = async () => {
    try {
      const countRes = await notificationsAPI.getUnreadCount()
      setUnreadCount(countRes?.data?.unread_count || 0)
    } catch (err) {
      console.error('Error refreshing unread count:', err)
    }
  }

  const handleNotificationAction = async (action, notificationId) => {
    if (!notificationId) return

    if (action === 'read' || action === 'delete') {
      setNotifications((prev) => prev.filter((n) => n._id !== notificationId))
    }

    await refreshUnreadCount()
  }

  const handleAdminFYChange = (nextFY) => {
    if (!isAdminUser || !nextFY) return

    setDisplayFY(nextFY)
    setSelectedFiscalYear(nextFY)
    setAdminSelectedFY(nextFY)
    window.dispatchEvent(new CustomEvent('selected-fiscal-year-changed', { detail: nextFY }))
    setFyDropdownOpen(false)
    setMenuOpen(false)
  }

  useEffect(() => {
    let mounted = true

    const loadFYs = async () => {
      try {
        const res = await fiscalAPI.listYears()
        const list = (res?.data?.data || []).map((item) => item?.value).filter(Boolean)
        if (!mounted) return

        setAvailableFYs(list)

        if (isAdminUser) {
          const nextFY = adminSelectedFY || list[0] || getSelectedFiscalYear() || 'FY-2025-2026'
          setDisplayFY(nextFY)
          if (nextFY !== adminSelectedFY) {
            setAdminSelectedFY(nextFY)
          }
          setSelectedFiscalYear(nextFY)
        } else {
          const userFY = getSelectedFiscalYear() || list[0] || 'FY-2025-2026'
          setDisplayFY(userFY)
        }
      } catch (err) {
        console.error('Error loading financial years:', err)
      }
    }

    loadFYs()
    loadNotifications()

    return () => {
      mounted = false
    }
  }, [refreshKey, isAdminUser, adminSelectedFY, setAdminSelectedFY])

  useEffect(() => {
    const handleFiscalYearChange = (event) => {
      if (isAdminUser) return
      const nextFY = event?.detail || getSelectedFiscalYear()
      if (nextFY) {
        setDisplayFY(nextFY)
      }
    }

    window.addEventListener('selected-fiscal-year-changed', handleFiscalYearChange)
    return () => window.removeEventListener('selected-fiscal-year-changed', handleFiscalYearChange)
  }, [isAdminUser])

  useEffect(() => {
    const closeOutside = (event) => {
      if (fyDropdownRef.current && !fyDropdownRef.current.contains(event.target)) {
        setFyDropdownOpen(false)
      }
      if (notificationRef.current && !notificationRef.current.contains(event.target)) {
        setNotificationOpen(false)
      }
    }

    document.addEventListener('mousedown', closeOutside)
    return () => document.removeEventListener('mousedown', closeOutside)
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      loadNotifications()
    }, 45000)

    return () => clearInterval(interval)
  }, [])

  const navClass = (tab, mobile = false) => {
    const base = mobile ? 'block w-full text-left font-medium' : 'font-medium'
    const tone = activeTab === tab ? 'text-blue-700' : 'text-gray-600 hover:text-gray-900'
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
    setFyDropdownOpen(false)
    setNotificationOpen(false)
  }

  const renderFYControl = (mobile = false) => {
    if (isAdminUser) {
      return (
        <div ref={mobile ? undefined : fyDropdownRef} className={mobile ? 'w-full' : 'relative'}>
          <button
            type="button"
            onClick={() => setFyDropdownOpen((value) => !value)}
            className={mobile
              ? 'w-full flex items-center justify-between border border-blue-200 rounded-md px-3 py-2 text-sm text-blue-800 bg-blue-50'
              : 'flex items-center gap-2 border border-blue-200 rounded-md px-3 py-1.5 text-sm text-blue-800 bg-blue-50'}
          >
            <span>{effectiveFY || 'Select FY'}</span>
            <ChevronDown size={16} />
          </button>

          {fyDropdownOpen && (
            <div className={mobile
              ? 'mt-2 w-full bg-white border border-gray-200 rounded-md shadow-lg z-30'
              : 'absolute top-full mt-2 right-0 min-w-52 bg-white border border-gray-200 rounded-md shadow-lg z-30'}>
              {(availableFYs.length ? availableFYs : [effectiveFY]).filter(Boolean).map((fy) => (
                <button
                  key={fy}
                  type="button"
                  onClick={() => handleAdminFYChange(fy)}
                  className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-100 ${fy === effectiveFY ? 'bg-blue-50 text-blue-800 font-medium' : 'text-gray-700'}`}
                >
                  {fy}
                </button>
              ))}
            </div>
          )}
        </div>
      )
    }

    return (
      <span className={mobile
        ? 'w-full block border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-700 bg-gray-50'
        : 'border border-gray-200 rounded-md px-3 py-1.5 text-sm text-gray-700 bg-gray-50'}
      >
        {effectiveFY || 'No FY selected'}
      </span>
    )
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
          {renderFYControl(false)}

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

          <div ref={notificationRef} className="relative">
            <button
              onClick={() => setNotificationOpen((value) => !value)}
              className="relative text-gray-600 hover:text-gray-900 transition-colors p-2 hover:bg-gray-100 rounded-lg"
              title={loadingNotifications ? 'Refreshing notifications...' : 'Notifications'}
            >
              <Bell size={20} />
              {unreadCount > 0 && (
                <span className="absolute top-0 right-0 bg-red-600 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {notificationOpen && (
              <NotificationDropdown
                notifications={notifications}
                onClose={() => setNotificationOpen(false)}
                onMarkRead={handleNotificationAction}
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

        <button className="md:hidden" onClick={() => setMenuOpen((value) => !value)}>
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t border-gray-200 p-4 space-y-3">
          {renderFYControl(true)}

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

          <button
            onClick={() => {
              setNotificationOpen((value) => !value)
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

          <span className="block text-sm text-gray-500">{currentUser || 'User'}</span>
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
