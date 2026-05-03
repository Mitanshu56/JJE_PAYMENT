import React, { useState } from 'react'
import {
  AreaChart,
  Area,
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
  RadialBarChart,
  RadialBar,
} from 'recharts'

const COLORS = {
  ink: '#0f0f0f',
  slate: '#64748b',
  muted: '#94a3b8',
  border: '#e2e8f0',
  bg: '#f8fafc',
  card: '#ffffff',
  paid: '#10b981',
  billed: '#3b82f6',
  pending: '#f43f5e',
  paidLight: 'rgba(16, 185, 129, 0.12)',
  billedLight: 'rgba(59, 130, 246, 0.12)',
  pendingLight: 'rgba(244, 63, 94, 0.12)',
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#fff',
      border: `1px solid ${COLORS.border}`,
      borderRadius: 10,
      padding: '10px 14px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
      fontSize: 13,
      color: COLORS.ink,
    }}>
      {label && <div style={{ fontWeight: 600, marginBottom: 6, color: COLORS.slate }}>{label}</div>}
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color }} />
          <span style={{ color: COLORS.slate, textTransform: 'capitalize' }}>{p.dataKey}:</span>
          <span style={{ fontWeight: 600 }}>₹{Number(p.value).toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

const StatPill = ({ label, value, color, bg }) => (
  <div style={{
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '4px 10px', borderRadius: 99,
    background: bg, fontSize: 12, fontWeight: 500,
  }}>
    <div style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
    <span style={{ color: COLORS.slate }}>{label}</span>
    <span style={{ color, fontWeight: 700 }}>₹{Number(value).toLocaleString()}</span>
  </div>
)

const CardHeader = ({ title, subtitle, stats }) => (
  <div style={{ marginBottom: 18 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
      <div>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: COLORS.ink, letterSpacing: '-0.2px' }}>{title}</h3>
        <p style={{ margin: '2px 0 0', fontSize: 12, color: COLORS.muted }}>{subtitle}</p>
      </div>
      {stats && <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>{stats}</div>}
    </div>
  </div>
)

export default function Charts({ monthlySummary = [] }) {
  const [activeTab, setActiveTab] = useState('overview')

  const chartData = monthlySummary.length > 0
    ? monthlySummary.map((item) => ({
        name: item.month,
        billed: item.total_billed || 0,
        paid: item.total_paid || 0,
        pending: item.total_pending || 0,
      }))
    : [
        { name: 'Jan', billed: 120000, paid: 95000, pending: 25000 },
        { name: 'Feb', billed: 145000, paid: 130000, pending: 15000 },
        { name: 'Mar', billed: 98000, paid: 80000, pending: 18000 },
        { name: 'Apr', billed: 175000, paid: 160000, pending: 15000 },
        { name: 'May', billed: 210000, paid: 185000, pending: 25000 },
        { name: 'Jun', billed: 163000, paid: 140000, pending: 23000 },
      ]

  const totalPaid = chartData.reduce((s, i) => s + i.paid, 0)
  const totalPending = chartData.reduce((s, i) => s + i.pending, 0)
  const totalBilled = chartData.reduce((s, i) => s + i.billed, 0)
  const collectionRate = totalBilled > 0 ? ((totalPaid / totalBilled) * 100).toFixed(1) : 0

  const radialData = [
    { name: 'Collected', value: parseFloat(collectionRate), fill: COLORS.paid },
  ]

  const tabs = ['overview', 'collection', 'trend']

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

        .charts-root * { box-sizing: border-box; }

        .charts-root {
          font-family: 'DM Sans', sans-serif;
          background: ${COLORS.bg};
          padding: 24px;
          min-height: 100vh;
        }

        .charts-header {
          margin-bottom: 24px;
        }

        .charts-title {
          font-size: 22px;
          font-weight: 700;
          color: ${COLORS.ink};
          letter-spacing: -0.5px;
          margin: 0 0 4px;
        }

        .charts-subtitle {
          font-size: 13px;
          color: ${COLORS.muted};
          margin: 0;
        }

        .tabs {
          display: flex;
          gap: 2px;
          background: ${COLORS.border};
          border-radius: 10px;
          padding: 3px;
          width: fit-content;
          margin-bottom: 20px;
        }

        .tab {
          padding: 6px 16px;
          border-radius: 8px;
          border: none;
          cursor: pointer;
          font-size: 12px;
          font-weight: 500;
          font-family: 'DM Sans', sans-serif;
          transition: all 0.15s ease;
          background: transparent;
          color: ${COLORS.slate};
          text-transform: capitalize;
        }

        .tab.active {
          background: #fff;
          color: ${COLORS.ink};
          box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        }

        .kpi-row {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 12px;
          margin-bottom: 20px;
        }

        .kpi-card {
          background: #fff;
          border: 1px solid ${COLORS.border};
          border-radius: 14px;
          padding: 16px;
          transition: box-shadow 0.2s ease;
        }

        .kpi-card:hover {
          box-shadow: 0 6px 20px rgba(0,0,0,0.06);
        }

        .kpi-label {
          font-size: 11px;
          font-weight: 500;
          color: ${COLORS.muted};
          text-transform: uppercase;
          letter-spacing: 0.6px;
          margin-bottom: 6px;
        }

        .kpi-value {
          font-size: 20px;
          font-weight: 700;
          color: ${COLORS.ink};
          font-family: 'DM Mono', monospace;
          letter-spacing: -0.5px;
        }

        .kpi-sub {
          font-size: 11px;
          color: ${COLORS.muted};
          margin-top: 2px;
        }

        .kpi-badge {
          display: inline-block;
          margin-top: 4px;
          padding: 2px 7px;
          border-radius: 99px;
          font-size: 11px;
          font-weight: 600;
        }

        .charts-grid {
          display: grid;
          gap: 14px;
        }

        .charts-grid.two-col {
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        }

        .chart-card {
          background: ${COLORS.card};
          border: 1px solid ${COLORS.border};
          border-radius: 16px;
          padding: 20px;
          transition: box-shadow 0.2s ease;
        }

        .chart-card:hover {
          box-shadow: 0 8px 28px rgba(0,0,0,0.06);
        }

        .chart-card.wide {
          grid-column: 1 / -1;
        }

        .divider {
          border: none;
          border-top: 1px solid ${COLORS.border};
          margin: 20px 0;
        }

        .legend-row {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid ${COLORS.border};
        }

        .legend-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 12px;
          color: ${COLORS.slate};
        }

        .legend-dot {
          width: 8px;
          height: 8px;
          border-radius: 2px;
        }
      `}</style>

      <div className="charts-root">
        {/* Header */}
        <div className="charts-header">
          <h2 className="charts-title">Financial Overview</h2>
          <p className="charts-subtitle">Billing & collection analytics</p>
        </div>

        {/* KPI Row */}
        <div className="kpi-row">
          <div className="kpi-card">
            <div className="kpi-label">Total Billed</div>
            <div className="kpi-value">₹{(totalBilled / 1000).toFixed(0)}K</div>
            <div className="kpi-sub">Across {chartData.length} months</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Collected</div>
            <div className="kpi-value" style={{ color: COLORS.paid }}>₹{(totalPaid / 1000).toFixed(0)}K</div>
            <span className="kpi-badge" style={{ background: COLORS.paidLight, color: COLORS.paid }}>{collectionRate}% rate</span>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Pending</div>
            <div className="kpi-value" style={{ color: COLORS.pending }}>₹{(totalPending / 1000).toFixed(0)}K</div>
            <span className="kpi-badge" style={{ background: COLORS.pendingLight, color: COLORS.pending }}>Outstanding</span>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Avg / Month</div>
            <div className="kpi-value">₹{(totalBilled / chartData.length / 1000).toFixed(0)}K</div>
            <div className="kpi-sub">Billing avg</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="tabs">
          {tabs.map(t => (
            <button key={t} className={`tab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>
              {t}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="charts-grid two-col">
            {/* Area Chart */}
            <div className="chart-card wide">
              <CardHeader
                title="Revenue Trend"
                subtitle="Monthly billed vs collected"
                stats={[
                  <StatPill label="Billed" value={totalBilled} color={COLORS.billed} bg={COLORS.billedLight} />,
                  <StatPill label="Paid" value={totalPaid} color={COLORS.paid} bg={COLORS.paidLight} />,
                ]}
              />
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="gradBilled" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.billed} stopOpacity={0.15} />
                      <stop offset="95%" stopColor={COLORS.billed} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gradPaid" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.paid} stopOpacity={0.15} />
                      <stop offset="95%" stopColor={COLORS.paid} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: COLORS.muted }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: COLORS.muted }} axisLine={false} tickLine={false} tickFormatter={v => `₹${v / 1000}K`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="billed" stroke={COLORS.billed} strokeWidth={2} fill="url(#gradBilled)" dot={false} activeDot={{ r: 5 }} />
                  <Area type="monotone" dataKey="paid" stroke={COLORS.paid} strokeWidth={2} fill="url(#gradPaid)" dot={false} activeDot={{ r: 5 }} />
                </AreaChart>
              </ResponsiveContainer>
              <div className="legend-row">
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.billed }} /><span>Billed</span></div>
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.paid }} /><span>Paid</span></div>
              </div>
            </div>

            {/* Bar Chart */}
            <div className="chart-card">
              <CardHeader title="Monthly Breakdown" subtitle="Paid vs pending per month" />
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} barSize={14} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: COLORS.muted }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: COLORS.muted }} axisLine={false} tickLine={false} tickFormatter={v => `${v / 1000}K`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="paid" fill={COLORS.paid} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="pending" fill={COLORS.pending} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <div className="legend-row">
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.paid }} /><span>Paid</span></div>
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.pending }} /><span>Pending</span></div>
              </div>
            </div>

            {/* Radial + Pie */}
            <div className="chart-card">
              <CardHeader title="Collection Rate" subtitle="Overall payment status" />
              <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
                {/* Radial gauge */}
                <div style={{ position: 'relative', width: 140, flexShrink: 0 }}>
                  <ResponsiveContainer width={140} height={140}>
                    <RadialBarChart innerRadius="72%" outerRadius="100%" data={radialData} startAngle={200} endAngle={-20}>
                      <RadialBar background={{ fill: COLORS.border }} dataKey="value" cornerRadius={10} />
                    </RadialBarChart>
                  </ResponsiveContainer>
                  <div style={{
                    position: 'absolute', top: '50%', left: '50%',
                    transform: 'translate(-50%, -50%)',
                    textAlign: 'center',
                  }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: COLORS.ink, fontFamily: 'DM Mono, monospace' }}>{collectionRate}%</div>
                    <div style={{ fontSize: 10, color: COLORS.muted }}>collected</div>
                  </div>
                </div>

                {/* Pie breakdown */}
                <div style={{ flex: 1 }}>
                  <ResponsiveContainer width="100%" height={140}>
                    <PieChart>
                      <Pie
                        data={[
                          { name: 'Paid', value: totalPaid },
                          { name: 'Pending', value: totalPending },
                        ]}
                        cx="50%" cy="50%"
                        innerRadius={38} outerRadius={58}
                        dataKey="value"
                        paddingAngle={3}
                      >
                        <Cell fill={COLORS.paid} />
                        <Cell fill={COLORS.pending} />
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="legend-row">
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.paid }} /><span>Paid — ₹{(totalPaid / 1000).toFixed(0)}K</span></div>
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.pending }} /><span>Pending — ₹{(totalPending / 1000).toFixed(0)}K</span></div>
              </div>
            </div>
          </div>
        )}

        {/* Collection Tab */}
        {activeTab === 'collection' && (
          <div className="charts-grid two-col">
            <div className="chart-card wide">
              <CardHeader title="Billing vs Collection" subtitle="Month-by-month performance comparison" />
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData} barSize={18} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: COLORS.muted }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: COLORS.muted }} axisLine={false} tickLine={false} tickFormatter={v => `₹${v / 1000}K`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="billed" fill={COLORS.billed} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="paid" fill={COLORS.paid} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <div className="legend-row">
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.billed }} /><span>Billed</span></div>
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.paid }} /><span>Collected</span></div>
              </div>
            </div>

            <div className="chart-card">
              <CardHeader title="Pending by Month" subtitle="Uncollected amounts" />
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} barSize={16} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: COLORS.muted }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: COLORS.muted }} axisLine={false} tickLine={false} tickFormatter={v => `${v / 1000}K`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="pending" radius={[4, 4, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={COLORS.pending} fillOpacity={0.6 + (i / chartData.length) * 0.4} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <CardHeader title="Payment Split" subtitle="Overall paid vs pending" />
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Paid', value: totalPaid },
                        { name: 'Pending', value: totalPending },
                      ]}
                      cx="50%" cy="50%"
                      innerRadius={55} outerRadius={80}
                      dataKey="value"
                      paddingAngle={4}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      <Cell fill={COLORS.paid} />
                      <Cell fill={COLORS.pending} />
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* Trend Tab */}
        {activeTab === 'trend' && (
          <div className="charts-grid">
            <div className="chart-card">
              <CardHeader title="Full Revenue Trend" subtitle="All metrics over time" />
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.billed} stopOpacity={0.12} />
                      <stop offset="95%" stopColor={COLORS.billed} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.paid} stopOpacity={0.12} />
                      <stop offset="95%" stopColor={COLORS.paid} stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="g3" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.pending} stopOpacity={0.12} />
                      <stop offset="95%" stopColor={COLORS.pending} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: COLORS.muted }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: COLORS.muted }} axisLine={false} tickLine={false} tickFormatter={v => `₹${v / 1000}K`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="billed" stroke={COLORS.billed} strokeWidth={2} fill="url(#g1)" dot={false} activeDot={{ r: 5 }} />
                  <Area type="monotone" dataKey="paid" stroke={COLORS.paid} strokeWidth={2} fill="url(#g2)" dot={false} activeDot={{ r: 5 }} />
                  <Area type="monotone" dataKey="pending" stroke={COLORS.pending} strokeWidth={2} fill="url(#g3)" dot={false} activeDot={{ r: 5 }} />
                </AreaChart>
              </ResponsiveContainer>
              <div className="legend-row">
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.billed }} /><span>Billed</span></div>
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.paid }} /><span>Paid</span></div>
                <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.pending }} /><span>Pending</span></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  )
}