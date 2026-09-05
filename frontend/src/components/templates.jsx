/**
 * Finova — Reusable Dashboard / UI Layout Templates
 * Vibrant Liquid templates built on ui.jsx primitives.
 * Accent: brand | cyan | fuchsia | teal | emerald | amber
 */
import React from 'react'
import { Link } from 'react-router-dom'
import {
  Activity, Clock, Zap, TrendingUp, BarChart3, ArrowUpRight,
  ShieldCheck, AlertTriangle, FileText, Brain
} from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts'
import { GlassCard, StatCard, ConfidenceBar, Button, EmptyState, StatusBadge } from './ui'

const ACCENT_MAP = {
  brand: { chip: 'from-brand-600/30 to-indigo-500/20 border-brand-500/30 text-brand-400', glow: 'shadow-glow-sm', border: 'border-aurora-brand', dot: 'bg-brand-500' },
  cyan: { chip: 'from-cyan-600/30 to-teal-500/20 border-cyan-500/30 text-cyan-400', glow: 'shadow-glow-cyan-sm', border: 'border-aurora-cyan', dot: 'bg-cyan-400' },
  fuchsia: { chip: 'from-fuchsia-600/30 to-purple-500/20 border-fuchsia-500/30 text-fuchsia-400', glow: 'shadow-glow-fuchsia-sm', border: 'border-aurora-fuchsia', dot: 'bg-fuchsia-400' },
  teal: { chip: 'from-teal-600/30 to-emerald-500/20 border-teal-500/30 text-teal-400', glow: 'shadow-glow-teal-sm', border: 'border-aurora-teal', dot: 'bg-teal-400' },
  emerald: { chip: 'from-emerald-600/30 to-teal-500/20 border-emerald-500/30 text-emerald-400', glow: 'shadow-glow-emerald', border: 'border-aurora-emerald', dot: 'bg-emerald-400' },
  amber: { chip: 'from-amber-600/30 to-orange-500/20 border-amber-500/30 text-amber-400', glow: 'shadow-glow-amber', border: 'border-aurora-amber', dot: 'bg-amber-400' },
}

function accentOf(a) { return ACCENT_MAP[a] || ACCENT_MAP.brand }

