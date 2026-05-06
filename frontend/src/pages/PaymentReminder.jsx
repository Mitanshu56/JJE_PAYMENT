import React, { useEffect, useMemo, useState } from 'react'
import { paymentRemindersAPI } from '../services/api'

const REMINDER_DAYS_OPTIONS = [20, 30, 45]

function formatDate(value) {
  if (!value) return 'N/A'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10)
  return date.toLocaleDateString('en-GB')
}

function formatDateTime(value) {
  if (!value) return 'N/A'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('en-GB', { hour: 'numeric', minute: 'numeric', hour12: true, day: '2-digit', month: '2-digit', year: 'numeric' })
}

function formatCurrency(value) {
  const amount = Number(value || 0)
  try {
    return amount.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 })
  } catch (e) {
    return `₹${amount.toFixed(2)}`
  }
}

function getStatusLabel(row) {
  if (row?.payment_status === 'Payment Received - Reminder Closed') return 'Reminder Closed'
  if (row?.reminder_active) return 'Reminder Active'
  if (row?.payment_status === 'PAID') return 'Payment Received'
  if (row?.email_status === 'sent') return 'Reminder Sent'
  return 'Unpaid'
}

function historyBadgeClass(status) {
  if (!status) return 'bg-gray-100 text-gray-800'
  const s = String(status).toLowerCase()
  if (s === 'sent' || s === 'sent') return 'bg-green-100 text-green-800'
  if (s === 'failed') return 'bg-red-100 text-red-800'
  if (s === 'stopped') return 'bg-amber-100 text-amber-800'
  if (s === 'payment received' || s.includes('closed')) return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-800'
}

function getNextReminderLabel(row) {
  if (!row?.next_reminder_date) return ''
  if (typeof row?.days_left === 'number') {
    return `Next Reminder In ${row.days_left} Days`
  }
  return 'Next Reminder Scheduled'
}

