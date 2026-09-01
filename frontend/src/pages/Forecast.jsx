import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, AlertTriangle, DollarSign, Calendar } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine
} from 'recharts'
import { getForecast } from '../api'
import { StatCard, Spinner, Currency } from '../components/ui'

const RISK_COLOR = {
  LOW: { cls: 'text-green-400', bg: 'bg-green-900/30 border-green-700/40', label: 'Low Risk' },
  MEDIUM: { cls: 'text-amber-400', bg: 'bg-amber-900/30 border-amber-700/40', label: 'Medium Risk' },
  HIGH: { cls: 'text-orange-400', bg: 'bg-orange-900/30 border-orange-700/40', label: 'High Risk' },
  CRITICAL: { cls: 'text-red-400', bg: 'bg-red-900/30 border-red-700/40', label: 'Critical Risk' },
}

export default function Forecast() {
  const [forecast, setForecast] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getForecast()
      .then(d => setForecast(d.forecast))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-4 text-red-400">{error}</div>
      </div>
    )
  }

  const risk = RISK_COLOR[forecast?.risk_level] || RISK_COLOR.LOW
  const daily = forecast?.daily_breakdown || []

  const chartData = daily.map(d => ({
    date: d.forecast_date?.slice(5),  // MM-DD
    inflow: Math.round(d.projected_inflow),
    outflow: Math.round(d.projected_outflow),
    net: Math.round(d.net_position),
    confidence: Math.round(d.confidence * 100),
  }))

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Cash Flow Forecast</h1>
          <p className="text-gray-400 text-sm mt-1">14-day projected cash position</p>
        </div>
        {forecast && (
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium ${risk.bg} ${risk.cls}`}>
            <AlertTriangle className="w-4 h-4" />
            {risk.label}
          </div>
        )}
      </div>

      {/* Stats */}
      {forecast && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Current Cash"
            value={`₹${(parseFloat(forecast.current_cash) / 1000).toFixed(0)}K`}
            icon={DollarSign}
            color="green"
            subtitle="Estimated position"
          />
          <StatCard
            label="7-Day Projection"
            value={`₹${(parseFloat(forecast.forecast_7_days) / 1000).toFixed(0)}K`}
            icon={TrendingUp}
            color="brand"
            subtitle="Net cash in 7 days"
          />
          <StatCard
            label="14-Day Projection"
            value={`₹${(parseFloat(forecast.forecast_14_days) / 1000).toFixed(0)}K`}
            icon={Calendar}
            color="purple"
            subtitle="Net cash in 14 days"
          />
          <StatCard
            label="Pending Settlements"
            value={`₹${(parseFloat(forecast.pending_settlements || 0) / 1000).toFixed(0)}K`}
            icon={TrendingDown}
            color="amber"
            subtitle="Awaiting settlement"
          />
        </div>
      )}

      {/* Area chart */}
      {chartData.length > 0 && (
        <div className="card p-5">
          <h3 className="section-heading mb-1">Net Cash Position</h3>
          <p className="text-xs text-gray-500 mb-4">14-day projected trajectory</p>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="netGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6172f3" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6172f3" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(45,59,107,0.4)" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} />
              <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip
                contentStyle={{ background: '#151d38', border: '1px solid #2d3b6b', borderRadius: 8, fontSize: 12 }}
                formatter={(v, name) => [`₹${v.toLocaleString('en-IN')}`, name]}
              />
              <Area
                type="monotone"
                dataKey="net"
                name="Net Position"
                stroke="#6172f3"
                strokeWidth={2}
                fill="url(#netGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Inflow vs Outflow */}
      {chartData.length > 0 && (
        <div className="card p-5">
          <h3 className="section-heading mb-4">Inflow vs Outflow</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="inGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="outGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(45,59,107,0.4)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip
                contentStyle={{ background: '#151d38', border: '1px solid #2d3b6b', borderRadius: 8, fontSize: 11 }}
                formatter={(v) => [`₹${v.toLocaleString('en-IN')}`]}
              />
              <Area type="monotone" dataKey="inflow" name="Inflow" stroke="#22c55e" strokeWidth={1.5} fill="url(#inGrad)" />
              <Area type="monotone" dataKey="outflow" name="Outflow" stroke="#ef4444" strokeWidth={1.5} fill="url(#outGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Risk factors */}
      {forecast?.risk_factors?.length > 0 && (
        <div className={`rounded-lg border p-4 ${risk.bg}`}>
          <h3 className={`text-sm font-semibold mb-2 ${risk.cls}`}>Risk Factors</h3>
          <ul className="space-y-1.5">
            {forecast.risk_factors.map((f, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-amber-400" />
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
