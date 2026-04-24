import React, { useEffect, useMemo, useState } from 'react'
import { RefreshCw, Upload } from 'lucide-react'
import { statementsAPI, uploadAPI } from '../../services/api'

const PAGE_SIZE = 12

function formatMoney(value) {
  return Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })
}

function getFiscalLabel(fiscalYear) {
  return fiscalYear ? `FY ${fiscalYear}` : 'Financial year'
}

export default function StatementTab() {
  const [months, setMonths] = useState([])
  const [activeMonthKey, setActiveMonthKey] = useState('')
  const [totalRows, setTotalRows] = useState(0)
  const [availableFilters, setAvailableFilters] = useState({ fiscal_years: [] })
  const [fiscalYear, setFiscalYear] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [deletingMonthKey, setDeletingMonthKey] = useState('')
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const fiscalYearOptions = useMemo(() => availableFilters.fiscal_years || [], [availableFilters.fiscal_years])
  const allRowsCount = useMemo(() => months.reduce((sum, month) => sum + Number(month.count || 0), 0), [months])
  const allTotalDeposit = useMemo(
    () => months.reduce((sum, month) => sum + Number(month.total_deposit || 0), 0),
    [months],
  )
  const isAllMonthsSelected = activeMonthKey === 'ALL'
  const activeMonth = useMemo(
    () => months.find((month) => month.month_key === activeMonthKey) || months[0] || null,
    [months, activeMonthKey],
  )

  const loadStatements = async (nextFiscalYear = fiscalYear) => {
    try {
      setLoading(true)
      setError(null)

      const res = await statementsAPI.getMonthly({
        fiscalYear: nextFiscalYear || undefined,
        page: 1,
        pageSize: PAGE_SIZE,
      })
      const data = res?.data || {}

      setMonths(data.months || [])
      setTotalRows(data.total_rows || 0)
      setAvailableFilters({
        fiscal_years: data.available_filters?.fiscal_years || [],
      })

      const resolvedFiscalYear = nextFiscalYear || data.filters?.fiscal_year || data.available_filters?.fiscal_years?.[0]?.value || ''
      if (resolvedFiscalYear && resolvedFiscalYear !== fiscalYear) {
        setFiscalYear(resolvedFiscalYear)
      }

      const nextActiveMonth = data.months?.find((month) => month.month_key === activeMonthKey) || data.months?.[0] || null
      setActiveMonthKey(nextActiveMonth?.month_key || '')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load statement data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStatements(fiscalYear)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fiscalYear])

  const handlePdfUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setUploading(true)
      setError(null)
      setSuccess(null)

      const res = await uploadAPI.uploadStatementPdf(file)
      setSuccess(res?.data?.message || 'Statement PDF uploaded')
      await loadStatements(fiscalYear)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to upload statement PDF')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleFiscalYearChange = (value) => {
    setFiscalYear(value)
  }

  const handleDeleteMonth = async (monthKey) => {
    if (!monthKey) return

    const confirmed = window.confirm(`Remove all statement rows for ${monthKey}? This cannot be undone.`)
    if (!confirmed) return

    try {
      setDeletingMonthKey(monthKey)
      setError(null)
      setSuccess(null)
      const res = await statementsAPI.deleteMonth(monthKey)
      setSuccess(res?.data?.message || 'Statement month removed successfully')
      await loadStatements(fiscalYear)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to remove statement month')
    } finally {
      setDeletingMonthKey('')
    }
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow-md p-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Statement (PDF)</h3>
            <p className="text-sm text-gray-600 mt-1">
              Upload a statement PDF, then browse months for the selected financial year.
            </p>
          </div>

          <button
            type="button"
            onClick={() => loadStatements(fiscalYear)}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-gray-200 text-sm text-gray-700 hover:bg-gray-50 transition"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        <div className="mt-4 flex items-center gap-3 flex-wrap">
          <label className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md cursor-pointer transition">
            <Upload size={16} />
            {uploading ? 'Uploading...' : 'Upload Statement PDF'}
            <input
              type="file"
              accept=".pdf"
              disabled={uploading}
              onChange={handlePdfUpload}
              className="hidden"
            />
          </label>

          <span className="text-sm text-gray-700">
            Total extracted rows: <span className="font-semibold">{totalRows}</span>
          </span>
        </div>

        <div className="mt-4 max-w-sm">
          <label className="block text-xs font-medium text-gray-500 mb-1">Financial year</label>
          <select
            value={fiscalYear}
            onChange={(e) => handleFiscalYearChange(e.target.value)}
            className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm bg-white"
          >
            <option value="">Select financial year</option>
            {fiscalYearOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>

        {success && (
          <div className="mt-3 px-3 py-2 rounded border border-green-200 bg-green-50 text-green-700 text-sm">
            {success}
          </div>
        )}

        {error && (
          <div className="mt-3 px-3 py-2 rounded border border-red-200 bg-red-50 text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow-md p-4">
        {loading ? (
          <div className="text-sm text-gray-600">Loading statement data...</div>
        ) : months.length === 0 ? (
          <div className="text-sm text-gray-500">
            No statement rows found. Upload a PDF or choose another financial year.
          </div>
        ) : (
          <div className="space-y-5">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <div className="text-sm text-gray-500">Month scale</div>
                <div className="text-sm font-semibold text-gray-900">{getFiscalLabel(fiscalYear)}</div>
              </div>
              <div className="text-sm text-gray-600">
                Showing <span className="font-semibold text-gray-900">{months.length}</span> month group{months.length === 1 ? '' : 's'}
              </div>
            </div>

            <div className="overflow-x-auto pb-2">
              <div className="flex gap-2 min-w-max">
                <button
                  type="button"
                  onClick={() => setActiveMonthKey('ALL')}
                  className={`min-w-[150px] rounded-lg border px-4 py-3 text-left transition ${
                    isAllMonthsSelected
                      ? 'border-blue-600 bg-blue-50 text-blue-700 shadow-sm'
                      : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="text-sm font-semibold">ALL</div>
                  <div className="mt-1 text-xs opacity-80">
                    {months.length} month{months.length === 1 ? '' : 's'}
                  </div>
                  <div className="mt-1 text-xs opacity-80">
                    Rs. {formatMoney(allTotalDeposit)}
                  </div>
                </button>

                {months.map((month) => {
                  const isActive = month.month_key === activeMonth?.month_key
                  const isDeletingThisMonth = deletingMonthKey === month.month_key
                  return (
                    <div
                      key={month.month_key}
                      className={`min-w-[150px] rounded-lg border px-4 py-3 transition relative ${
                        isActive
                          ? 'border-blue-600 bg-blue-50 text-blue-700 shadow-sm'
                          : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => setActiveMonthKey(month.month_key)}
                        className="w-full text-left"
                      >
                        <div className="text-sm font-semibold">{month.month_label}</div>
                        <div className="mt-1 text-xs opacity-80">
                          {month.count} row{month.count === 1 ? '' : 's'}
                        </div>
                        <div className="mt-1 text-xs opacity-80">
                          Rs. {formatMoney(month.total_deposit)}
                        </div>
                      </button>

                      <button
                        type="button"
                        title={`Remove ${month.month_label}`}
                        onClick={() => handleDeleteMonth(month.month_key)}
                        disabled={Boolean(deletingMonthKey)}
                        className="absolute top-2 right-2 h-6 w-6 rounded-full border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-60 disabled:cursor-not-allowed"
                      >
                        {isDeletingThisMonth ? '...' : 'x'}
                      </button>
                    </div>
                  )
                })}
              </div>
            </div>

            {isAllMonthsSelected && (
              <div className="space-y-4">
                <div className="bg-gray-50 px-4 py-3 flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <div className="font-semibold text-gray-900">All Months</div>
                    <div className="text-xs text-gray-500">{getFiscalLabel(fiscalYear)}</div>
                  </div>
                  <div className="text-sm text-gray-700">
                    Rows: <span className="font-semibold">{allRowsCount}</span>
                    {' | '}
                    Total Deposit:{' '}
                    <span className="font-semibold">
                      Rs. {formatMoney(allTotalDeposit)}
                    </span>
                  </div>
                </div>

                {months.map((month) => (
                  <div key={month.month_key} className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-3 flex items-center justify-between flex-wrap gap-2">
                      <div>
                        <div className="font-semibold text-gray-900">{month.month_label}</div>
                        <div className="text-xs text-gray-500">
                          {month.fiscal_year ? `FY ${month.fiscal_year}` : 'Fiscal year unavailable'}
                        </div>
                      </div>
                      <div className="text-sm text-gray-700">
                        Rows: <span className="font-semibold">{month.count}</span>
                        {' | '}
                        Total Deposit: <span className="font-semibold">Rs. {formatMoney(month.total_deposit)}</span>
                      </div>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-100 border-b border-gray-200">
                          <tr>
                            <th className="px-3 py-2 text-left">Value Date</th>
                            <th className="px-3 py-2 text-left">Narration</th>
                            <th className="px-3 py-2 text-left">Cheque No./Ref.No</th>
                            <th className="px-3 py-2 text-right">Deposit</th>
                          </tr>
                        </thead>
                        <tbody>
                          {month.rows.map((row) => (
                            <tr key={row.id || `${month.month_key}-${row.value_date}-${row.reference}-${row.deposit}`} className="border-t border-gray-100">
                              <td className="px-3 py-2 whitespace-nowrap">{row.value_date || '-'}</td>
                              <td className="px-3 py-2">{row.narration || '-'}</td>
                              <td className="px-3 py-2">{row.reference || '-'}</td>
                              <td className="px-3 py-2 text-right font-medium whitespace-nowrap">Rs. {formatMoney(row.deposit)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!isAllMonthsSelected && activeMonth && (
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-3 flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <div className="font-semibold text-gray-900">{activeMonth.month_label}</div>
                    <div className="text-xs text-gray-500">
                      {activeMonth.fiscal_year ? `FY ${activeMonth.fiscal_year}` : 'Fiscal year unavailable'}
                    </div>
                  </div>
                  <div className="text-sm text-gray-700">
                    Rows: <span className="font-semibold">{activeMonth.count}</span>
                    {' | '}
                    Total Deposit: <span className="font-semibold">Rs. {formatMoney(activeMonth.total_deposit)}</span>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-100 border-b border-gray-200">
                      <tr>
                        <th className="px-3 py-2 text-left">Value Date</th>
                        <th className="px-3 py-2 text-left">Narration</th>
                        <th className="px-3 py-2 text-left">Cheque No./Ref.No</th>
                        <th className="px-3 py-2 text-right">Deposit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeMonth.rows.map((row) => (
                        <tr key={row.id || `${activeMonth.month_key}-${row.value_date}-${row.reference}-${row.deposit}`} className="border-t border-gray-100">
                          <td className="px-3 py-2 whitespace-nowrap">{row.value_date || '-'}</td>
                          <td className="px-3 py-2">{row.narration || '-'}</td>
                          <td className="px-3 py-2">{row.reference || '-'}</td>
                          <td className="px-3 py-2 text-right font-medium whitespace-nowrap">Rs. {formatMoney(row.deposit)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}