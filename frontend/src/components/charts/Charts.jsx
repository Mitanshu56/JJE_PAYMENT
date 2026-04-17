import React from 'react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

export default function Charts({ monthlySummary }) {
  const COLORS = ['#16a34a', '#dc2626', '#f59e0b']

  // Prepare data for pie chart
  const chartData = monthlySummary.map((item) => ({
    name: item.month,
    billed: item.total_billed,
    paid: item.total_paid,
    pending: item.total_pending,
  }))

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Revenue Trend */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Monthly Revenue Trend</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
            <Legend />
            <Line type="monotone" dataKey="billed" stroke="#3b82f6" name="Billed" />
            <Line type="monotone" dataKey="paid" stroke="#16a34a" name="Paid" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Paid vs Unpaid */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Monthly Paid vs Pending</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
            <Legend />
            <Bar dataKey="paid" fill="#16a34a" name="Paid" />
            <Bar dataKey="pending" fill="#dc2626" name="Pending" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Overall Status */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Payment Status</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={[
                {
                  name: 'Paid',
                  value: chartData.reduce((sum, item) => sum + item.paid, 0),
                },
                {
                  name: 'Pending',
                  value: chartData.reduce((sum, item) => sum + item.pending, 0),
                },
              ]}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, value }) => `${name}: ₹${(value / 100000).toFixed(1)}L`}
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
            >
              <Cell fill="#16a34a" />
              <Cell fill="#dc2626" />
            </Pie>
            <Tooltip formatter={(value) => `₹${(value / 100000).toFixed(1)}L`} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Amount Trend */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Billed vs Collected</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
            <Legend />
            <Bar dataKey="billed" fill="#3b82f6" name="Billed" />
            <Bar dataKey="paid" fill="#16a34a" name="Collected" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
