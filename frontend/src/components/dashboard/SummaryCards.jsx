import React from 'react'
import { TrendingUp, TrendingDown, DollarSign, FileText } from 'lucide-react'

export default function SummaryCards({ summary }) {
  const safeSummary = summary || {}
  const paidPercentage = Number(safeSummary.paid_percentage || 0)
  const invoiceStats = safeSummary.invoice_stats || {}

  const receivedByMode = Array.isArray(safeSummary.received_by_mode)
    ? safeSummary.received_by_mode
    : []

  const receivedModeRows = receivedByMode.length
    ? receivedByMode
    : [
        { mode: 'CASH', amount: 0 },
        { mode: 'CHEQUE', amount: 0 },
        { mode: 'UPI', amount: 0 },
        { mode: 'NEFT', amount: 0 },
      ]

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
      showReceivedModesPopup: true,
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
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
      {cards.map((card, idx) => {
        const Icon = card.icon

        return (
          <div
            key={idx}
            className="relative overflow-visible rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_8px_30px_rgba(15,23,42,0.06)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_14px_40px_rgba(15,23,42,0.12)]"
          >
            {/* Top color bar */}
            <div className={`absolute inset-x-0 top-0 h-1 ${card.color}`} />

            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-[12px] font-semibold uppercase tracking-wide text-slate-500">
                  {card.title}
                </p>

                {/* Popup for payment mode */}
                {card.showReceivedModesPopup && (
                  <div className="relative mt-2 group">
                    <button
                      type="button"
                      className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
                    >
                      Mode-wise breakdown
                    </button>

                    <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-full z-50 mt-2 w-80 rounded-xl border border-slate-200 bg-white p-4 opacity-0 shadow-2xl transition-opacity group-hover:pointer-events-auto group-hover:opacity-100">
                      <div className="mb-3 text-xs font-semibold text-slate-700">
                        Received by payment mode
                      </div>

                      <div className="space-y-2">
                        {receivedModeRows.map((row) => (
                          <div
                            key={row.mode}
                            className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-xs hover:bg-slate-100 transition-colors"
                          >
                            <span className="text-slate-600 font-medium">{row.mode}</span>
                            <span className="font-semibold text-slate-900">
                              ₹
                              {Number(row.amount || 0).toLocaleString('en-IN', {
                                maximumFractionDigits: 2,
                              })}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                <h3 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
                  {card.value}
                </h3>

                {card.subtext && (
                  <p className="mt-2 text-xs text-slate-500">
                    {card.subtext}
                  </p>
                )}

                {card.change && (
                  <p className="mt-2 text-sm font-medium text-emerald-600">
                    {card.change}
                  </p>
                )}
              </div>

              {/* Icon */}
              <div
                className={`flex h-12 w-12 items-center justify-center rounded-2xl ${card.color} text-white shadow-lg`}
              >
                <Icon size={22} />
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}