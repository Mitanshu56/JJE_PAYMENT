import React, { useEffect, useMemo, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { statementsAPI } from '../../services/api'

const PAGE_SIZE = 200

function formatMoney(value) {
  return Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })
}

function normalizeArray(value) {
  return Array.isArray(value) ? value : []
}

function sumMoney(items, field) {
  return normalizeArray(items).reduce((total, item) => total + Number(item?.[field] || 0), 0)
}

function formatApiError(err, fallback = 'Failed to load statement match data') {
  const detail = err?.response?.data?.detail

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    const firstMsg = detail.find((item) => typeof item?.msg === 'string')?.msg
    if (firstMsg) return firstMsg
    return fallback
  }

  if (detail && typeof detail === 'object') {
    if (typeof detail.msg === 'string') return detail.msg
    return fallback
  }

  if (typeof err?.message === 'string' && err.message.trim()) {
    return err.message
  }

  return fallback
}

function getGroupTone(isMatched) {
  if (isMatched) {
    return {
      card: 'border-emerald-300 bg-emerald-50/40',
      header: 'bg-emerald-100 border-emerald-200',
      title: 'text-emerald-900',
      badge: 'bg-emerald-600 text-white',
      neftHead: 'bg-sky-100 border-sky-200 text-sky-900',
      invoiceHead: 'bg-emerald-100 border-emerald-200 text-emerald-900',
      neftRowOdd: 'bg-sky-50/50',
      neftRowEven: 'bg-white',
      invoiceRowOdd: 'bg-emerald-50/40',
      invoiceRowEven: 'bg-white',
      summaryBand: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    }
  }

  return {
    card: 'border-amber-300 bg-amber-50/40',
    header: 'bg-amber-100 border-amber-200',
    title: 'text-amber-900',
    badge: 'bg-amber-600 text-white',
    neftHead: 'bg-orange-100 border-orange-200 text-orange-900',
    invoiceHead: 'bg-amber-100 border-amber-200 text-amber-900',
    neftRowOdd: 'bg-orange-50/40',
    neftRowEven: 'bg-white',
    invoiceRowOdd: 'bg-amber-50/40',
    invoiceRowEven: 'bg-white',
    summaryBand: 'bg-amber-50 border-amber-200 text-amber-900',
  }
}

