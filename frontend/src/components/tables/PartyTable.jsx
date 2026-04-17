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
      if (!map[partyName]) {
        map[partyName] = []
      }

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

    if (!term) {
      return sorted
    }

    return sorted.filter((party) => (party?.party_name || '').toLowerCase().includes(term))
  }, [safeParties, searchTerm])

  const openPartyInvoices = (partyName) => {
    const invoices = partyInvoicesMap[partyName] || []
    setSelectedParty({ partyName, invoices })
  }

  const closePartyInvoices = () => {
    setSelectedParty(null)
  }

  const getHealthStatus = (paid, total) => {
    const percentage = (paid / total) * 100
    if (percentage >= 100) return { label: 'Excellent', color: 'text-green-600', icon: TrendingUp }
    if (percentage >= 75) return { label: 'Good', color: 'text-blue-600', icon: TrendingUp }
    if (percentage >= 50) return { label: 'Fair', color: 'text-yellow-600', icon: TrendingDown }
    return { label: 'Poor', color: 'text-red-600', icon: TrendingDown }
  }

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search party by name..."
          className="w-full md:w-96 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
              Party Name
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">
              Total Billed
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">
              Total Paid
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">
              Pending
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
              Collection %
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
              Invoices
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {filteredParties.map((party) => {
            const totalBilled = party.total_billed || 0
            const totalPaid = party.total_paid || 0
            const collectionPercentage = totalBilled > 0 ? (totalPaid / totalBilled * 100).toFixed(1) : '0.0'
            const status = getHealthStatus(totalPaid, totalBilled)
            const StatusIcon = status.icon
            const partyName = party.party_name || 'Unknown Party'
            const invoices = partyInvoicesMap[partyName] || []

            return (
              <React.Fragment key={partyName}>
                <tr className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {partyName}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 font-medium">
                    ₹{totalBilled.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600 font-medium">
                    ₹{totalPaid.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600 font-medium">
                    ₹{(party.pending_amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex items-center justify-center">
                      <div className="w-24 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${Math.min(collectionPercentage, 100)}%` }}
                        ></div>
                      </div>
                      <span className="ml-2 text-sm font-medium text-gray-900">{collectionPercentage}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className={`flex items-center justify-center gap-1 ${status.color}`}>
                      <StatusIcon size={16} />
                      <span className="text-sm font-medium">{status.label}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <button
                      onClick={() => openPartyInvoices(partyName)}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                    >
                      View ({invoices.length})
                    </button>
                  </td>
                </tr>
              </React.Fragment>
            )
          })}

          {filteredParties.length === 0 && (
            <tr>
              <td colSpan={7} className="px-6 py-8 text-center text-sm text-gray-500">
                No parties match your search.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {selectedParty && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40 p-4">
          <div className="bg-white w-full max-w-3xl rounded-lg shadow-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">
                {selectedParty.partyName} - Invoices
              </h3>
              <button
                onClick={closePartyInvoices}
                className="text-gray-500 hover:text-gray-800 text-sm font-medium"
              >
                Close
              </button>
            </div>

            <div className="p-4 max-h-[70vh] overflow-auto">
              {selectedParty.invoices.length === 0 ? (
                <p className="text-sm text-gray-500">No invoices found for this party.</p>
              ) : (
                <table className="min-w-full text-sm border border-gray-200 rounded-md">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 uppercase">Invoice No</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-600 uppercase">Payment Status</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-600 uppercase">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedParty.invoices.map((inv, idx) => (
                      <tr key={`${selectedParty.partyName}-${inv.invoice_no}-${idx}`} className="border-t border-gray-100">
                        <td className="px-4 py-2 text-gray-900 font-medium">{inv.invoice_no}</td>
                        <td className="px-4 py-2 text-gray-700">{inv.status}</td>
                        <td className="px-4 py-2 text-right text-gray-900">₹{(inv.amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
