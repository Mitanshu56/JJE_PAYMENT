import React from 'react'
import { TrendingUp, TrendingDown, DollarSign, FileText } from 'lucide-react'

export default function SummaryCards({ summary }) {
  const safeSummary = summary || {}
  const paidPercentage = Number(safeSummary.paid_percentage || 0)
  const invoiceStats = safeSummary.invoice_stats || {}

  const cards = [
    {
      title: 'Total Billing',
      value: `₹${(safeSummary.total_billing || 0).toLocaleString('en-IN', {
        maximumFractionDigits: 2,
      })}`,
      icon: DollarSign,
      color: 'bg-blue-500',
      change: '+2.5%',
    },
    {
      title: 'Total Received',
      value: `₹${(safeSummary.total_paid || 0).toLocaleString('en-IN', {
        maximumFractionDigits: 2,
      })}`,
      icon: TrendingUp,
      color: 'bg-green-500',
      change: `${paidPercentage.toFixed(1)}%`,
    },
    {
      title: 'Pending Amount',
      value: `₹${(safeSummary.total_pending || 0).toLocaleString('en-IN', {
        maximumFractionDigits: 2,
      })}`,
      icon: TrendingDown,
      color: 'bg-red-500',
      change: `${(100 - paidPercentage).toFixed(1)}%`,
    },
    {
      title: 'Total Invoices',
      value: invoiceStats.total || 0,
      icon: FileText,
      color: 'bg-purple-500',
      subtext: `${invoiceStats.paid || 0} Paid • ${invoiceStats.unpaid || 0} Unpaid`,
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {cards.map((card, idx) => {
        const Icon = card.icon
        return (
          <div key={idx} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-gray-600 text-sm font-medium">{card.title}</p>
                <h3 className="text-2xl font-bold text-gray-900 mt-2">{card.value}</h3>
                {card.subtext && <p className="text-gray-500 text-xs mt-2">{card.subtext}</p>}
                {card.change && (
                  <p className="text-green-600 text-sm font-medium mt-2">{card.change}</p>
                )}
              </div>
              <div className={`${card.color} p-3 rounded-lg text-white`}>
                <Icon size={24} />
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
