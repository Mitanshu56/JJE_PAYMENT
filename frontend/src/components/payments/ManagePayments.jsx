import React, { useEffect, useMemo, useState } from 'react'
import { paymentsAPI } from '../../services/api'

const PAYMENT_MODES = ['CASH', 'CHEQUE', 'NEFT', 'UPI']

const getTodayISO = () => new Date().toISOString().slice(0, 10)

export default function ManagePayments({ bills, onPaymentSaved }) {
  const [partySearch, setPartySearch] = useState('')
  const [selectedParty, setSelectedParty] = useState(null)
  const [historyParty, setHistoryParty] = useState(null)
  const [showPaymentHistory, setShowPaymentHistory] = useState(false)
  const [selectedInvoices, setSelectedInvoices] = useState({})
  const [paymentMode, setPaymentMode] = useState('CASH')
  const [actualReceivedAmount, setActualReceivedAmount] = useState('')
  const [chequeDate, setChequeDate] = useState(getTodayISO())
  const [partyBankName, setPartyBankName] = useState('')
  const [chequeAmount, setChequeAmount] = useState('')
  const [depositDate, setDepositDate] = useState(getTodayISO())
  const [upiId, setUpiId] = useState('')
  const [upiTransferDate, setUpiTransferDate] = useState(getTodayISO())
  const [reference, setReference] = useState('')
  const [notes, setNotes] = useState('')
  const [partyPayments, setPartyPayments] = useState([])
  const [historyPayments, setHistoryPayments] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState(null)
  const [editingPayment, setEditingPayment] = useState(null)
  const [editSelectedInvoices, setEditSelectedInvoices] = useState({})
  const [editPaymentMode, setEditPaymentMode] = useState('CASH')
  const [editAmount, setEditAmount] = useState('')
  const [editActualReceivedAmount, setEditActualReceivedAmount] = useState('')
  const [editReference, setEditReference] = useState('')
  const [editNotes, setEditNotes] = useState('')
  const [editChequeDate, setEditChequeDate] = useState(getTodayISO())
  const [editPartyBankName, setEditPartyBankName] = useState('')
  const [editChequeAmount, setEditChequeAmount] = useState('')
  const [editDepositDate, setEditDepositDate] = useState(getTodayISO())
  const [editUpiId, setEditUpiId] = useState('')
  const [editUpiTransferDate, setEditUpiTransferDate] = useState(getTodayISO())
  const [editError, setEditError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const safeBills = Array.isArray(bills) ? bills : []

  const partyGroups = useMemo(() => {
    const groups = {}

    for (const bill of safeBills) {
      const partyName = bill?.party_name || 'Unknown Party'
      if (!groups[partyName]) {
        groups[partyName] = []
      }
      groups[partyName].push(bill)
    }

    return Object.entries(groups)
      .map(([partyName, partyBills]) => {
        const dueAmount = partyBills.reduce((sum, b) => sum + Number(b?.remaining_amount ?? b?.grand_total ?? 0), 0)
        const receivedAmount = partyBills.reduce((sum, b) => sum + Number(b?.paid_amount ?? 0), 0)
        return {
          partyName,
          bills: partyBills,
          dueAmount,
          receivedAmount,
          totalInvoices: partyBills.length,
        }
      })
      .sort((a, b) => b.dueAmount - a.dueAmount)
  }, [safeBills])

  const filteredParties = useMemo(() => {
    const term = partySearch.trim().toLowerCase()
    if (!term) {
      return partyGroups
    }
    return partyGroups.filter((p) => p.partyName.toLowerCase().includes(term))
  }, [partyGroups, partySearch])

  useEffect(() => {
    if (selectedParty?.partyName) {
      const updatedSelectedParty = partyGroups.find((p) => p.partyName === selectedParty.partyName)
      if (updatedSelectedParty && updatedSelectedParty !== selectedParty) {
        setSelectedParty(updatedSelectedParty)
      }
    }

    if (historyParty?.partyName) {
      const updatedHistoryParty = partyGroups.find((p) => p.partyName === historyParty.partyName)
      if (updatedHistoryParty && updatedHistoryParty !== historyParty) {
        setHistoryParty(updatedHistoryParty)
      }
    }
  }, [partyGroups, selectedParty, historyParty])

  const openReceivePopup = async (party) => {
    setSelectedParty(party)
    setSelectedInvoices({})
    setPaymentMode('CASH')
    setActualReceivedAmount('')
    setChequeDate(getTodayISO())
    setPartyBankName('')
    setChequeAmount('')
    setDepositDate(getTodayISO())
    setUpiId('')
    setUpiTransferDate(getTodayISO())
    setReference('')
    setNotes('')
    setError(null)

    setPartyPayments(await fetchPaymentsByParty(party.partyName))
  }

  const fetchPaymentsByParty = async (partyName) => {
    try {
      const res = await paymentsAPI.getByParty(partyName)
      return Array.isArray(res?.data?.payments) ? res.data.payments : []
    } catch (e) {
      return []
    }
  }

  const sortPaymentsByDateDesc = (payments) => {
    return [...payments].sort((a, b) => {
      const aTime = new Date(a?.payment_date || a?.created_at || 0).getTime()
      const bTime = new Date(b?.payment_date || b?.created_at || 0).getTime()
      return bTime - aTime
    })
  }

  const syncAfterPaymentMutation = async (partyName) => {
    await Promise.resolve(onPaymentSaved?.())

    if (!partyName) return

    const refreshedPayments = await fetchPaymentsByParty(partyName)
    const sortedPayments = sortPaymentsByDateDesc(refreshedPayments)

    if (selectedParty?.partyName === partyName) {
      setPartyPayments(sortedPayments)
    }

    if (historyParty?.partyName === partyName) {
      setHistoryPayments(sortedPayments)
    }
  }

  const closeReceivePopup = () => {
    setSelectedParty(null)
    setSelectedInvoices({})
    setActualReceivedAmount('')
    setChequeDate(getTodayISO())
    setPartyBankName('')
    setChequeAmount('')
    setDepositDate(getTodayISO())
    setUpiId('')
    setUpiTransferDate(getTodayISO())
    setPartyPayments([])
    setError(null)
  }

  const openPaymentHistoryPopup = async (party) => {
    setHistoryParty(party)
    setShowPaymentHistory(true)
    setHistoryLoading(true)
    setHistoryError(null)

    try {
      const payments = await fetchPaymentsByParty(party.partyName)
      const sortedPayments = sortPaymentsByDateDesc(payments)
      setHistoryPayments(sortedPayments)
    } catch (e) {
      setHistoryPayments([])
      setHistoryError('Failed to load payment history for this party.')
    } finally {
      setHistoryLoading(false)
    }
  }

  const closePaymentHistoryPopup = () => {
    setShowPaymentHistory(false)
    setHistoryParty(null)
    setHistoryPayments([])
    setHistoryLoading(false)
    setHistoryError(null)
    setEditingPayment(null)
    setEditSelectedInvoices({})
    setEditError(null)
  }

  const getEditingAllocationMap = (payment) => {
    const map = {}
    if (!payment) return map

    const allocations = Array.isArray(payment?.allocations) ? payment.allocations : []
    if (allocations.length > 0) {
      for (const allocation of allocations) {
        const key = allocation?.bill_id || allocation?.invoice_no
        if (!key) continue
        map[key] = Number(allocation?.allocated_amount || 0)
      }
      return map
    }

    const invoiceNos = Array.isArray(payment?.matched_invoice_nos) ? payment.matched_invoice_nos : []
    const fallbackAmount = Number(payment?.applied_amount || payment?.amount || 0)
    if (invoiceNos.length > 0 && fallbackAmount > 0) {
      const splitAmount = fallbackAmount / invoiceNos.length
      for (const inv of invoiceNos) {
        if (!inv) continue
        map[inv] = splitAmount
      }
    }

    return map
  }

  const openEditPaymentPopup = (payment) => {
    const invoiceNos = Array.isArray(payment?.matched_invoice_nos) ? payment.matched_invoice_nos : []
    const selected = {}
    for (const bill of historyParty?.bills || []) {
      if (invoiceNos.includes(bill?.invoice_no)) {
        selected[bill._id] = true
      }
    }

    setEditingPayment(payment)
    setEditSelectedInvoices(selected)
    setEditPaymentMode((payment?.payment_mode || 'CASH').toUpperCase())
    setEditAmount(String(payment?.amount ?? ''))
    setEditActualReceivedAmount(String(payment?.actual_received_amount ?? payment?.amount ?? ''))
    setEditReference(payment?.reference || '')
    setEditNotes(payment?.notes || '')
    setEditChequeDate((payment?.cheque_date || '').slice(0, 10) || getTodayISO())
    setEditPartyBankName(payment?.party_bank_name || '')
    setEditChequeAmount(String(payment?.cheque_amount ?? payment?.actual_received_amount ?? payment?.amount ?? ''))
    setEditDepositDate((payment?.deposit_date || '').slice(0, 10) || getTodayISO())
    setEditUpiId(payment?.upi_id || '')
    setEditUpiTransferDate((payment?.upi_transfer_date || '').slice(0, 10) || getTodayISO())
    setEditError(null)
  }

  const closeEditPaymentPopup = () => {
    setEditingPayment(null)
    setEditSelectedInvoices({})
    setEditError(null)
  }

  const toggleEditInvoice = (billId) => {
    setEditSelectedInvoices((prev) => ({ ...prev, [billId]: !prev[billId] }))
  }

  const editDisplayBills = useMemo(() => {
    const partyBills = historyParty?.bills || []
    if (!editingPayment) return []

    const matchedInvoiceNos = new Set(
      (Array.isArray(editingPayment?.matched_invoice_nos) ? editingPayment.matched_invoice_nos : []).filter(Boolean)
    )

    if (matchedInvoiceNos.size === 0) {
      return []
    }

    return partyBills.filter((bill) => matchedInvoiceNos.has(bill?.invoice_no))
  }, [historyParty, editingPayment])

  const editSelectedBills = useMemo(() => {
    return editDisplayBills.filter((bill) => !!editSelectedInvoices[bill._id])
  }, [editSelectedInvoices, editDisplayBills])

  const editAllocationMap = useMemo(() => getEditingAllocationMap(editingPayment), [editingPayment])

  const editSelectedDueAmount = useMemo(() => {
    return editSelectedBills.reduce((sum, bill) => {
      const keyById = bill?._id
      const keyByInvoice = bill?.invoice_no
      const previousAllocated = Number(editAllocationMap[keyById] || editAllocationMap[keyByInvoice] || 0)
      const dueNow = Number(bill?.remaining_amount ?? bill?.grand_total ?? 0)
      return sum + dueNow + previousAllocated
    }, 0)
  }, [editSelectedBills, editAllocationMap])

  const handleUpdatePayment = async () => {
    if (!editingPayment || !historyParty) return

    if (editSelectedBills.length === 0) {
      setEditError('Select at least one invoice for this payment.')
      return
    }

    const amountValue = Number(editAmount)
    if (!amountValue || amountValue <= 0) {
      setEditError('Enter a valid payment amount.')
      return
    }

    const actualAmountValue = Number(editActualReceivedAmount)
    if (!actualAmountValue || actualAmountValue <= 0) {
      setEditError('Enter actual received amount.')
      return
    }

    if (editPaymentMode === 'CHEQUE') {
      if (!editPartyBankName.trim()) {
        setEditError('Enter party bank name for cheque payment.')
        return
      }
      if (!editChequeDate || !editDepositDate) {
        setEditError('Select cheque and deposit dates.')
        return
      }
      const chequeAmountValue = Number(editChequeAmount)
      if (!chequeAmountValue || chequeAmountValue <= 0) {
        setEditError('Enter cheque amount.')
        return
      }
    }

    if (editPaymentMode === 'UPI') {
      if (!editUpiTransferDate) {
        setEditError('Select UPI transfer date.')
        return
      }
      if (editUpiTransferDate > getTodayISO()) {
        setEditError('UPI transfer date cannot be in the future.')
        return
      }
    }

    try {
      const shouldUpdate = window.confirm(
        'Caution: Updating this payment will recalculate bill totals, statuses, and payment history. Continue?'
      )
      if (!shouldUpdate) {
        return
      }

      setSaving(true)
      setEditError(null)

      await paymentsAPI.updateManual(editingPayment.payment_id, {
        amount: amountValue,
        actual_received_amount: actualAmountValue,
        payment_mode: editPaymentMode,
        reference: editReference || null,
        notes: editNotes || null,
        invoice_nos: editSelectedBills.map((b) => b.invoice_no),
        bill_ids: editSelectedBills.map((b) => b._id),
        cheque_date: editPaymentMode === 'CHEQUE' ? editChequeDate : null,
        party_bank_name: editPaymentMode === 'CHEQUE' ? editPartyBankName : null,
        cheque_amount: editPaymentMode === 'CHEQUE' ? Number(editChequeAmount || 0) : null,
        deposit_date: editPaymentMode === 'CHEQUE' ? editDepositDate : null,
        upi_id: editPaymentMode === 'UPI' ? editUpiId.trim() : null,
        upi_transfer_date: editPaymentMode === 'UPI' ? editUpiTransferDate : null,
      })

      closeEditPaymentPopup()

      syncAfterPaymentMutation(historyParty.partyName).catch((err) => {
        console.error('Background refresh failed after update payment:', err)
      })
    } catch (e) {
      const detail = e?.response?.data?.detail
      setEditError(typeof detail === 'string' ? detail : 'Failed to update payment.')
    } finally {
      setSaving(false)
    }
  }

  const handleDeletePayment = async () => {
    if (!editingPayment || !editingPayment.payment_id || !historyParty) return

    const shouldDelete = window.confirm(
      'Caution: This will permanently delete this payment and revert its bill allocations. This action cannot be undone. Continue?'
    )
    if (!shouldDelete) {
      return
    }

    try {
      setSaving(true)
      setEditError(null)

      await paymentsAPI.delete(editingPayment.payment_id)

      await syncAfterPaymentMutation(historyParty.partyName)

      closeEditPaymentPopup()
    } catch (e) {
      const detail = e?.response?.data?.detail
      setEditError(typeof detail === 'string' ? detail : 'Failed to delete payment.')
    } finally {
      setSaving(false)
    }
  }

  const selectedBills = useMemo(() => {
    if (!selectedParty) {
      return []
    }
    return selectedParty.bills.filter((bill) => selectedInvoices[bill._id])
  }, [selectedParty, selectedInvoices])

  const selectedDueAmount = useMemo(
    () => selectedBills.reduce((sum, b) => sum + Number(b?.remaining_amount ?? b?.grand_total ?? 0), 0),
    [selectedBills]
  )

  const selectedInvoiceNumbers = useMemo(
    () => selectedBills.map((bill) => bill?.invoice_no).filter(Boolean),
    [selectedBills]
  )

  const totalReceivedPaymentInvoiceCount = useMemo(() => {
    const uniqueInvoiceNos = new Set()
    for (const payment of partyPayments) {
      const invoiceNos = Array.isArray(payment?.matched_invoice_nos) ? payment.matched_invoice_nos : []
      for (const invoiceNo of invoiceNos) {
        if (invoiceNo) {
          uniqueInvoiceNos.add(invoiceNo)
        }
      }
    }
    return uniqueInvoiceNos.size
  }, [partyPayments])

  const invoiceModeMap = useMemo(() => {
    const modeMap = {}
    const sortedPayments = [...partyPayments].sort((a, b) => {
      const aTime = new Date(a?.payment_date || a?.created_at || 0).getTime()
      const bTime = new Date(b?.payment_date || b?.created_at || 0).getTime()
      return bTime - aTime
    })

    for (const payment of sortedPayments) {
      const mode = payment?.payment_mode || '-'
      const invoices = Array.isArray(payment?.matched_invoice_nos) ? payment.matched_invoice_nos : []
      for (const invNo of invoices) {
        if (!modeMap[invNo]) {
          modeMap[invNo] = mode
        }
      }
    }

    return modeMap
  }, [partyPayments])

  const latestKnownUpiId = useMemo(() => {
    const sortedPayments = [...historyPayments].sort((a, b) => {
      const aTime = new Date(a?.payment_date || a?.created_at || 0).getTime()
      const bTime = new Date(b?.payment_date || b?.created_at || 0).getTime()
      return bTime - aTime
    })

    for (const payment of sortedPayments) {
      if ((payment?.payment_mode || '').toUpperCase() !== 'UPI') continue
      const candidate = (payment?.upi_id || payment?.upiId || payment?.reference || '').trim()
      if (candidate) {
        return candidate
      }
    }

    return ''
  }, [historyPayments])

  const formatDisplayDate = (value) => {
    if (!value) return '-'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    const dd = String(date.getDate()).padStart(2, '0')
    const mm = String(date.getMonth() + 1).padStart(2, '0')
    const yyyy = date.getFullYear()
    return `${dd}/${mm}/${yyyy}`
  }

  const toggleInvoice = (billId) => {
    setSelectedInvoices((prev) => ({
      ...prev,
      [billId]: !prev[billId],
    }))
  }

  const isLockedInvoice = (bill) => Number(bill?.paid_amount || 0) > 0 || bill?.status === 'PAID' || bill?.status === 'PARTIAL'

  const handleSavePayment = async () => {
    if (!selectedParty) return

    if (selectedBills.length === 0) {
      setError('Select at least one invoice.')
      return
    }

    const autoTotalReceiveAmount = Number(selectedDueAmount)
    if (!autoTotalReceiveAmount || autoTotalReceiveAmount <= 0) {
      setError('Selected invoices must have a due amount greater than zero.')
      return
    }

    const actualAmount = Number(actualReceivedAmount)
    if (!actualAmount || actualAmount <= 0) {
      setError('Enter actual received amount.')
      return
    }

    if (paymentMode === 'CHEQUE') {
      if (!partyBankName.trim()) {
        setError('Enter party bank name for cheque payment.')
        return
      }
      if (!chequeDate) {
        setError('Select cheque date.')
        return
      }
      if (!depositDate) {
        setError('Select deposit date.')
        return
      }

      const chequeAmountValue = Number(chequeAmount)
      if (!chequeAmountValue || chequeAmountValue <= 0) {
        setError('Enter cheque amount.')
        return
      }
    }

    if (paymentMode === 'UPI') {
      if (!upiTransferDate) {
        setError('Select UPI transfer date.')
        return
      }

      const todayISO = getTodayISO()
      if (upiTransferDate > todayISO) {
        setError('UPI transfer date cannot be in the future.')
        return
      }
    }

    try {
      setSaving(true)
      setError(null)

      await paymentsAPI.createManual({
        party_name: selectedParty.partyName,
        amount: autoTotalReceiveAmount,
        actual_received_amount: actualAmount,
        payment_mode: paymentMode,
        reference: reference || null,
        notes: notes || null,
        invoice_nos: selectedBills.map((b) => b.invoice_no),
        bill_ids: selectedBills.map((b) => b._id),
        cheque_date: paymentMode === 'CHEQUE' ? chequeDate : null,
        party_bank_name: paymentMode === 'CHEQUE' ? partyBankName : null,
        cheque_amount: paymentMode === 'CHEQUE' ? Number(chequeAmount || 0) : null,
        deposit_date: paymentMode === 'CHEQUE' ? depositDate : null,
        upi_id: paymentMode === 'UPI' ? upiId.trim() : null,
        upi_transfer_date: paymentMode === 'UPI' ? upiTransferDate : null,
      })

      closeReceivePopup()

      syncAfterPaymentMutation(selectedParty.partyName).catch((err) => {
        console.error('Background refresh failed after save payment:', err)
      })
    } catch (e) {
      const detail = e?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to save payment.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow-md p-4">
        <input
          type="text"
          placeholder="Search party by name..."
          value={partySearch}
          onChange={(e) => setPartySearch(e.target.value)}
          className="w-full md:w-96 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
        />
      </div>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">Party</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">Invoices</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">Received</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">Due Amount</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredParties.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-6 text-center text-sm text-gray-500">No parties found.</td>
              </tr>
            ) : (
              filteredParties.map((party) => (
                <tr key={party.partyName} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{party.partyName}</td>
                  <td className="px-6 py-4 text-sm text-center text-gray-700">{party.totalInvoices}</td>
                  <td className="px-6 py-4 text-sm text-right text-green-600 font-medium">
                    ₹{party.receivedAmount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </td>
                  <td className="px-6 py-4 text-sm text-right text-red-600 font-medium">
                    ₹{party.dueAmount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </td>
                  <td className="px-6 py-4 text-sm text-center">
                    <div className="flex items-center justify-center gap-2 flex-wrap">
                      <button
                        onClick={() => openReceivePopup(party)}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium"
                      >
                        Receive Payment
                      </button>
                      <button
                        onClick={() => openPaymentHistoryPopup(party)}
                        className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-800 border border-gray-300 rounded-md text-sm font-medium"
                      >
                        Show Payment History
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showPaymentHistory && historyParty && (
        <div className="fixed inset-0 z-[65] bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl overflow-hidden">
            <div className="flex justify-between items-center px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Payment History - {historyParty.partyName}</h3>
              <button onClick={closePaymentHistoryPopup} className="text-sm text-gray-500 hover:text-gray-700">Close</button>
            </div>

            <div className="p-4 max-h-[75vh] overflow-auto">
              {historyLoading ? (
                <p className="text-sm text-gray-500">Loading payment history...</p>
              ) : historyError ? (
                <p className="text-sm text-red-600">{historyError}</p>
              ) : historyPayments.length === 0 ? (
                <p className="text-sm text-gray-500">No payments found for this party.</p>
              ) : (
                <div className="overflow-x-auto border border-gray-200 rounded-md">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-3 py-2 text-left">Payment ID</th>
                        <th className="px-3 py-2 text-left">Payment Date</th>
                        <th className="px-3 py-2 text-left">Mode</th>
                        <th className="px-3 py-2 text-left">Invoice Nos</th>
                        <th className="px-3 py-2 text-left">UPI ID</th>
                        <th className="px-3 py-2 text-left">UPI Transfer Date</th>
                        <th className="px-3 py-2 text-left">Cheque Date</th>
                        <th className="px-3 py-2 text-left">Deposit Date</th>
                        <th className="px-3 py-2 text-left">Bank</th>
                        <th className="px-3 py-2 text-right">Cheque Amount</th>
                        <th className="px-3 py-2 text-right">Allocated Amount</th>
                        <th className="px-3 py-2 text-right">Actual Received</th>
                        <th className="px-3 py-2 text-left">Reference</th>
                        <th className="px-3 py-2 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historyPayments.map((p) => {
                        const mode = (p?.payment_mode || '').toUpperCase()
                        const isCheque = mode === 'CHEQUE'
                        const isUpi = mode === 'UPI'
                        const invoiceNos = Array.isArray(p?.matched_invoice_nos) ? p.matched_invoice_nos : []
                        const upiIdValue = p?.upi_id || p?.upiId || p?.reference || p?.transaction_id || p?.transactionId || p?.utr || p?.utr_no || latestKnownUpiId || '-'
                        const upiTransferDateValue = p?.upi_transfer_date || p?.upiTransferDate || p?.payment_date || p?.created_at
                        const chequeDateValue = p?.cheque_date || p?.chequeDate || p?.payment_date || p?.created_at
                        const depositDateValue = p?.deposit_date || p?.depositDate || p?.payment_date || p?.created_at
                        const bankNameValue = p?.party_bank_name || p?.partyBankName || p?.bank_name || p?.bankName || p?.bank || p?.reference || '-'
                        const chequeAmountValue = p?.cheque_amount ?? p?.chequeAmount ?? p?.actual_received_amount ?? p?.amount ?? null
                        return (
                          <tr key={p.payment_id || p._id} className="border-t border-gray-100 align-top">
                            <td className="px-3 py-2 font-medium">{p.payment_id || '-'}</td>
                            <td className="px-3 py-2">{formatDisplayDate(p.payment_date || p.created_at)}</td>
                            <td className="px-3 py-2">{mode || '-'}</td>
                            <td className="px-3 py-2">{invoiceNos.length > 0 ? invoiceNos.join(', ') : '-'}</td>
                            <td className="px-3 py-2">{isUpi ? upiIdValue : '-'}</td>
                            <td className="px-3 py-2">{isUpi ? formatDisplayDate(upiTransferDateValue) : '-'}</td>
                            <td className="px-3 py-2">{isCheque ? formatDisplayDate(chequeDateValue) : '-'}</td>
                            <td className="px-3 py-2">{isCheque ? formatDisplayDate(depositDateValue) : '-'}</td>
                            <td className="px-3 py-2">{isCheque ? bankNameValue : '-'}</td>
                            <td className="px-3 py-2 text-right">{isCheque && chequeAmountValue != null ? `₹${Number(chequeAmountValue).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '-'}</td>
                            <td className="px-3 py-2 text-right">₹{Number(p.amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                            <td className="px-3 py-2 text-right">₹{Number(p.actual_received_amount || p.amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                            <td className="px-3 py-2">{p.reference || '-'}</td>
                            <td className="px-3 py-2 text-center">
                              <button
                                onClick={() => openEditPaymentPopup(p)}
                                className="px-2.5 py-1 bg-amber-100 hover:bg-amber-200 text-amber-800 border border-amber-300 rounded-md text-xs font-medium"
                              >
                                Edit
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {editingPayment && historyParty && (
        <div className="fixed inset-0 z-[70] bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl overflow-hidden">
            <div className="flex justify-between items-center px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">
                Edit Payment - {editingPayment.payment_id}
              </h3>
              <button onClick={closeEditPaymentPopup} className="text-sm text-gray-500 hover:text-gray-700">Close</button>
            </div>

            <div className="p-6 space-y-4 max-h-[75vh] overflow-auto">
              {editError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm">
                  {editError}
                </div>
              )}

              <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
                <div className="text-sm text-amber-900 font-medium">Editing Selected Payment Row</div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-2 text-sm text-amber-800">
                  <div>
                    <span className="font-medium">Payment ID:</span> {editingPayment?.payment_id || '-'}
                  </div>
                  <div>
                    <span className="font-medium">Date:</span> {formatDisplayDate(editingPayment?.payment_date || editingPayment?.created_at)}
                  </div>
                  <div>
                    <span className="font-medium">Mode:</span> {(editingPayment?.payment_mode || '-').toUpperCase()}
                  </div>
                  <div>
                    <span className="font-medium">Current Amount:</span> ₹{Number(editingPayment?.amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Payment Mode</label>
                  <select
                    value={editPaymentMode}
                    onChange={(e) => setEditPaymentMode(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    {PAYMENT_MODES.map((mode) => (
                      <option key={mode} value={mode}>{mode}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Editable Selected Due</label>
                  <input
                    type="text"
                    value={editSelectedDueAmount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    readOnly
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-700"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Allocated Amount</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={editAmount}
                    onChange={(e) => setEditAmount(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Actual Received Amount</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={editActualReceivedAmount}
                    onChange={(e) => setEditActualReceivedAmount(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>

              {editPaymentMode === 'CHEQUE' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Cheque Date</label>
                    <input
                      type="date"
                      value={editChequeDate}
                      onChange={(e) => setEditChequeDate(e.target.value)}
                      max={getTodayISO()}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Party Bank Name</label>
                    <input
                      type="text"
                      value={editPartyBankName}
                      onChange={(e) => setEditPartyBankName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Cheque Amount</label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={editChequeAmount}
                      onChange={(e) => setEditChequeAmount(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Deposit Date</label>
                    <input
                      type="date"
                      value={editDepositDate}
                      onChange={(e) => setEditDepositDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                </div>
              )}

              {editPaymentMode === 'UPI' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">UPI ID</label>
                    <input
                      type="text"
                      value={editUpiId}
                      onChange={(e) => setEditUpiId(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">UPI Transfer Date</label>
                    <input
                      type="date"
                      value={editUpiTransferDate}
                      onChange={(e) => setEditUpiTransferDate(e.target.value)}
                      max={getTodayISO()}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Reference</label>
                  <input
                    type="text"
                    value={editReference}
                    onChange={(e) => setEditReference(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                  <input
                    type="text"
                    value={editNotes}
                    onChange={(e) => setEditNotes(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>

              <div className="overflow-x-auto border border-gray-200 rounded-md">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-3 py-2 text-left">Select</th>
                      <th className="px-3 py-2 text-left">Invoice No</th>
                      <th className="px-3 py-2 text-left">Status</th>
                      <th className="px-3 py-2 text-right">Due Now</th>
                      <th className="px-3 py-2 text-right">Previous Allocated</th>
                      <th className="px-3 py-2 text-right">Editable Due</th>
                    </tr>
                  </thead>
                  <tbody>
                    {editDisplayBills.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-3 py-4 text-center text-gray-500">
                          No matched invoices found for this payment row.
                        </td>
                      </tr>
                    ) : editDisplayBills.map((bill) => {
                      const dueNow = Number(bill?.remaining_amount ?? bill?.grand_total ?? 0)
                      const prevAllocated = Number(editAllocationMap[bill?._id] || editAllocationMap[bill?.invoice_no] || 0)
                      const editableDue = dueNow + prevAllocated
                      return (
                        <tr key={`edit-${bill._id}`} className={`border-t border-gray-100 ${editSelectedInvoices[bill._id] ? 'bg-amber-50' : ''}`}>
                          <td className="px-3 py-2">
                            <input
                              type="checkbox"
                              checked={!!editSelectedInvoices[bill._id]}
                              onChange={() => toggleEditInvoice(bill._id)}
                            />
                          </td>
                          <td className="px-3 py-2 font-medium">{bill.invoice_no}</td>
                          <td className="px-3 py-2">{bill.status || 'UNPAID'}</td>
                          <td className="px-3 py-2 text-right">₹{dueNow.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                          <td className="px-3 py-2 text-right">₹{prevAllocated.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                          <td className="px-3 py-2 text-right font-medium">₹{editableDue.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={handleDeletePayment}
                disabled={saving}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white rounded-md font-medium mr-auto"
              >
                {saving ? 'Working...' : 'Delete Payment'}
              </button>
              <button
                onClick={closeEditPaymentPopup}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdatePayment}
                disabled={saving}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-60 text-white rounded-md font-medium"
              >
                {saving ? 'Working...' : 'Update Payment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedParty && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-40 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl overflow-hidden">
            <div className="flex justify-between items-center px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Receive Payment - {selectedParty.partyName}</h3>
              <button onClick={closeReceivePopup} className="text-sm text-gray-500 hover:text-gray-700">Close</button>
            </div>

            <div className="p-6 space-y-4 max-h-[75vh] overflow-auto">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm">
                  {error}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Payment Mode</label>
                  <select
                    value={paymentMode}
                    onChange={(e) => setPaymentMode(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    {PAYMENT_MODES.map((mode) => (
                      <option key={mode} value={mode}>{mode}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Total Receive (Auto)</label>
                  <input
                    type="text"
                    value={selectedDueAmount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    readOnly
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-700"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Actual Receive Amount</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={actualReceivedAmount}
                    onChange={(e) => setActualReceivedAmount(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>

              {paymentMode === 'CHEQUE' && (
                <div className="space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Cheque Date</label>
                      <input
                        type="date"
                        value={chequeDate}
                        onChange={(e) => setChequeDate(e.target.value)}
                        max={getTodayISO()}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Party Bank Name</label>
                      <input
                        type="text"
                        value={partyBankName}
                        onChange={(e) => setPartyBankName(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Cheque Amount</label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={chequeAmount}
                        onChange={(e) => setChequeAmount(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Deposit Date</label>
                      <input
                        type="date"
                        value={depositDate}
                        onChange={(e) => setDepositDate(e.target.value)}
                        min={getTodayISO()}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                  </div>
                </div>
              )}

              {paymentMode === 'UPI' && (
                <div className="space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">UPI ID</label>
                      <input
                        type="text"
                        value={upiId}
                        onChange={(e) => setUpiId(e.target.value)}
                        placeholder="example@upi"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">UPI Transfer Date</label>
                      <input
                        type="date"
                        value={upiTransferDate}
                        onChange={(e) => setUpiTransferDate(e.target.value)}
                        max={getTodayISO()}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-1 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Reference</label>
                  <input
                    type="text"
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                    placeholder="Cheque no / bank ref / UPI ref"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>

              <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
                <div className="text-sm text-gray-700">
                  Current selected invoice count: <span className="font-semibold">{selectedBills.length}</span>
                </div>
                <div className="text-sm text-gray-700">
                  Current selected invoice amount: <span className="font-semibold">₹{selectedDueAmount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                </div>
                <div className="text-sm text-gray-700">
                  Total received payment invoice count: <span className="font-semibold">{totalReceivedPaymentInvoiceCount}</span>
                </div>
                <div className="text-sm text-gray-700 mt-2">
                  Current selected invoice numbers:
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selectedInvoiceNumbers.length > 0 ? (
                      selectedInvoiceNumbers.map((invoiceNo) => (
                        <span key={invoiceNo} className="inline-flex items-center px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-xs font-medium">
                          {invoiceNo}
                        </span>
                      ))
                    ) : (
                      <span className="text-gray-500">-</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto border border-gray-200 rounded-md">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-3 py-2 text-left">Select</th>
                      <th className="px-3 py-2 text-left">Invoice No</th>
                      <th className="px-3 py-2 text-left">Receive Mode</th>
                      <th className="px-3 py-2 text-left">Status</th>
                      <th className="px-3 py-2 text-right">Due Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedParty.bills.map((bill) => {
                      const due = Number(bill?.remaining_amount ?? bill?.grand_total ?? 0)
                      const locked = isLockedInvoice(bill)
                      const isSelected = !!selectedInvoices[bill._id]
                      return (
                        <tr
                          key={bill._id}
                          className={`border-t border-gray-100 ${locked ? 'bg-gray-100 text-gray-500' : ''} ${isSelected && !locked ? 'bg-green-50' : ''}`}
                        >
                          <td className="px-3 py-2">
                            <input
                              type="checkbox"
                              checked={!!selectedInvoices[bill._id]}
                              onChange={() => !locked && toggleInvoice(bill._id)}
                              disabled={locked}
                              className={locked ? 'cursor-not-allowed opacity-60' : ''}
                            />
                          </td>
                          <td className="px-3 py-2 font-medium">{bill.invoice_no}</td>
                          <td className="px-3 py-2">{invoiceModeMap[bill.invoice_no] || '-'}</td>
                          <td className="px-3 py-2">{bill.status || 'UNPAID'}</td>
                          <td className="px-3 py-2 text-right">₹{due.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={closeReceivePopup}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSavePayment}
                disabled={saving}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white rounded-md font-medium"
              >
                {saving ? 'Saving...' : 'Save Payment'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
