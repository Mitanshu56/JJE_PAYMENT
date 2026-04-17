import React, { useState, useEffect } from 'react'
import { dashboardAPI } from '../services/api'
import SummaryCards from '../components/dashboard/SummaryCards'
import PartyTable from '../components/tables/PartyTable'
import BillsTable from '../components/tables/BillsTable'
import Charts from '../components/charts/Charts'
import '../components/dashboard/Dashboard.css'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [partySummary, setPartySummary] = useState(null)
  const [monthlySummary, setMonthlySummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('summary')

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const [summaryRes, partyRes, monthlyRes] = await Promise.all([
        dashboardAPI.getSummary(),
        dashboardAPI.getPartySummary(),
        dashboardAPI.getMonthlySummary(),
      ])

      setSummary(summaryRes.data.summary)
      setPartySummary(partyRes.data.party_summary)
      setMonthlySummary(monthlyRes.data.monthly_summary)
      setError(null)
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
          </div>
        </div>

        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === 'summary' && monthlySummary && (
            <Charts monthlySummary={monthlySummary} />
          )}
          {activeTab === 'parties' && partySummary && (
            <PartyTable parties={partySummary} />
          )}
          {activeTab === 'invoices' && (
            <BillsTable />
          )}
        </div>
      </div>
    </div>
  )
}