export default function StatementMatchTab() {
  const [rows, setRows] = useState([])
  const [summary, setSummary] = useState(null)
  const [filters, setFilters] = useState({ page: 1, pageSize: PAGE_SIZE })
  const [pagination, setPagination] = useState({ page: 1, pageSize: PAGE_SIZE, totalPages: 0 })
  const [partyOptions, setPartyOptions] = useState([])
  const [partySearch, setPartySearch] = useState('')
  const [partyDropdownOpen, setPartyDropdownOpen] = useState(false)
  const [matchFilter, setMatchFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const visiblePartyOptions = useMemo(() => {
    const q = partySearch.trim().toLowerCase()
    if (!q) return partyOptions

    return partyOptions.filter((party) => party.toLowerCase().includes(q))
  }, [partyOptions, partySearch])

  const displayedRows = useMemo(() => {
    const neftRows = normalizeArray(rows).filter((item) => {
      const narration = String(item?.statement_entry?.narration || '').toUpperCase()
      return narration.includes('NEFT')
    })

    const q = partySearch.trim().toLowerCase()
    if (!q) return neftRows

    return neftRows.filter((item) => {
      const party = String(item?.matched_party?.party_name || '').toLowerCase()
      const extracted = String(item?.extracted_party_name || '').toLowerCase()
      return party.includes(q) || extracted.includes(q)
    })
  }, [rows, partySearch])

  const filteredRows = useMemo(() => {
    if (matchFilter === 'matched') {
      return displayedRows.filter((item) => Boolean(item?.matched))
    }
    if (matchFilter === 'unmatched') {
      return displayedRows.filter((item) => !item?.matched)
    }
    return displayedRows
  }, [displayedRows, matchFilter])

  const displayedSummary = useMemo(() => {
    const matchedRows = filteredRows.filter((item) => item.matched).length
    return {
      page_rows: filteredRows.length,
      matched_rows: matchedRows,
      unmatched_rows: filteredRows.length - matchedRows,
    }
  }, [filteredRows])

  const groupedRows = useMemo(() => {
    const groups = new Map()

    normalizeArray(filteredRows).forEach((item) => {
      const matchedPartyName = String(item?.matched_party?.party_name || '').trim()
      const extractedName = String(item?.extracted_party_name || '').trim()
      const groupKey = matchedPartyName || `UNMATCHED::${extractedName || 'UNKNOWN'}`

      if (!groups.has(groupKey)) {
        groups.set(groupKey, {
          key: groupKey,
          matched: Boolean(matchedPartyName),
          partyName: matchedPartyName,
          extractedName,
          matchedParty: item?.matched_party || null,
          neftRows: [],
          totalDeposit: 0,
          invoices: [],
          invoiceKeys: new Set(),
        })
      }

      const group = groups.get(groupKey)
      group.neftRows.push(item)
      group.totalDeposit += Number(item?.statement_entry?.deposit || 0)

      normalizeArray(item?.invoices).forEach((invoice) => {
        const invoiceKey = String(invoice?.id || invoice?.invoice_no || '')
        if (!invoiceKey || group.invoiceKeys.has(invoiceKey)) return
        group.invoiceKeys.add(invoiceKey)
        group.invoices.push(invoice)
      })
    })

    return Array.from(groups.values())
  }, [filteredRows])

  const loadRows = async (nextFilters = filters) => {
    try {
      setLoading(true)
      setError('')

      const matchRes = await statementsAPI.getMatch({
        ...nextFilters,
        neftOnly: true,
      })

      const matchData = matchRes?.data || {}

      setRows(matchData.rows || [])
      setSummary(matchData.summary || null)
      setPagination({
        page: Number(matchData?.pagination?.page || nextFilters.page || 1),
        pageSize: Number(matchData?.pagination?.page_size || nextFilters.pageSize || PAGE_SIZE),
        totalPages: Number(matchData?.pagination?.total_pages || 0),
      })

      const parties = Array.from(
        new Set(
          (matchData.available_parties || [])
            .map((party) => String(party || '').trim())
            .filter(Boolean),
        ),
      ).sort((a, b) => a.localeCompare(b))

      setPartyOptions(parties)
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRows(filters)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.page])

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow-md p-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Statement Match</h3>
            <p className="text-sm text-gray-600 mt-1">
              Search by NEFT extracted party name and view mapped invoice payment details.
            </p>
          </div>

          <button
            type="button"
            onClick={() => loadRows(filters)}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-gray-200 text-sm text-gray-700 hover:bg-gray-50 transition"
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        <div className="mt-4 max-w-sm">
          <label className="block text-xs font-medium text-gray-500 mb-1">Party search</label>
          <div className="relative">
            <div className="flex items-center rounded-md border border-gray-200 bg-white overflow-hidden focus-within:ring-2 focus-within:ring-blue-200">
              <input
                type="text"
                value={partySearch}
                onChange={(e) => {
                  setPartySearch(e.target.value)
                  setPartyDropdownOpen(true)
                }}
                onFocus={() => setPartyDropdownOpen(true)}
                placeholder="Type or select party name"
                className="w-full px-3 py-2 text-sm bg-white outline-none"
              />
              <button
                type="button"
                onClick={() => setPartyDropdownOpen((prev) => !prev)}
                className="px-3 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-50 border-l border-gray-200"
                aria-label="Toggle party list"
              >
                ▾
              </button>
            </div>

            {partyDropdownOpen && (
              <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-lg overflow-hidden">
                <div className="max-h-56 overflow-y-auto py-1">
                  {visiblePartyOptions.length > 0 ? (
                    visiblePartyOptions.map((party) => (
                      <button
                        key={party}
                        type="button"
                        onClick={() => {
                          setPartySearch(party)
                          setPartyDropdownOpen(false)
                        }}
                        className="w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700"
                      >
                        {party}
                      </button>
                    ))
                  ) : (
                    <div className="px-3 py-2 text-sm text-gray-500">No party found</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setMatchFilter('all')}
            className={`px-3 py-1.5 rounded border text-sm ${matchFilter === 'all' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'}`}
          >
            All
          </button>
          <button
            type="button"
            onClick={() => setMatchFilter('matched')}
            className={`px-3 py-1.5 rounded border text-sm ${matchFilter === 'matched' ? 'bg-green-600 text-white border-green-600' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'}`}
          >
            Matched
          </button>
          <button
            type="button"
            onClick={() => setMatchFilter('unmatched')}
            className={`px-3 py-1.5 rounded border text-sm ${matchFilter === 'unmatched' ? 'bg-amber-600 text-white border-amber-600' : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'}`}
          >
            Unmatched
          </button>
        </div>

        {(summary || displayedSummary) && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
              <div className="text-xs text-gray-500">NEFT Rows</div>
              <div className="text-lg font-semibold text-gray-900">{displayedSummary.page_rows || 0}</div>
            </div>
            <div className="rounded border border-green-200 bg-green-50 px-3 py-2">
              <div className="text-xs text-green-700">Matched</div>
              <div className="text-lg font-semibold text-green-800">{displayedSummary.matched_rows || 0}</div>
            </div>
            <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2">
              <div className="text-xs text-amber-700">Unmatched</div>
              <div className="text-lg font-semibold text-amber-800">{displayedSummary.unmatched_rows || 0}</div>
            </div>
            <div className="rounded border border-blue-200 bg-blue-50 px-3 py-2">
              <div className="text-xs text-blue-700">Total NEFT Rows</div>
              <div className="text-lg font-semibold text-blue-800">{summary?.total_rows || 0}</div>
            </div>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between gap-3 flex-wrap">
          <div className="text-xs text-gray-500">
            Page {pagination.page || 1} of {pagination.totalPages || 1}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={loading || (pagination.page || 1) <= 1}
              onClick={() => setFilters((prev) => ({ ...prev, page: Math.max(1, Number(prev.page || 1) - 1) }))}
              className="px-3 py-1.5 rounded border border-gray-200 text-sm text-gray-700 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={loading || (pagination.totalPages || 0) <= (pagination.page || 1)}
              onClick={() => setFilters((prev) => ({ ...prev, page: Number(prev.page || 1) + 1 }))}
              className="px-3 py-1.5 rounded border border-gray-200 text-sm text-gray-700 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-3 px-3 py-2 rounded border border-red-200 bg-red-50 text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow-md p-4">
        {loading ? (
          <div className="text-sm text-gray-600">Loading statement match rows...</div>
        ) : filteredRows.length === 0 ? (
          <div className="text-sm text-gray-500">No NEFT rows found for selected party search.</div>
        ) : (
          <div className="space-y-4">
            {groupedRows.map((group) => {
              const invoices = normalizeArray(group?.invoices)
              const tone = getGroupTone(group.matched)
              const invoiceGrandTotal = Number(group?.matchedParty?.invoice_grand_total ?? sumMoney(invoices, 'grand_total'))
              const invoicePaidTotal = Number(group?.matchedParty?.invoice_paid_total ?? sumMoney(invoices, 'paid_amount'))
              const invoicePendingTotal = Number(group?.matchedParty?.invoice_pending_total ?? sumMoney(invoices, 'remaining_amount'))
              const totalReceivedWithNeft = Math.min(invoiceGrandTotal, invoicePaidTotal + Number(group.totalDeposit || 0))
              const adjustedPendingTotal = Math.max(0, invoiceGrandTotal - totalReceivedWithNeft)
              const isSettledAfterNeft = adjustedPendingTotal <= 0.001

              return (
              <div key={group.key} className={`border rounded-lg overflow-hidden shadow-sm ${tone.card}`}>
                <div className={`px-4 py-3 flex items-start justify-between gap-3 flex-wrap border-b ${tone.header}`}>
                  <div>
                    <div className={`text-sm font-semibold ${tone.title}`}>
                      {group.matched ? group.partyName : `Unmatched - ${group.extractedName || 'Unknown'}`}
                    </div>
                    <div className="text-xs text-gray-600 mt-1">
                      NEFT rows: {group.neftRows.length}
                    </div>
                    <div className="text-xs text-gray-600 mt-1">
                      Total NEFT deposit: <span className="font-semibold text-gray-900">Rs. {formatMoney(group.totalDeposit)}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`inline-flex text-xs px-2 py-1 rounded-full font-semibold ${tone.badge}`}>
                      {group.matched ? 'Matched' : 'Unmatched'}
                    </div>
                    {group.matched && (
                      <div className={`mt-1 inline-flex text-xs px-2 py-1 rounded-full font-semibold ${isSettledAfterNeft ? 'bg-green-600 text-white' : 'bg-amber-500 text-white'}`}>
                        {isSettledAfterNeft ? 'Paid' : 'Pending'}
                      </div>
                    )}
                    {group.matched && (
                      <div className="text-xs text-gray-600 mt-1">
                        Invoices: {invoices.length}
                      </div>
                    )}
                  </div>
                </div>

                <div className="overflow-x-auto border-t border-gray-100">
                  <table className="w-full text-sm">
                    <thead className={`border-b ${tone.neftHead}`}>
                      <tr>
                        <th className="px-3 py-2 text-left">NEFT Date</th>
                        <th className="px-3 py-2 text-left">Narration</th>
                        <th className="px-3 py-2 text-left">Reference</th>
                        <th className="px-3 py-2 text-right">Deposit</th>
                        <th className="px-3 py-2 text-left">Extracted Party</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.neftRows.map((item, idx) => (
                        <tr
                          key={item.statement_entry?.id || `${item.statement_entry?.value_date}-${item.statement_entry?.deposit}`}
                          className={`border-t border-gray-100 ${idx % 2 === 0 ? tone.neftRowEven : tone.neftRowOdd}`}
                        >
                          <td className="px-3 py-2 whitespace-nowrap">{item.statement_entry?.value_date || '-'}</td>
                          <td className="px-3 py-2">{item.statement_entry?.narration || '-'}</td>
                          <td className="px-3 py-2">{item.statement_entry?.reference || '-'}</td>
                          <td className="px-3 py-2 text-right">Rs. {formatMoney(item.statement_entry?.deposit)}</td>
                          <td className="px-3 py-2">{item.extracted_party_name || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {group.matched ? (
                  <div className="p-4 space-y-3">
                    <div className={`text-sm px-3 py-2 rounded border ${tone.summaryBand}`}>
                      Party: <span className="font-semibold text-gray-900">{group.matchedParty?.party_name || group.partyName}</span>
                      {' | '}Invoices: <span className="font-semibold text-gray-900">{group.matchedParty?.invoice_count || invoices.length}</span>
                      {' | '}Invoice Grand Total: <span className="font-semibold text-slate-700">Rs. {formatMoney(invoiceGrandTotal)}</span>
                      {' | '}Paid (incl. NEFT): <span className="font-semibold text-green-700">Rs. {formatMoney(totalReceivedWithNeft)}</span>
                      {' | '}Pending (after NEFT): <span className="font-semibold text-amber-700">Rs. {formatMoney(adjustedPendingTotal)}</span>
                      {' | '}NEFT Deposit: <span className="font-semibold text-blue-700">Rs. {formatMoney(group.totalDeposit)}</span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className={`border-b ${tone.invoiceHead}`}>
                          <tr>
                            <th className="px-3 py-2 text-left">Invoice No</th>
                            <th className="px-3 py-2 text-left">Invoice Date</th>
                            <th className="px-3 py-2 text-right">Grand Total</th>
                            <th className="px-3 py-2 text-right">Paid</th>
                            <th className="px-3 py-2 text-right">Pending</th>
                            <th className="px-3 py-2 text-left">Status</th>
                            <th className="px-3 py-2 text-left">Payment IDs</th>
                          </tr>
                        </thead>
                        <tbody>
                          {invoices.map((invoice, idx) => {
                            const paymentIds = normalizeArray(invoice?.matched_payment_ids)

                            return (
                            <tr
                              key={invoice.id || invoice.invoice_no}
                              className={`border-t border-gray-100 ${idx % 2 === 0 ? tone.invoiceRowEven : tone.invoiceRowOdd}`}
                            >
                              <td className="px-3 py-2 whitespace-nowrap">{invoice.invoice_no || '-'}</td>
                              <td className="px-3 py-2 whitespace-nowrap">{invoice.invoice_date || '-'}</td>
                              <td className="px-3 py-2 text-right">Rs. {formatMoney(invoice.grand_total)}</td>
                              <td className="px-3 py-2 text-right text-green-700">Rs. {formatMoney(invoice.paid_amount)}</td>
                              <td className="px-3 py-2 text-right text-amber-700">Rs. {formatMoney(invoice.remaining_amount)}</td>
                              <td className="px-3 py-2">{invoice.status || '-'}</td>
                              <td className="px-3 py-2">{paymentIds.join(', ') || '-'}</td>
                            </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <div className="px-4 py-3 text-sm text-amber-700 bg-amber-50 border-t border-amber-200">
                    Could not map this statement row to any invoice party. You can improve this by keeping party names cleaner in narration.
                  </div>
                )}
              </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
