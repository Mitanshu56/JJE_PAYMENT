import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react'
import { dashboardAPI, billsAPI } from '../services/api'
import SummaryCards from '../components/dashboard/SummaryCards'
import PartyTable from '../components/tables/PartyTable'
import BillsTable from '../components/tables/BillsTable'
import ManagePayments from '../components/payments/ManagePayments'
import StatementTab from '../components/statements/StatementTab'
import StatementMatchTab from '../components/statements/StatementMatchTab'
import Charts from '../components/charts/Charts'
import ChatBot from '../components/ChatBot'
import PaymentReminder from './PaymentReminder'
import { fiscalAPI } from '../services/api'
import { getSelectedFiscalYear } from '../utils/fiscal'
import '../components/dashboard/Dashboard.css'
import { useAdminFY } from '../context/AdminFYContext'

function buildNextFiscalYearLabel() {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  return month >= 4 ? `FY-${year}-${year + 1}` : `FY-${year - 1}-${year}`
}

const Dashboard = forwardRef(function Dashboard({ onActiveTabChange, currentRole = 'user', onFiscalYearsChanged }, ref) {
  const { adminSelectedFY } = useAdminFY()
  const isAdmin = currentRole === 'admin'

  const [summary, setSummary] = useState(null)
  const [partySummary, setPartySummary] = useState(null)
  const [monthlySummary, setMonthlySummary] = useState(null)
  const [allBills, setAllBills] = useState([])
  const [fiscalYears, setFiscalYears] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('summary')
  const [invoicesRefreshToken, setInvoicesRefreshToken] = useState(0)
  const [newFiscalYear, setNewFiscalYear] = useState(buildNextFiscalYearLabel())
  const [creatingFiscalYear, setCreatingFiscalYear] = useState(false)
  const [fiscalYearMessage, setFiscalYearMessage] = useState('')
  const [fiscalYearError, setFiscalYearError] = useState('')
  const [currentFY, setCurrentFY] = useState(() => getSelectedFiscalYear())
  const [deleteFYTarget, setDeleteFYTarget] = useState('')
  const [deleteFYPassword, setDeleteFYPassword] = useState('')
  const [deletingFiscalYear, setDeletingFiscalYear] = useState(false)

  useEffect(() => {
    loadDashboardData()
    refreshFiscalYears()
  }, [])

  useEffect(() => {
    if (isAdmin && adminSelectedFY && adminSelectedFY !== currentFY) {
      setCurrentFY(adminSelectedFY)
    }
  }, [isAdmin, adminSelectedFY, currentFY])

  // Listen for admin FY changes and reload data
  useEffect(() => {
    const handleAdminFYChange = (event) => {
      if (isAdmin && event?.detail?.fy) {
        setCurrentFY(event.detail.fy)
        // Refresh invoice token to trigger reload in child components
        setInvoicesRefreshToken((prev) => prev + 1)
      }
    }

    window.addEventListener('admin-fy-changed', handleAdminFYChange)
    return () => window.removeEventListener('admin-fy-changed', handleAdminFYChange)
  }, [isAdmin])

  useEffect(() => {
    const handleFYChange = (event) => {
      const nextFY = event?.detail || getSelectedFiscalYear()
      if (nextFY && nextFY !== currentFY) {
        setCurrentFY(nextFY)
      }
    }

    window.addEventListener('selected-fiscal-year-changed', handleFYChange)
    return () => window.removeEventListener('selected-fiscal-year-changed', handleFYChange)
  }, [currentFY])

  useEffect(() => {
    if (!currentFY) return
    setSummary(null)
    setPartySummary(null)
    setMonthlySummary(null)
    setAllBills([])
    loadDashboardData()
  }, [currentFY])

  useEffect(() => {
    onActiveTabChange?.(activeTab)
  }, [activeTab, onActiveTabChange])

  // Keep dashboard views in sync across admin and normal users.
  useEffect(() => {
    const interval = setInterval(() => {
      loadDashboardData()
      setInvoicesRefreshToken((prev) => prev + 1)
    }, 30000)

    return () => clearInterval(interval)
  }, [currentFY, isAdmin])

  useImperativeHandle(ref, () => ({
    reload: async () => {
      await loadDashboardData()
      setInvoicesRefreshToken((prev) => prev + 1)
    },
    setActiveTab: (tab) => {
      if (tab) setActiveTab(tab)
    },
  }))

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      setError(null)
      const fyParam = isAdmin ? currentFY : null
      const [summaryRes, partyRes, monthlyRes, billsRes] = await Promise.allSettled([
        dashboardAPI.getSummary(fyParam),
        dashboardAPI.getPartySummary(fyParam),
        dashboardAPI.getMonthlySummary(fyParam),
        billsAPI.getAll(0, 1000, null, null, null, fyParam),
      ])

      const errors = []

      if (summaryRes.status === 'fulfilled') {
        setSummary(summaryRes.value.data.summary)
      } else {
        errors.push('summary')
      }

      if (partyRes.status === 'fulfilled') {
        setPartySummary(partyRes.value.data.party_summary || [])
      } else {
        errors.push('parties')
      }

      if (monthlyRes.status === 'fulfilled') {
        setMonthlySummary(monthlyRes.value.data.monthly_summary || [])
      } else {
        errors.push('monthly')
      }

      if (billsRes.status === 'fulfilled') {
        setAllBills(billsRes.value.data.bills || [])
      } else {
        errors.push('bills')
        setAllBills([])
      }

      setError(errors.length ? `Failed to load: ${errors.join(', ')}` : null)
    } catch (err) {
      setError('Failed to load dashboard data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const refreshFiscalYears = async () => {
    try {
      const res = await fiscalAPI.listYears()
      const list = (res?.data?.data || []).map((item) => item.value).filter(Boolean)
      setFiscalYears(list)
    } catch {
      setFiscalYears([])
    }
  }

  const handleCreateFiscalYear = async (event) => {
    event.preventDefault()
    setFiscalYearError('')
    setFiscalYearMessage('')

    const value = newFiscalYear.trim()
    if (!value) {
      setFiscalYearError('Fiscal year value is required')
      return
    }

    try {
      setCreatingFiscalYear(true)
      const res = await fiscalAPI.createYear({ value })
      const createdValue = res?.data?.fiscal_year?.value || value
      localStorage.setItem('selected_fiscal_year', createdValue)
      window.dispatchEvent(new CustomEvent('selected-fiscal-year-changed', { detail: createdValue }))
      setFiscalYearMessage(`Created ${createdValue}`)
      setNewFiscalYear(buildNextFiscalYearLabel())
      await refreshFiscalYears()
      onFiscalYearsChanged?.()
      await loadDashboardData()
    } catch (err) {
      setFiscalYearError(err?.response?.data?.detail || 'Unable to create fiscal year')
    } finally {
      setCreatingFiscalYear(false)
    }
  }

  const handleDeleteFiscalYear = async (value) => {
    const fiscalValue = String(value || '').trim()
    if (!fiscalValue) return

    setFiscalYearError('')
    setFiscalYearMessage('')
    setDeleteFYTarget(fiscalValue)
    setDeleteFYPassword('')
  }

  const confirmDeleteFiscalYear = async (event) => {
    event?.preventDefault?.()

    const fiscalValue = String(deleteFYTarget || '').trim()
    const password = String(deleteFYPassword || '').trim()

    if (!fiscalValue) return
    if (!password) {
      setFiscalYearError('Admin password required')
      return
    }

    try {
      setDeletingFiscalYear(true)
      setFiscalYearError('')
      setFiscalYearMessage('')
      await fiscalAPI.deleteYear(fiscalValue, password)

      const res = await fiscalAPI.listYears()
      const remainingYears = (res?.data?.data || []).map((item) => item.value).filter(Boolean)
      setFiscalYears(remainingYears)

      const activeFY = getSelectedFiscalYear() || ''
      if (activeFY === fiscalValue) {
        const fallbackFY = remainingYears[0] || buildNextFiscalYearLabel()
        localStorage.setItem('selected_fiscal_year', fallbackFY)
        window.dispatchEvent(new CustomEvent('selected-fiscal-year-changed', { detail: fallbackFY }))
      }

      setFiscalYearMessage(`Removed ${fiscalValue}`)
      onFiscalYearsChanged?.()
      await loadDashboardData()
      setDeleteFYTarget('')
      setDeleteFYPassword('')
    } catch (err) {
      setFiscalYearError(err?.response?.data?.detail || 'Unable to remove fiscal year')
    } finally {
      setDeletingFiscalYear(false)
    }
  }

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Payment Dashboard</h1>
        </div>

        {currentRole === 'admin' && (
          <div className="bg-white border border-blue-200 rounded-xl p-4 mb-6 shadow-sm">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Admin FY Setup</h2>
                  <p className="text-sm text-gray-600">Create or remove financial years for login and statement scoping.</p>
                </div>
                <form onSubmit={handleCreateFiscalYear} className="flex flex-col gap-3 md:flex-row md:items-end">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Fiscal Year</label>
                    <input
                      type="text"
                      value={newFiscalYear}
                      onChange={(e) => setNewFiscalYear(e.target.value)}
                      className="w-full md:w-56 border border-gray-300 rounded-md px-3 py-2 text-sm"
                      placeholder="FY-2025-2026"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={creatingFiscalYear}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md font-medium transition"
                  >
                    {creatingFiscalYear ? 'Creating...' : 'Create FY'}
                  </button>
                </form>
              </div>

              <div className="border-t border-gray-100 pt-4">
                <div className="text-sm font-semibold text-gray-900 mb-2">Available fiscal years</div>
                <div className="flex flex-wrap gap-2">
                  {fiscalYears.length > 0 ? fiscalYears.map((fy) => (
                    <div key={fy} className="flex items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5">
                      <span className="text-sm text-gray-800">{fy}</span>
                      <button
                        type="button"
                        onClick={() => handleDeleteFiscalYear(fy)}
                        className="text-xs font-semibold text-red-700 hover:text-red-800"
                        title={`Remove ${fy}`}
                      >
                        Remove
                      </button>
                    </div>
                  )) : (
                    <div className="text-sm text-gray-500">No fiscal years found.</div>
                  )}
                </div>
              </div>
            </div>
            {fiscalYearMessage && <div className="mt-3 text-sm text-green-700">{fiscalYearMessage}</div>}
            {fiscalYearError && <div className="mt-3 text-sm text-red-700">{fiscalYearError}</div>}
          </div>
        )}

        {deleteFYTarget && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
            <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl border border-slate-200">
              <div className="border-b border-slate-200 px-6 py-4">
                <h3 className="text-lg font-semibold text-slate-900">Warning</h3>
                <p className="mt-1 text-sm text-slate-600">
                  Removing fiscal year <span className="font-semibold text-slate-900">{deleteFYTarget}</span> will delete it from admin settings.
                </p>
              </div>

              <form onSubmit={confirmDeleteFiscalYear} className="px-6 py-5 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Admin password</label>
                  <input
                    type="password"
                    value={deleteFYPassword}
                    onChange={(e) => setDeleteFYPassword(e.target.value)}
                    autoFocus
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                    placeholder="Enter admin password"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setDeleteFYTarget('')
                      setDeleteFYPassword('')
                    }}
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    disabled={deletingFiscalYear}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={deletingFiscalYear}
                    className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:bg-red-300"
                  >
                    {deletingFiscalYear ? 'Removing...' : 'Remove FY'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Summary Cards */}
        {summary && <SummaryCards summary={summary} />}

        {/* Tabs */}
        <div className="mt-8 border-b border-gray-200">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('summary')}
              className={`pb-3 px-4 font-medium border-b-2 transition ${
                activeTab === 'summary'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Summary
            </button>
            <button
              onClick={() => setActiveTab('parties')}
              className={`pb-3 px-4 font-medium border-b-2 transition ${
                activeTab === 'parties'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Parties
            </button>
            <button
              onClick={() => setActiveTab('invoices')}
              className={`pb-3 px-4 font-medium border-b-2 transition ${
                activeTab === 'invoices'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Invoices
            </button>
            <button
              onClick={() => setActiveTab('manage-payments')}
              className={`pb-3 px-4 font-medium border-b-2 transition ${
                activeTab === 'manage-payments'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Manage Payment
            </button>
            <button
              onClick={() => setActiveTab('statement')}
              className={`pb-3 px-4 font-medium border-b-2 transition ${
                activeTab === 'statement'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Statement
            </button>
            <button
              onClick={() => setActiveTab('statement-match')}
              className={`pb-3 px-4 font-medium border-b-2 transition ${
                activeTab === 'statement-match'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Statement Match
            </button>
            <button
              onClick={() => setActiveTab('payment-reminder')}
              className={`pb-3 px-4 font-medium border-b-2 transition ${
                activeTab === 'payment-reminder'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              Payment Reminder
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === 'summary' && monthlySummary && (
            <Charts monthlySummary={monthlySummary} />
          )}
          {activeTab === 'parties' && partySummary && (
            <PartyTable parties={partySummary} bills={allBills} />
          )}
          {activeTab === 'invoices' && (
            <BillsTable refreshToken={invoicesRefreshToken} onBillDeleted={loadDashboardData} />
          )}
          {activeTab === 'manage-payments' && (
            <ManagePayments bills={allBills} onPaymentSaved={loadDashboardData} />
          )}
          {activeTab === 'statement' && (
            <StatementTab />
          )}
          {activeTab === 'statement-match' && (
            <StatementMatchTab onDataChanged={loadDashboardData} />
          )}
          {activeTab === 'payment-reminder' && (
            <PaymentReminder />
          )}
        </div>

        {/* ChatBot Widget */}
        <ChatBot fiscalYear={currentFY} />
      </div>
    </div>
  )
})

export default Dashboard
