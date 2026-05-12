import React, { createContext, useState, useEffect, useCallback } from 'react'

/**
 * AdminFYContext
 * Manages admin-only Financial Year (FY) selection globally.
 * Normal users are not affected and will not have access to this context.
 */
export const AdminFYContext = createContext()

export function AdminFYProvider({ children, isAdmin = false }) {
  // Admin-specific FY storage key
  const ADMIN_FY_STORAGE_KEY = 'adminSelectedFY'
  
  const [adminSelectedFY, setAdminSelectedFY] = useState(() => {
    if (!isAdmin) return null
    
    try {
      // Restore admin FY from localStorage if available
      const stored = localStorage.getItem(ADMIN_FY_STORAGE_KEY)
      return stored || null
    } catch (e) {
      return null
    }
  })

  /**
   * Update admin-selected FY
   * This triggers automatic reload of all admin modules
   */
  const updateAdminFY = useCallback((newFY) => {
    if (!isAdmin || !newFY) return

    try {
      setAdminSelectedFY(newFY)
      localStorage.setItem(ADMIN_FY_STORAGE_KEY, newFY)
      
      // Emit custom event so all admin modules can reload
      window.dispatchEvent(
        new CustomEvent('admin-fy-changed', {
          detail: { fy: newFY },
        })
      )
    } catch (e) {
      console.error('Error updating admin FY:', e)
    }
  }, [isAdmin])

  /**
   * Clear admin FY on logout
   */
  const clearAdminFY = useCallback(() => {
    try {
      setAdminSelectedFY(null)
      localStorage.removeItem(ADMIN_FY_STORAGE_KEY)
    } catch (e) {
      console.error('Error clearing admin FY:', e)
    }
  }, [])

  const value = {
    adminSelectedFY,
    setAdminSelectedFY: updateAdminFY,
    clearAdminFY,
    isAdmin,
  }

  return <AdminFYContext.Provider value={value}>{children}</AdminFYContext.Provider>
}

/**
 * Hook to access admin FY context
 * Returns null if not admin user
 */
export function useAdminFY() {
  const context = React.useContext(AdminFYContext)
  if (!context) {
    return {
      adminSelectedFY: null,
      setAdminSelectedFY: () => {},
      clearAdminFY: () => {},
      isAdmin: false,
    }
  }
  return context
}
