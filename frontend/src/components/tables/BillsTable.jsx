import React, { useState, useEffect } from 'react'
import { billsAPI } from '../../services/api'
import { Trash2, Eye } from 'lucide-react'

const MONTH_OPTIONS = [
  { label: 'January', value: '1' },
  { label: 'February', value: '2' },
  { label: 'March', value: '3' },
  { label: 'April', value: '4' },
  { label: 'May', value: '5' },
  { label: 'June', value: '6' },
  { label: 'July', value: '7' },
  { label: 'August', value: '8' },
  { label: 'September', value: '9' },
  { label: 'October', value: '10' },
  { label: 'November', value: '11' },
  { label: 'December', value: '12' },
]

export default function BillsTable() {
  const [bills, setBills] = useState([])
  const [totalBills, setTotalBills] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [loading, setLoading] = useState(false)
  const [selectedBill, setSelectedBill] = useState(null)
  const [filters, setFilters] = useState({
    status: '',
    party: '',
    month: '',
  })

  const totalPages = Math.max(1, Math.ceil(totalBills / pageSize))

  useEffect(() => {
    loadBills()
  }, [filters, page, pageSize])

  useEffect(() => {
    setPage(1)
  }, [filters.status, filters.party, filters.month, pageSize])

  const loadBills = async () => {
    try {
      setLoading(true)
      const skip = (page - 1) * pageSize
      const res = await billsAPI.getAll(
        skip,
        pageSize,
        filters.status || null,
        filters.party || null,
        filters.month || null,
      )
      setBills(res.data.bills)
      setTotalBills(res.data.total || 0)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (invoiceNo) => {
    if (window.confirm('Are you sure you want to delete this bill?')) {
      try {
        await billsAPI.delete(invoiceNo)
        await loadBills()
      } catch (err) {
        console.error(err)
      }
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'PAID':
        return 'bg-green-100 text-green-800'
      case 'PARTIAL':
        return 'bg-yellow-100 text-yellow-800'
      case 'UNPAID':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatDisplayDate = (value) => {
    if (!value) return '-'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    const dd = String(date.getDate()).padStart(2, '0')
    const mm = String(date.getMonth() + 1).padStart(2, '0')
    const yyyy = date.getFullYear()
    return `${dd}/${mm}/${yyyy}`
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow-md p-4 flex gap-4">
        <input
          type="text"
          placeholder="Filter by party..."
          value={filters.party}
          onChange={(e) => setFilters({ ...filters, party: e.target.value })}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
        />
        <select
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
        >
          <option value="">All Status</option>
          <option value="PAID">Paid</option>
          <option value="PARTIAL">Partial</option>
          <option value="UNPAID">Unpaid</option>
        </select>
        <select
          value={filters.month}
          onChange={(e) => setFilters({ ...filters, month: e.target.value })}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
        >
          <option value="">All Months</option>
          {MONTH_OPTIONS.map((month) => (
            <option key={month.value} value={month.value}>{month.label}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="overflow-x-auto">
        <table className="w-full min-w-[1400px]">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                Invoice No
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                Party
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                Party GST No
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">
                Net
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">
                CGST
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">
                SGST
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">
                Amount
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">
                Paid
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-600 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan="11" className="px-6 py-4 text-center text-gray-500">
                  Loading...
                </td>
              </tr>
            ) : bills.length === 0 ? (
              <tr>
                <td colSpan="11" className="px-6 py-4 text-center text-gray-500">
                  No bills found
                </td>
              </tr>
            ) : (
              bills.map((bill) => (
                <tr key={bill._id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {bill.invoice_no}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {bill.party_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {bill.gst_no || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {formatDisplayDate(bill.invoice_date)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                    ₹{(bill.net_amount || 0).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                    ₹{(bill.cgst || 0).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                    ₹{(bill.sgst || 0).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 font-medium">
                    ₹{(bill.grand_total || 0).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600 font-medium">
                    ₹{(bill.paid_amount || 0).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(bill.status)}`}>
                      {bill.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex justify-center gap-2">
                      <button
                        onClick={() => setSelectedBill(bill)}
                        className="text-blue-600 hover:text-blue-800"
                        title="View Details"
                      >
                        <Eye size={18} />
                      </button>
                      <button
                        onClick={() => handleDelete(bill.invoice_no)}
                        className="text-red-600 hover:text-red-800"
                        title="Delete"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        </div>

        <div className="border-t border-gray-200 px-4 py-3 flex items-center justify-between gap-4">
          <div className="text-sm text-gray-600">
            Showing {bills.length === 0 ? 0 : (page - 1) * pageSize + 1}-{Math.min(page * pageSize, totalBills)} of {totalBills} invoices
          </div>
          <div className="flex items-center gap-3">
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="px-2 py-1 border border-gray-300 rounded text-sm"
            >
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
              <option value={100}>100 / page</option>
            </select>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
              className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
            >
              Prev
            </button>
            <span className="text-sm text-gray-700">Page {page} / {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Modal for bill details */}
      {selectedBill && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full">
            <div className="p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Bill Details</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-gray-600">Invoice No</p>
                  <p className="font-medium">{selectedBill.invoice_no}</p>
                </div>
                <div>
                  <p className="text-gray-600">Party Name</p>
                  <p className="font-medium">{selectedBill.party_name}</p>
                </div>
                <div>
                  <p className="text-gray-600">GST No</p>
                  <p className="font-medium">{selectedBill.gst_no || 'N/A'}</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-gray-600">Net Amount</p>
                    <p className="font-medium">₹{(selectedBill.net_amount || 0).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">CGST</p>
                    <p className="font-medium">₹{(selectedBill.cgst || 0).toLocaleString()}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-gray-600">SGST</p>
                    <p className="font-medium">₹{(selectedBill.sgst || 0).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Grand Total</p>
                    <p className="font-medium text-blue-600">₹{(selectedBill.grand_total || 0).toLocaleString()}</p>
                  </div>
                </div>
                <div>
                  <p className="text-gray-600">Paid Amount</p>
                  <p className="font-medium text-green-600">₹{(selectedBill.paid_amount || 0).toLocaleString()}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedBill(null)}
                className="mt-6 w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