// ——————————————————————————————
// PageHero — richer animated header
export function PageHero({ title, subtitle, badge, icon: Icon, actions, accent = 'brand' }) {
  const a = accentOf(accent)
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/40">
      <div className="flex items-start gap-3">
        {Icon && (
          <div className={`w-11 h-11 rounded-xl bg-gradient-to-tr border flex items-center justify-center shrink-0 shadow-sm animate-float ${a.chip}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-black tracking-tight text-slate-100">{title}</h1>
            {badge && <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-800/80 text-slate-300 border border-slate-700/60">{badge}</span>}
            <span className={`w-2 h-2 rounded-full ${a.dot} pulse-ring`} />
          </div>
          {subtitle && <p className="text-xs sm:text-sm text-slate-400 mt-0.5 max-w-2xl">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2.5 flex-wrap">{actions}</div>}
    </div>
  )
}

// KpiGrid — responsive KPI strip with stagger
export function KpiGrid({ items = [], cols = 4 }) {
  const colCls = cols === 2 ? 'grid-cols-1 sm:grid-cols-2' : cols === 3 ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'
  return (
    <div className={`grid ${colCls} gap-4 stagger`}>
      {items.map((it, i) => (
        <StatCard key={i} {...it} />
      ))}
    </div>
  )
}

// InsightsPanel — AI insight cards
export function InsightsPanel({ insights = [], accent = 'cyan', title = 'AI Insights' }) {
  const a = accentOf(accent)
  return (
    <GlassCard className={`p-6 space-y-4 ${a.glow}`} accent={accent} gradientBorder>
      <div className="flex items-center justify-between">
        <h3 className="section-heading"><Brain className={`w-4 h-4 ${a.chip.split(' ').pop()}`} />{title}</h3>
        <span className="text-[10px] font-mono text-slate-400 border border-slate-700/50 px-2 py-0.5 rounded-full">{insights.length} signals</span>
      </div>
      <div className="space-y-3 stagger">
        {insights.map((ins, i) => (
          <div key={i} className="p-3 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-colors space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-200 truncate">{ins.headline}</span>
              {ins.impact && <span className={`text-[10px] px-2 py-0.5 rounded-full border font-bold ${a.chip}`}>{ins.impact}</span>}
            </div>
            {ins.confidence !== undefined && <ConfidenceBar value={ins.confidence} />}
            {ins.sparkline && (
              <div className="h-10">
                <ResponsiveContainer width="100%" height="100%"><AreaChart data={ins.sparkline}><Area type="monotone" dataKey="v" stroke={a.dot.replace('bg-','')} strokeWidth={1.5} fillOpacity={0.15} fill={a.dot.replace('bg-','')} /></AreaChart></ResponsiveContainer>
              </div>
            )}
          </div>
        ))}
        {insights.length === 0 && <p className="text-xs text-slate-500 italic py-4 text-center">No insights yet.</p>}
      </div>
    </GlassCard>
  )
}

// HealthMonitor — engine health card
export function HealthMonitor({ latency = '~0.04s/batch', uptime = '99.98%', lastRun = 'just now', status = 'healthy', metrics = [], accent = 'teal' }) {
  const a = accentOf(accent)
  const statusColor = status === 'healthy' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' : status === 'degraded' ? 'text-amber-400 bg-amber-500/10 border-amber-500/30' : 'text-red-400 bg-red-500/10 border-red-500/30'
  return (
    <GlassCard className={`p-6 space-y-4 ${a.glow}`} accent={accent} gradientBorder>
      <div className="flex items-center justify-between">
        <h3 className="section-heading"><Activity className={`w-4 h-4 ${a.chip.split(' ').pop()}`} />Engine Health</h3>
        <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold border flex items-center gap-1.5 ${statusColor}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${a.dot} pulse-ring`} />{status.toUpperCase()}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-800">
          <p className="text-[10px] uppercase tracking-wider text-slate-400">Latency</p><p className="text-sm font-mono font-bold text-slate-100 mt-1">{latency}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-800">
          <p className="text-[10px] uppercase tracking-wider text-slate-400">Uptime</p><p className="text-sm font-mono font-bold text-emerald-400 mt-1">{uptime}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/50 border border-slate-800">
          <p className="text-[10px] uppercase tracking-wider text-slate-400">Last Run</p><p className="text-sm font-mono font-bold text-slate-100 mt-1">{lastRun}</p>
        </div>
      </div>
      {metrics.length > 0 && (
        <div className="space-y-2 stagger">
          {metrics.map((m, i) => (
            <div key={i} className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-slate-900/40 border border-slate-800">
              <span className="text-slate-400">{m.label}</span><span className="font-mono font-bold text-slate-200">{m.value}</span>
            </div>
          ))}
        </div>
      )}
      {/* scan line */}
      <div className="relative h-1 bg-slate-800 rounded-full overflow-hidden">
        <span className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-teal-400/60 to-transparent" style={{ animation: 'scan 2.5s linear infinite' }} />
      </div>
    </GlassCard>
  )
}

// ActivityFeed — vertical timeline
export function ActivityFeed({ items = [], accent = 'brand', title = 'Activity', viewAllHref }) {
  const dotMap = { cyan: 'bg-cyan-400', fuchsia: 'bg-fuchsia-400', teal: 'bg-teal-400', emerald: 'bg-emerald-400', amber: 'bg-amber-400', brand: 'bg-brand-500' }
  const dot = dotMap[accent] || dotMap.brand
  return (
    <GlassCard className="p-6 space-y-4" accent={accent}>
      <div className="flex items-center justify-between">
        <h3 className="section-heading"><Clock className="w-4 h-4 text-slate-400" />{title}</h3>
        {viewAllHref && <Link to={viewAllHref} className="text-xs text-brand-400 hover:text-brand-300 font-semibold flex items-center gap-1">View all <ArrowUpRight className="w-3 h-3" /></Link>}
      </div>
      {items.length === 0 ? <p className="text-xs text-slate-500 italic py-6 text-center">No activity yet.</p> : (
        <div className="relative pl-4 space-y-0">
          <div className="absolute left-1.5 top-2 bottom-2 w-px bg-slate-800" />
          <div className="space-y-3 stagger">
            {items.map((it, i) => (
              <div key={i} className="relative flex gap-3 pl-4">
                <span className={`absolute left-0 top-1.5 w-2.5 h-2.5 rounded-full ${it.color || dot} border-2 border-slate-900 pulse-ring`} style={{ color: it.color || dot }} />
                <div className="flex-1 min-w-0 p-2.5 rounded-xl bg-slate-900/40 border border-slate-800 hover:border-slate-700 transition-colors">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-slate-200 truncate">{it.title}</span>
                    <span className="text-[10px] font-mono text-slate-500 shrink-0">{it.time}</span>
                  </div>
                  {it.subtitle && <p className="text-[11px] text-slate-400 truncate">{it.subtitle}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </GlassCard>
  )
}

// DonutSummaryCard
export function DonutSummaryCard({ title = 'Reconciliation Breakdown', subtitle = 'Distribution by outcome', data = [], centerLabel, footerStats, accent = 'brand' }) {
  const COLORS_FALLBACK = ['#22c55e', '#06b6d4', '#f59e0b', '#e879f9', '#ef4444']
  return (
    <GlassCard className="p-6 flex flex-col justify-between" accent={accent} gradientBorder>
      <div>
        <div className="flex items-center justify-between mb-1">
          <h3 className="section-heading"><BarChart3 className="w-4 h-4 text-brand-400" />{title}</h3>
          {centerLabel && <span className="text-[11px] font-mono text-slate-400">{centerLabel}</span>}
        </div>
        <p className="section-subheading mb-4">{subtitle}</p>
      </div>
      <div className="h-52 w-full flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={4} dataKey="value" animationDuration={900}>
              {data.map((e, i) => <Cell key={i} fill={e.fill || COLORS_FALLBACK[i % COLORS_FALLBACK.length]} stroke="transparent" />)}
            </Pie>
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} iconType="circle" iconSize={8} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      {footerStats && (
        <div className="pt-4 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-center text-xs">
          {footerStats.map((s, i) => (
            <div key={i} className="bg-slate-900/50 p-2 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase tracking-wider">{s.label}</span>
              <span className="font-bold font-mono" style={{ color: s.color || '#f8fafc' }}>{s.value}</span>
            </div>
          ))}
        </div>
      )}
    </GlassCard>
  )
}

// TrendChartCard — area/bar with animated entrance
export function TrendChartCard({ title, subtitle, data = [], dataKey = 'value', color = '#6172f3', gradientId, href, hrefLabel, type = 'area', accent = 'brand' }) {
  const gid = gradientId || `grad-${Math.random().toString(36).slice(2,6)}`
  return (
    <GlassCard className="p-6 flex flex-col justify-between" accent={accent}>
      <div>
        <div className="flex items-center justify-between mb-1">
          <h3 className="section-heading"><TrendingUp className="w-4 h-4 text-emerald-400" />{title}</h3>
          {href && <Link to={href} className="text-xs text-brand-400 hover:text-brand-300 font-semibold flex items-center gap-1">{hrefLabel || 'View'} <ArrowUpRight className="w-3 h-3" /></Link>}
        </div>
        {subtitle && <p className="section-subheading mb-4">{subtitle}</p>}
      </div>
      <div className="h-52 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {type === 'bar' ? (
            <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey={dataKey} fill={color} radius={[6,6,0,0]} animationDuration={800} />
            </BarChart>
          ) : (
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} fill={`url(#${gid})`} animationDuration={1100} />
            </AreaChart>
          )}
        </ResponsiveContainer>
      </div>
    </GlassCard>
  )
}

// DataTableCard — glass table
export function DataTableCard({ title, subtitle, icon: Icon, columns = [], rows = [], footer, viewAllHref, emptyState, accent = 'brand' }) {
  return (
    <GlassCard className="p-6 space-y-4" accent={accent}>
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <div>
          <h3 className="section-heading">{Icon && <Icon className="w-4 h-4 text-indigo-400" />}{title}</h3>
          {subtitle && <p className="section-subheading">{subtitle}</p>}
        </div>
        {viewAllHref && <Link to={viewAllHref} className="btn-ghost text-xs py-1 px-2.5">View All</Link>}
      </div>
      {rows.length === 0 ? (
        emptyState || <p className="text-xs text-slate-500 italic py-8 text-center">No data.</p>
      ) : (
        <>
          <div className="table-container">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400">
                  {columns.map((c, i) => <th key={i} className={`p-3 font-semibold ${c.align === 'right' ? 'text-right' : ''}`}>{c.header}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, ri) => (
                  <tr key={ri} className="table-row">
                    {columns.map((c, ci) => (
                      <td key={ci} className={`p-3 ${c.align === 'right' ? 'text-right' : ''} ${c.mono ? 'font-mono' : ''}`}>{c.cell ? c.cell(r) : r[c.accessor]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {footer && <div className="text-xs text-slate-500 pt-2 border-t border-slate-800/60">{footer}</div>}
        </>
      )}
    </GlassCard>
  )
}
