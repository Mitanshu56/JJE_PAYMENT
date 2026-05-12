import React, { useMemo, useState } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

export default function PartyTable({ parties, bills }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedParty, setSelectedParty] = useState(null)

  const safeParties = Array.isArray(parties) ? parties : []
  const safeBills = Array.isArray(bills) ? bills : []

  const partyInvoicesMap = useMemo(() => {
    const map = {}

    for (const bill of safeBills) {
      const partyName = bill?.party_name || 'Unknown Party'
      if (!map[partyName]) map[partyName] = []

      map[partyName].push({
        invoice_no: bill?.invoice_no || 'N/A',
        status: bill?.status || 'UNPAID',
        amount: Number(bill?.grand_total || 0),
      })
    }

    return map
  }, [safeBills])

  const filteredParties = useMemo(() => {
    const term = searchTerm.trim().toLowerCase()
    const sorted = [...safeParties].sort((a, b) => (b.total_billed || 0) - (a.total_billed || 0))

    if (!term) return sorted
    return sorted.filter((p) => (p?.party_name || '').toLowerCase().includes(term))
  }, [safeParties, searchTerm])

  const openPartyInvoices = (partyName) => {
    const invoices = partyInvoicesMap[partyName] || []
    setSelectedParty({ partyName, invoices })
  }

  const closePartyInvoices = () => setSelectedParty(null)

  const getHealthStatus = (paid, total) => {
    const percentage = total > 0 ? (paid / total) * 100 : 0

    if (percentage >= 100) return { label: 'Excellent', color: 'bg-green-100 text-green-700', icon: TrendingUp }
    if (percentage >= 75) return { label: 'Good', color: 'bg-blue-100 text-blue-700', icon: TrendingUp }
    if (percentage >= 50) return { label: 'Fair', color: 'bg-yellow-100 text-yellow-700', icon: TrendingDown }
    return { label: 'Poor', color: 'bg-red-100 text-red-700', icon: TrendingDown }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">

      {/* 🔍 Search */}
      <div className="p-4 border-b bg-gray-50">
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search party..."
          className="w-full md:w-80 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>

      {/* 📊 TABLE */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">

          {/* HEADER */}
          <thead className="bg-gray-100 sticky top-0 z-10">
            <tr className="text-gray-600 text-xs uppercase tracking-wider">
              <th className="px-4 py-3 text-left w-12">Sr</th>
              <th className="px-4 py-3 text-left">Party Name</th>
              <th className="px-4 py-3 text-right">Total</th>
              <th className="px-4 py-3 text-right">Paid</th>
              <th className="px-4 py-3 text-right">Pending</th>
              <th className="px-4 py-3 text-center">Collection</th>
              <th className="px-4 py-3 text-center">Status</th>
              <th className="px-4 py-3 text-center">Invoices</th>
            </tr>
          </thead>

          {/* BODY */}
          <tbody>
            {filteredParties.map((party, index) => {
              const totalBilled = party.total_billed || 0
              const totalPaid = party.total_paid || 0
              const pending = party.pending_amount || 0
              const percentage = totalBilled > 0 ? (totalPaid / totalBilled * 100) : 0

              const status = getHealthStatus(totalPaid, totalBilled)
              const StatusIcon = status.icon
              const partyName = party.party_name || 'Unknown Party'
              const invoices = partyInvoicesMap[partyName] || []

              return (
                <tr
                  key={partyName}
                  className={`border-t hover:bg-blue-50 transition ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'}`}
                >
                  {/* SR NO */}
                  <td className="px-4 py-3 text-gray-500 font-medium">
                    {index + 1}
                  </td>

                  {/* PARTY */}
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {partyName}
                  </td>

                  {/* TOTAL */}
                  <td className="px-4 py-3 text-right font-medium">
                    ₹{totalBilled.toLocaleString('en-IN')}
                  </td>

                  {/* PAID */}
                  <td className="px-4 py-3 text-right text-green-600 font-medium">
                    ₹{totalPaid.toLocaleString('en-IN')}
                  </td>

                  {/* PENDING */}
                  <td className="px-4 py-3 text-right text-red-600 font-medium">
                    ₹{pending.toLocaleString('en-IN')}
                  </td>

                  {/* PROGRESS */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 justify-center">
                      <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-600"
                          style={{ width: `${Math.min(percentage, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-semibold text-gray-700">
                        {percentage.toFixed(0)}%
                      </span>
                    </div>
                  </td>

                  {/* STATUS */}
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full ${status.color}`}>
                      <StatusIcon size={12} />
                      {status.label}
                    </span>
                  </td>

                  {/* INVOICES */}
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => openPartyInvoices(partyName)}
                      className="text-blue-600 hover:underline text-sm font-medium"
                    >
                      View ({invoices.length})
                    </button>
                  </td>
                </tr>
              )
            })}

            {filteredParties.length === 0 && (
              <tr>
                <td colSpan={8} className="text-center py-8 text-gray-500">
                  No data found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 📄 MODAL */}
      {selectedParty && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white w-full max-w-3xl rounded-xl shadow-xl overflow-hidden">

            <div className="flex justify-between items-center px-5 py-4 border-b">
              <h3 className="font-semibold text-gray-900">
                {selectedParty.partyName} - Invoices
              </h3>
              <button onClick={closePartyInvoices} className="text-gray-500 hover:text-black">
                Close
              </button>
            </div>

            <div className="p-4 max-h-[70vh] overflow-auto">
              <table className="w-full text-sm border rounded-lg overflow-hidden">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left">Invoice No</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedParty.invoices.map((inv, idx) => (
                    <tr key={idx} className="border-t">
                      <td className="px-4 py-2 font-medium">{inv.invoice_no}</td>
                      <td className="px-4 py-2">{inv.status}</td>
                      <td className="px-4 py-2 text-right">
                        ₹{inv.amount.toLocaleString('en-IN')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

          </div>
        </div>
      )}
    </div>
  )
}