function PaymentReminder() {
  const [parties, setParties] = useState([])
  const [search, setSearch] = useState('')
  const [selectedPartyName, setSelectedPartyName] = useState('')
  const [selectedParty, setSelectedParty] = useState(null)
  const [partyEmail, setPartyEmail] = useState('')
  const [bills, setBills] = useState([])
  const [activeConfigs, setActiveConfigs] = useState([])
  const [selectedInvoices, setSelectedInvoices] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [savingEmail, setSavingEmail] = useState(false)
  const [sending, setSending] = useState(false)
  const [feedback, setFeedback] = useState({ type: '', message: '' })
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [emailDraft, setEmailDraft] = useState('')
  const [reminderDaysPreset, setReminderDaysPreset] = useState(30)
  const [customReminderDays, setCustomReminderDays] = useState('')
  const [showDeleteHistoryModal, setShowDeleteHistoryModal] = useState(false)
  const [deletePasswordDraft, setDeletePasswordDraft] = useState('')
  const [deletingHistory, setDeletingHistory] = useState(false)

  useEffect(() => {
    loadParties()
    loadHistory()
  }, [])

  const filteredParties = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return parties
    return parties.filter((party) => String(party.party_name || '').toLowerCase().includes(term))
  }, [parties, search])

  const reminderDaysValue = reminderDaysPreset === 'custom'
    ? Number(customReminderDays || 0)
    : Number(reminderDaysPreset || 0)

  const partyHistory = useMemo(() => {
    if (!selectedPartyName) return []
    return history.filter((row) => String(row.partyName || '').toLowerCase() === selectedPartyName.toLowerCase())
  }, [history, selectedPartyName])

  const loadParties = async () => {
    try {
      setLoading(true)
      const res = await paymentRemindersAPI.listParties()
      setParties(res?.data?.parties || [])
    } catch (err) {
      setFeedback({ type: 'error', message: err?.response?.data?.detail || 'Failed to load parties' })
    } finally {
      setLoading(false)
    }
  }

  const loadHistory = async (partyName = '') => {
    try {
      const res = partyName
        ? await paymentRemindersAPI.getHistoryByParty(partyName)
        : await paymentRemindersAPI.getHistory()
      setHistory(res?.data?.history || [])
    } catch (err) {
      setFeedback({ type: 'error', message: err?.response?.data?.detail || 'Failed to load reminder history' })
    }
  }

  const loadParty = async (partyName) => {
    try {
      setLoading(true)
      const res = await paymentRemindersAPI.getParty(partyName)
      const data = res?.data || {}
      setSelectedParty(data)
      setSelectedPartyName(data?.partyName || partyName)
      setPartyEmail(data?.email || '')
      setEmailDraft(data?.email || '')
      setBills(data?.bills || [])
      setActiveConfigs(data?.activeConfigs || [])
      setSelectedInvoices([])
      setFeedback({ type: '', message: '' })
      if (!data?.email) {
        setShowEmailModal(true)
      }
      await loadHistory(data?.partyName || partyName)
    } catch (err) {
      setFeedback({ type: 'error', message: err?.response?.data?.detail || 'Failed to load party data' })
    } finally {
      setLoading(false)
    }
  }

  const handleSelectParty = async (party) => {
    await loadParty(party.party_name)
  }

  const saveEmail = async () => {
    if (!selectedPartyName || !emailDraft.trim()) return
    try {
      setSavingEmail(true)
      await paymentRemindersAPI.savePartyEmail({ party_name: selectedPartyName, email: emailDraft.trim() })
      setPartyEmail(emailDraft.trim())
      setShowEmailModal(false)
      setFeedback({ type: 'success', message: 'Party email saved' })
      await loadParty(selectedPartyName)
    } catch (err) {
      setFeedback({ type: 'error', message: err?.response?.data?.detail || 'Failed to save party email' })
    } finally {
      setSavingEmail(false)
    }
  }

  const toggleInvoice = (invoiceNo) => {
    setSelectedInvoices((current) => {
      if (current.includes(invoiceNo)) {
        return current.filter((value) => value !== invoiceNo)
      }
      return [...current, invoiceNo]
    })
  }

  const sendSingle = async (invoiceNo) => {
    if (!selectedPartyName || !partyEmail) {
      setFeedback({ type: 'error', message: 'Please save the party email first' })
      setShowEmailModal(true)
      return
    }

    try {
      setSending(true)
      const res = await paymentRemindersAPI.sendSingle({
        party_name: selectedPartyName,
        party_email: partyEmail,
        invoice_no: invoiceNo,
        reminder_days: reminderDaysValue,
      })

      if (res?.data?.status === 'failed') {
        throw new Error(res?.data?.error_message || 'Failed to send reminder')
      }

      setFeedback({ type: 'success', message: 'Reminder sent and history updated' })
      await loadParty(selectedPartyName)
    } catch (err) {
      setFeedback({ type: 'error', message: err?.response?.data?.detail || err?.message || 'Failed to send reminder' })
      await loadHistory(selectedPartyName)
    } finally {
      setSending(false)
    }
  }

  const sendMultiple = async () => {
    if (!selectedPartyName || !partyEmail) {
      setFeedback({ type: 'error', message: 'Please save the party email first' })
      setShowEmailModal(true)
      return
    }

    if (selectedInvoices.length === 0) {
      setFeedback({ type: 'error', message: 'Select at least one invoice' })
      return
    }

    try {
      setSending(true)
      const res = await paymentRemindersAPI.sendMultiple({
        party_name: selectedPartyName,
        party_email: partyEmail,
        invoice_numbers: selectedInvoices,
        reminder_days: reminderDaysValue,
      })

      if (res?.data?.status === 'failed') {
        throw new Error(res?.data?.error_message || 'Failed to send reminder')
      }

      setSelectedInvoices([])
      setFeedback({ type: 'success', message: 'Multiple reminder sent and history updated' })
      await loadParty(selectedPartyName)
    } catch (err) {
      setFeedback({ type: 'error', message: err?.response?.data?.detail || err?.message || 'Failed to send reminder' })
      await loadHistory(selectedPartyName)
    } finally {
      setSending(false)
    }
  }

  const stopInvoice = async (invoiceNo) => {
    if (!selectedPartyName) return
    try {
      setSending(true)
      const res = await paymentRemindersAPI.stopInvoice(invoiceNo, selectedPartyName)
      setFeedback({ type: 'success', message: 'Reminder stopped successfully' })
      await loadParty(selectedPartyName)
      await loadHistory(selectedPartyName)
    } catch (err) {
      setFeedback({ type: 'error', message: err?.response?.data?.detail || err?.message || 'Failed to stop reminder' })
      await loadHistory(selectedPartyName)
    } finally {
      setSending(false)
    }
  }

  const deleteHistoryByParty = async () => {
    if (!selectedPartyName || !deletePasswordDraft.trim()) return
    try {
      setDeletingHistory(true)
      await paymentRemindersAPI.deleteHistoryByParty(selectedPartyName, deletePasswordDraft.trim())
      setFeedback({ type: 'success', message: 'History deleted and reminders reset successfully' })
      setShowDeleteHistoryModal(false)
      setDeletePasswordDraft('')
      setHistory([])
      await loadParty(selectedPartyName)
      await loadHistory(selectedPartyName)
    } catch (err) {
      if (err?.response?.status === 401) {
        setFeedback({ type: 'error', message: 'Invalid current password' })
      } else {
        setFeedback({ type: 'error', message: err?.response?.data?.detail || err?.message || 'Failed to delete history' })
      }
    } finally {
      setDeletingHistory(false)
    }
  }

  const selectedCount = selectedInvoices.length

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Payment Reminder</h1>
            <p className="text-sm text-gray-600">Unpaid invoices only. Active reminders are disabled until payment is received.</p>
          </div>
          <button
            type="button"
            onClick={() => selectedPartyName ? setShowEmailModal(true) : null}
            className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-100 disabled:opacity-50"
            disabled={!selectedPartyName}
          >
            Edit Email
          </button>
        </div>

        {feedback.message && (
          <div className={`rounded-lg border px-4 py-3 text-sm ${feedback.type === 'success' ? 'border-green-200 bg-green-50 text-green-700' : 'border-red-200 bg-red-50 text-red-700'}`}>
            {feedback.message}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search party"
              className="mb-4 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            <div className="max-h-[70vh] space-y-2 overflow-auto pr-1">
              {loading && !parties.length && <div className="text-sm text-gray-500">Loading...</div>}
              {filteredParties.map((party) => (
                <button
                  key={party.party_name}
                  type="button"
                  onClick={() => handleSelectParty(party)}
                  className={`w-full rounded-xl border px-3 py-3 text-left transition ${selectedPartyName === party.party_name ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-white hover:bg-gray-50'}`}
                >
                  <div className="font-semibold text-gray-900">{party.party_name}</div>
                  <div className="mt-1 text-xs text-gray-600">Unpaid invoices: {party.invoice_count || 0}</div>
                  <div className="text-xs text-gray-600">Pending: {formatCurrency(party.pending_amount || 0)}</div>
                </button>
              ))}
              {!loading && filteredParties.length === 0 && <div className="text-sm text-gray-500">No parties found</div>}
            </div>
          </aside>

          <section className="space-y-6 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            {!selectedPartyName ? (
              <div className="rounded-xl border border-dashed border-gray-300 p-8 text-sm text-gray-600">Select a party to view invoices and reminders.</div>
            ) : (
              <>
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">{selectedPartyName}</h2>
                    <div className="mt-2 text-sm text-gray-600">Email: {partyEmail || 'Not set'}</div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-700">Reminder Days: {reminderDaysPreset === 'custom' ? `Custom - ${reminderDaysValue || 0} days` : `${reminderDaysPreset} days`}</span>
                    <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">Reminder Sent / Active Configs: {activeConfigs.length}</span>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">Party Email</label>
                    <div className="flex gap-2">
                      <input
                        value={partyEmail}
                        readOnly
                        className="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm"
                      />
                      <button
                        type="button"
                        onClick={() => { setEmailDraft(partyEmail || ''); setShowEmailModal(true) }}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                      >
                        {partyEmail ? 'Update Email' : 'Add Email'}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">Reminder Days</label>
                    <div className="flex gap-2">
                      {REMINDER_DAYS_OPTIONS.map((option) => (
                        <button
                          key={option}
                          type="button"
                          onClick={() => setReminderDaysPreset(option)}
                          className={`rounded-lg border px-3 py-2 text-sm font-semibold ${reminderDaysPreset === option ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-300 bg-white text-gray-700'}`}
                        >
                          {option}
                        </button>
                      ))}
                      <button
                        type="button"
                        onClick={() => setReminderDaysPreset('custom')}
                        className={`rounded-lg border px-3 py-2 text-sm font-semibold ${reminderDaysPreset === 'custom' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-300 bg-white text-gray-700'}`}
                      >
                        Custom
                      </button>
                    </div>
                    {reminderDaysPreset === 'custom' && (
                      <input
                        type="number"
                        min="1"
                        value={customReminderDays}
                        onChange={(e) => setCustomReminderDays(e.target.value)}
                        placeholder="Enter custom days"
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                      />
                    )}
                  </div>
                </div>

                <div className="overflow-hidden rounded-2xl border border-gray-200">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                      <tr>
                        <th className="px-3 py-3"></th>
                        <th className="px-3 py-3">Invoice No</th>
                        <th className="px-3 py-3">Invoice Date</th>
                        <th className="px-3 py-3">Invoice Amount</th>
                        <th className="px-3 py-3">Pending Amount</th>
                        <th className="px-3 py-3">Payment Status</th>
                        <th className="px-3 py-3">Reminder Status</th>
                        <th className="px-3 py-3">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {bills.map((invoice) => {
                        const invoiceNo = String(invoice.invoice_no || '')
                        const active = Boolean(invoice.reminder_active)
                        const statusLabel = getStatusLabel(invoice)
                        return (
                          <tr key={invoice._id || invoiceNo} className={active ? 'bg-blue-50/50' : ''}>
                            <td className="px-3 py-3 align-top">
                              <input
                                type="checkbox"
                                checked={selectedInvoices.includes(invoiceNo)}
                                disabled={active}
                                onChange={() => toggleInvoice(invoiceNo)}
                                className="h-4 w-4 rounded border-gray-300 text-blue-600 disabled:opacity-50"
                              />
                            </td>
                            <td className="px-3 py-3 align-top font-medium text-gray-900">{invoiceNo}</td>
                            <td className="px-3 py-3 align-top text-gray-700">{formatDate(invoice.invoice_date)}</td>
                            <td className="px-3 py-3 align-top text-gray-700">{formatCurrency(invoice.grand_total)}</td>
                            <td className="px-3 py-3 align-top text-gray-700">{formatCurrency(invoice.pending_amount)}</td>
                            <td className="px-3 py-3 align-top">
                              <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-700">{invoice.payment_status || 'UNPAID'}</span>
                            </td>
                            <td className="px-3 py-3 align-top">
                              <div className="space-y-1">
                                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${active ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>{statusLabel}</span>
                                {active && (
                                  <div className="text-xs font-medium text-blue-700">{getNextReminderLabel(invoice)}</div>
                                )}
                                {invoice.next_reminder_date && (
                                  <div className="text-xs text-gray-600">Next Reminder: {formatDateTime(invoice.next_reminder_date)}</div>
                                )}
                                {typeof invoice.days_left === 'number' && (
                                  <div className="text-xs text-gray-600">Days Left: {invoice.days_left}</div>
                                )}
                              </div>
                            </td>
                            <td className="px-3 py-3 align-top flex gap-2">
                              {active ? (
                                <>
                                  <button type="button" disabled className="rounded-lg border border-gray-300 bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-700">Reminder Active</button>
                                  <button type="button" onClick={() => stopInvoice(invoiceNo)} disabled={sending} className="rounded-lg border border-red-400 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50">Stop Reminder</button>
                                </>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => sendSingle(invoiceNo)}
                                  disabled={sending}
                                  className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-400"
                                >
                                  Send Single
                                </button>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                      {bills.length === 0 && (
                        <tr>
                          <td colSpan="8" className="px-3 py-8 text-center text-sm text-gray-500">No unpaid invoices available for reminders.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="flex items-center justify-between gap-4">
                  <div className="text-sm text-gray-600">{selectedCount} invoice(s) selected for multiple reminder</div>
                  <button
                    type="button"
                    onClick={sendMultiple}
                    disabled={selectedCount === 0 || sending}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
                  >
                    {sending ? 'Sending...' : 'Send Multiple'}
                  </button>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">Reminder History</h3>
                      <p className="text-sm text-gray-600">Latest entries first. History is permanent.</p>
                    </div>
                    {selectedPartyName && partyHistory.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setShowDeleteHistoryModal(true)}
                        className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-100"
                      >
                        Delete All History
                      </button>
                    )}
                  </div>
                  <div className="overflow-x-auto rounded-2xl border border-gray-200">
                    <div style={{ minWidth: 1100 }}>
                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                      <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                        <tr>
                          <th className="px-3 py-3">Party</th>
                          <th className="px-3 py-3">Email</th>
                          <th className="px-3 py-3">Type</th>
                          <th className="px-3 py-3">Invoice Numbers</th>
                          <th className="px-3 py-3">Invoice Dates</th>
                          <th className="px-3 py-3">Total Pending</th>
                          <th className="px-3 py-3">Reminder Days</th>
                          <th className="px-3 py-3">Sent At</th>
                          <th className="px-3 py-3">Status</th>
                          <th className="px-3 py-3">Next Reminder</th>
                          <th className="px-3 py-3">Days Left</th>
                          <th className="px-3 py-3">Payment Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 bg-white">
                        {partyHistory.map((row) => (
                          <tr key={row._id}>
                            <td className="px-3 py-3 text-gray-900">{row.partyName}</td>
                            <td className="px-3 py-3 text-gray-700 break-words max-w-[200px]">{row.partyEmail}</td>
                            <td className="px-3 py-3 text-gray-700">{row.reminderType}</td>
                            <td className="px-3 py-3 text-gray-700">{(row.invoiceNumbers || []).join(', ')}</td>
                            <td className="px-3 py-3 text-gray-700">{(row.invoiceDates || []).map(formatDate).join('\n')}</td>
                            <td className="px-3 py-3 text-right text-gray-700">{formatCurrency(row.totalPendingAmount)}</td>
                            <td className="px-3 py-3 text-gray-700">{row.reminderDaysLabel || row.reminderDays}</td>
                            <td className="px-3 py-3 text-gray-700">{formatDateTime(row.sentAt)}</td>
                            <td className="px-3 py-3"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${historyBadgeClass(row.emailStatus)}`}>{row.emailStatus || row.emailStatus || 'N/A'}</span></td>
                            <td className="px-3 py-3 text-gray-700">{formatDate(row.nextReminderDate)}</td>
                            <td className="px-3 py-3 text-gray-700">{row.daysLeft ?? 'N/A'}</td>
                            <td className="px-3 py-3 text-gray-700">{row.paymentStatus}</td>
                          </tr>
                        ))}
                        {partyHistory.length === 0 && (
                          <tr>
                            <td colSpan="12" className="px-3 py-8 text-center text-sm text-gray-500">No reminder history yet for this party.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                    </div>
                  </div>
                </div>
              </>
            )}
          </section>
        </div>
      </div>

      {showEmailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-xl font-bold text-gray-900">Party Email</h3>
            <p className="mt-1 text-sm text-gray-600">Enter or update the email address for {selectedPartyName}.</p>
            <div className="mt-4 space-y-2">
              <label className="block text-sm font-medium text-gray-700">Email Address</label>
              <input
                type="email"
                value={emailDraft}
                onChange={(e) => setEmailDraft(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder="party@example.com"
              />
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowEmailModal(false)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={saveEmail}
                disabled={savingEmail}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
              >
                {savingEmail ? 'Saving...' : 'Save Email'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showDeleteHistoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-xl font-bold text-red-700">Delete Payment Reminder History</h3>
            <p className="mt-3 text-sm text-gray-600">
              This action will permanently delete all payment reminder history for <strong>{selectedPartyName}</strong> and reset reminder tracking for unpaid invoices. Invoices and payment records will not be deleted.
            </p>
            <div className="mt-4 space-y-2">
              <label className="block text-sm font-medium text-gray-700">Enter Your Current Account Password</label>
              <input
                type="password"
                value={deletePasswordDraft}
                onChange={(e) => setDeletePasswordDraft(e.target.value)}
                placeholder="Enter your current account password"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowDeleteHistoryModal(false)
                  setDeletePasswordDraft('')
                }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={deleteHistoryByParty}
                disabled={deletingHistory || !deletePasswordDraft.trim()}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-gray-400"
              >
                {deletingHistory ? 'Deleting...' : 'Delete History'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PaymentReminder