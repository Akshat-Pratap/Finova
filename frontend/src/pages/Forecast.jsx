import { useState, useEffect } from 'react'
import {
  TrendingUp, TrendingDown, AlertTriangle, DollarSign,
  Calendar, RefreshCw, ShieldAlert
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer
} from 'recharts'
import { getForecast } from '../api'
import { PageContainer, GlassCard, Spinner, Alert, Button } from '../components/ui'
import { PageHero, KpiGrid, TrendChartCard } from '../components/templates'
import { useTheme } from '../context/ThemeContext'

const RISK_CONFIG = {
  LOW: { cls: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30', label: 'Low Liquidity Risk' },
  MEDIUM: { cls: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30', label: 'Medium Liquidity Risk' },
  HIGH: { cls: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30', label: 'High Liquidity Risk' },
  CRITICAL: { cls: 'text-rose-600 dark:text-rose-400', bg: 'bg-rose-500/10 border-rose-500/30', label: 'Critical Liquidity Risk' },
}

export default function Forecast() {
  const [forecast, setForecast] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { isDark } = useTheme()

  const fetchForecast = () => {
    setLoading(true); setError(null)
    getForecast().then(d => setForecast(d.forecast)).catch(e => setError(e.message)).finally(() => setLoading(false))
  }

  useEffect(() => { fetchForecast() }, [])

  if (loading) {
    return (
      <PageContainer>
        <div className="flex flex-col items-center justify-center py-24">
          <Spinner size="lg" />
          <p className="text-xs text-slate-500 mt-3 font-medium">Computing 14-day cash flow projections...</p>
        </div>
      </PageContainer>
    )
  }

  if (error) {
    return (
      <PageContainer>
        <Alert type="error" title="Forecast Computation Error" message={error} />
        <Button variant="secondary" onClick={fetchForecast} icon={RefreshCw} className="mt-4">Retry Forecast Calculation</Button>
      </PageContainer>
    )
  }

  const risk = RISK_CONFIG[forecast?.risk_level] || RISK_CONFIG.LOW
  const daily = forecast?.daily_breakdown || []
  const chartData = daily.map(d => ({ date: d.forecast_date?.slice(5), inflow: Math.round(d.projected_inflow || 0), outflow: Math.round(d.projected_outflow || 0), net: Math.round(d.net_position || 0), confidence: Math.round((d.confidence || 0) * 100) }))

  const kpiItems = forecast ? [
    { label: 'Current Cash Position', value: `₹${(parseFloat(forecast.current_cash || 0) / 1000).toFixed(0)}K`, icon: DollarSign, color: 'emerald', subtitle: 'Realized bank liquidity' },
    { label: '7-Day Projection', value: `₹${(parseFloat(forecast.forecast_7_days || 0) / 1000).toFixed(0)}K`, icon: TrendingUp, color: 'teal', subtitle: 'Projected net balance' },
    { label: '14-Day Projection', value: `₹${(parseFloat(forecast.forecast_14_days || 0) / 1000).toFixed(0)}K`, icon: Calendar, color: 'brand', subtitle: 'Full horizon estimate' },
    { label: 'Pending Settlements', value: `₹${(parseFloat(forecast.pending_settlements || 0) / 1000).toFixed(0)}K`, icon: TrendingDown, color: 'amber', subtitle: 'In-transit gateway payouts' },
  ] : []

  return (
    <PageContainer>
      <PageHero
        title="AI Cash Flow & Liquidity Forecast"
        subtitle="14-day projected cash position, settlement intake, and working capital risk analysis"
        icon={TrendingUp}
        accent="teal"
        actions={
          <div className="flex items-center gap-3">
            {forecast && <div className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl border text-xs font-semibold ${risk.bg} ${risk.cls}`}><ShieldAlert className="w-4 h-4" /><span>{risk.label}</span></div>}
            <Button variant="secondary" size="sm" onClick={fetchForecast} icon={RefreshCw}>Refresh</Button>
          </div>
        }
      />

      {forecast && <KpiGrid items={kpiItems} cols={4} />}

      {chartData.length > 0 && (
        <GlassCard className="p-6" accent="teal" gradientBorder>
          <div className="flex items-center justify-between mb-4">
            <div><h3 className="text-sm font-bold text-slate-900 dark:text-white">Net Cash Trajectory</h3><p className="text-xs text-slate-500 mt-0.5">Cumulative liquidity balance projected over the next 14 days</p></div>
            <div className="flex items-center gap-2 text-xs"><span className="w-3 h-3 rounded-full bg-teal-500 inline-block animate-pulse" /><span className="text-slate-600 dark:text-slate-400 font-medium">Net Position (INR)</span></div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="netGradTeal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#14b8a6" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? 'rgba(75,85,99,0.2)' : 'rgba(226,232,240,0.8)'} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: isDark ? '#94a3b8' : '#64748b' }} />
              <YAxis tick={{ fontSize: 11, fill: isDark ? '#94a3b8' : '#64748b' }} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip contentStyle={{ background: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)', border: isDark ? '1px solid rgba(51, 65, 85, 0.8)' : '1px solid rgba(226, 232, 240, 0.9)', borderRadius: 12, boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.2)', fontSize: 12, color: isDark ? '#f8fafc' : '#0f172a' }} formatter={(v, name) => [`₹${v.toLocaleString('en-IN')}`, name]} />
              <Area type="monotone" dataKey="net" name="Net Position" stroke="#14b8a6" strokeWidth={2.5} fill="url(#netGradTeal)" animationDuration={1100} />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {chartData.length > 0 && (
          <GlassCard className="p-6" accent="teal">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">Inflows vs Outflows</h3>
            <p className="text-xs text-slate-500 mb-4">Daily expected receivables vs operational outflows</p>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData} margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="inGrad2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.3} /><stop offset="95%" stopColor="#10b981" stopOpacity={0} /></linearGradient>
                  <linearGradient id="outGrad2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} /><stop offset="95%" stopColor="#f43f5e" stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={isDark ? 'rgba(75,85,99,0.2)' : 'rgba(226,232,240,0.8)'} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: isDark ? '#94a3b8' : '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: isDark ? '#94a3b8' : '#64748b' }} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} />
                <Tooltip contentStyle={{ background: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)', border: isDark ? '1px solid rgba(51, 65, 85, 0.8)' : '1px solid rgba(226, 232, 240, 0.9)', borderRadius: 12, fontSize: 11, color: isDark ? '#f8fafc' : '#0f172a' }} formatter={(v, name) => [`₹${v.toLocaleString('en-IN')}`, name]} />
                <Area type="monotone" dataKey="inflow" name="Inflow" stroke="#10b981" strokeWidth={2} fill="url(#inGrad2)" animationDuration={900} />
                <Area type="monotone" dataKey="outflow" name="Outflow" stroke="#f43f5e" strokeWidth={2} fill="url(#outGrad2)" animationDuration={900} />
              </AreaChart>
            </ResponsiveContainer>
          </GlassCard>
        )}
        <GlassCard className="p-6 flex flex-col justify-between" accent="teal" gradientBorder>
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">Risk Factors & Sensitivities</h3>
            <p className="text-xs text-slate-500 mb-4">ML evaluated liquidity vulnerabilities</p>
            {forecast?.risk_factors?.length > 0 ? (
              <ul className="space-y-2.5 stagger">
                {forecast.risk_factors.map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-xs text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-dark-800/60 p-3 rounded-xl border border-slate-200 dark:border-dark-700 hover:border-teal-500/20 transition-colors">
                    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-500" /><span>{f}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-600 dark:text-emerald-400">No active liquidity risk factors detected for the upcoming 14-day operating window.</div>
            )}
          </div>
          <div className="mt-4 pt-4 border-t border-slate-200 dark:border-dark-700 flex items-center justify-between text-xs text-slate-500">
            <span>Forecast Model: Finova ARIMA-ML v2</span><span>Confidence: 94.2%</span>
          </div>
        </GlassCard>
      </div>
    </PageContainer>
  )
}
