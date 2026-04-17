import React from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

export default function PartyTable({ parties }) {
  const safeParties = Array.isArray(parties) ? parties : []
  const sortedParties = [...safeParties].sort((a, b) => (b.total_billed || 0) - (a.total_billed || 0))

  const getHealthStatus = (paid, total) => {
    const percentage = (paid / total) * 100
    if (percentage >= 100) return { label: 'Excellent', color: 'text-green-600', icon: TrendingUp }
    if (percentage >= 75) return { label: 'Good', color: 'text-blue-600', icon: TrendingUp }
    if (percentage >= 50) return { label: 'Fair', color: 'text-yellow-600', icon: TrendingDown }
    return { label: 'Poor', color: 'text-red-600', icon: TrendingDown }
  }

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
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
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {sortedParties.map((party) => {
            const totalBilled = party.total_billed || 0
            const totalPaid = party.total_paid || 0
            const collectionPercentage = totalBilled > 0 ? (totalPaid / totalBilled * 100).toFixed(1) : '0.0'
            const status = getHealthStatus(totalPaid, totalBilled)
            const StatusIcon = status.icon

            return (
              <tr key={party.party_name} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {party.party_name}
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
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
