import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react'
import { dashboardAPI, billsAPI } from '../services/api'
import SummaryCards from '../components/dashboard/SummaryCards'
import PartyTable from '../components/tables/PartyTable'
import BillsTable from '../components/tables/BillsTable'
import ManagePayments from '../components/payments/ManagePayments'
import StatementTab from '../components/statements/StatementTab'
import StatementMatchTab from '../components/statements/StatementMatchTab'
import Charts from '../components/charts/Charts'
import '../components/dashboard/Dashboard.css'

const Dashboard = forwardRef(function Dashboard(_, ref) {
  const [summary, setSummary] = useState(null)
  const [partySummary, setPartySummary] = useState(null)
  const [monthlySummary, setMonthlySummary] = useState(null)
  const [allBills, setAllBills] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('summary')
  const [invoicesRefreshToken, setInvoicesRefreshToken] = useState(0)

  useEffect(() => {
    loadDashboardData()
  }, [])

  useImperativeHandle(ref, () => ({
    reload: async () => {
      await loadDashboardData()
      setInvoicesRefreshToken((prev) => prev + 1)
    },
  }))

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const [summaryRes, partyRes, monthlyRes, billsRes] = await Promise.allSettled([
        dashboardAPI.getSummary(),
        dashboardAPI.getPartySummary(),
        dashboardAPI.getMonthlySummary(),
        billsAPI.getAll(0, 1000),
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

  const handleMatchPayments = async () => {
    try {
      setLoading(true)
      await dashboardAPI.matchPayments()
      await loadDashboardData()
    } catch (err) {
      setError('Failed to match payments')
      console.error(err)
    } finally {
      setLoading(false)
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
          <button
            onClick={handleMatchPayments}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-medium transition"
          >
            {loading ? 'Processing...' : 'Match Payments'}
          </button>
        </div>

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
        </div>
      </div>
    </div>
  )
})

export default Dashboard
