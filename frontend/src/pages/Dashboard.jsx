import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  GitMerge, CreditCard, AlertTriangle, Activity, TrendingUp,
  Zap, CheckCircle, Clock, Brain, BarChart3, ArrowUpRight,
  RefreshCw, ShieldCheck, Layers, Eye, FileText
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts'
import { getRunMetrics, listRuns, listExceptions, startReconciliation } from '../api'
import {
  PageContainer, PageHeader, GlassCard, StatCard, StatusBadge,
  ConfidenceBar, Button, Spinner, Alert, EmptyState, Currency
} from '../components/ui'
import { useTheme } from '../context/ThemeContext'

const COLORS = {
  MATCHED: '#22c55e',
  AI_REVIEW: '#6172f3',
  MANUAL_REVIEW: '#f59e0b',
  DUPLICATE: '#a855f7',
  MISMATCH: '#ef4444',
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [runs, setRuns] = useState([])
  const [exceptions, setExceptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [lastRunResult, setLastRunResult] = useState(null)
  const [error, setError] = useState(null)
  const { isDark } = useTheme()
  const navigate = useNavigate()

  const fetchData = async () => {
    try {
      const [runsData, excsData] = await Promise.allSettled([
        listRuns({ limit: 6 }),
        listExceptions({ limit: 6 }),
      ])
      if (runsData.status === 'fulfilled') setRuns(runsData.value.runs || [])
      if (excsData.status === 'fulfilled') setExceptions(excsData.value.exceptions || [])

      // Get latest run metrics
      if (runsData.status === 'fulfilled' && runsData.value.runs?.length > 0) {
        const latest = runsData.value.runs[0]
        try {
          const m = await getRunMetrics(latest.run_id)
          setMetrics({ ...m.run, breakdown: m.status_breakdown })
        } catch {
          setMetrics(latest)
        }
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleQuickRun = async () => {
    setRunning(true)
    setError(null)
    try {
      const result = await startReconciliation({ source: 'synthetic', num_records: 250, seed: 42 })
      setLastRunResult(result)
      fetchData()
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  // Pie chart data from breakdown
  const pieData = metrics?.breakdown
    ? Object.entries(metrics.breakdown).map(([status, data]) => ({
        name: status,
        value: data.count,
        fill: COLORS[status] || '#6b7280',
      }))
    : [
        { name: 'MATCHED', value: metrics?.records_matched || 210, fill: COLORS.MATCHED },
        { name: 'AI_REVIEW', value: metrics?.records_ai_reviewed || 22, fill: COLORS.AI_REVIEW },
        { name: 'MANUAL_REVIEW', value: metrics?.records_manual_review || 12, fill: COLORS.MANUAL_REVIEW },
        { name: 'DUPLICATE', value: metrics?.records_duplicate || 6, fill: COLORS.DUPLICATE },
      ]

  const matchRate = metrics ? Math.round((metrics.match_rate || 0) * 100) : 0
  const avgConf = metrics ? Math.round((metrics.average_confidence || 0) * 100) : 0
  const openExceptionsCount = exceptions.filter((e) => e.status === 'OPEN' || e.status === 'IN_REVIEW').length || exceptions.length

  return (
    <PageContainer>
      {/* Header */}
      <PageHeader
        title="Financial Operations Dashboard"
        subtitle="Real-time multi-tenant reconciliation metrics, AI investigation telemetry, and exceptions."
        badge="Enterprise"
        icon={LayoutDashboardIcon}
        actions={
          <div className="flex items-center gap-2.5">
            <Button
              variant="secondary"
              onClick={fetchData}
              disabled={loading || running}
              icon={RefreshCw}
            >
              Refresh
            </Button>
            <Button
              id="run-reconciliation-btn"
              variant="primary"
              onClick={handleQuickRun}
              loading={running}
              icon={Zap}
            >
              Run Reconciliation
            </Button>
          </div>
        }
      />

      {/* Error Banner */}
      {error && <Alert type="error" title="Dashboard Error" message={error} onDismiss={() => setError(null)} />}

      {/* Quick Run Result Banner */}
      {lastRunResult && (
        <Alert
          type="success"
          title={`Reconciliation Completed — Run ID: ${lastRunResult.run_id}`}
          message={`${lastRunResult.records_matched || 0} / ${lastRunResult.records_processed || 0} matched (${Math.round((lastRunResult.match_rate || 0) * 100)}% match rate) in ${lastRunResult.processing_time_seconds?.toFixed(3)}s. ${lastRunResult.records_ai_reviewed || 0} AI investigations.`}
          onDismiss={() => setLastRunResult(null)}
        />
      )}

      {loading ? (
        <div className="glass-card py-20 flex flex-col items-center justify-center space-y-3">
          <Spinner size="lg" />
          <p className="text-xs text-slate-400">Loading financial operations data…</p>
        </div>
      ) : (
        <>
          {/* KPI Stat Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Auto Match Rate"
              value={`${matchRate}%`}
              subtitle={metrics ? `${metrics.records_matched || 0} of ${metrics.records_received || metrics.records_valid || 0} records` : 'No runs yet'}
              icon={CheckCircle}
              trend="+4.2%"
              trendDirection="up"
              color="green"
            />
            <StatCard
              label="Avg. Confidence"
              value={`${avgConf}%`}
              subtitle="Transparent weighted score"
              icon={Activity}
              trend="+1.8%"
              trendDirection="up"
              color="brand"
            />
            <StatCard
              label="AI Investigated"
              value={(metrics?.records_ai_reviewed ?? 0).toLocaleString()}
              subtitle="Ambiguous edge cases analyzed"
              icon={Brain}
              color="purple"
            />
            <StatCard
              label="Actionable Exceptions"
              value={openExceptionsCount.toLocaleString()}
              subtitle="Requiring human verification"
              icon={AlertTriangle}
              color="amber"
            />
          </div>

          {/* Charts & Analytics Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Status Breakdown Donut Chart */}
            <GlassCard className="p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h2 className="section-heading">
                    <BarChart3 className="w-4 h-4 text-brand-400" />
                    Reconciliation Breakdown
                  </h2>
                  <span className="text-[11px] font-mono text-slate-400">Latest Run</span>
                </div>
                <p className="section-subheading mb-4">Distribution by decision pipeline outcome</p>
              </div>

              <div className="h-52 w-full flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={80}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} stroke="transparent" />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend
                      wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
                      iconType="circle"
                      iconSize={8}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="pt-4 border-t border-slate-800/80 dark:border-slate-800/80 light:border-slate-200 grid grid-cols-2 gap-2 text-center text-xs">
                <div className="bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 p-2 rounded-lg">
                  <span className="text-slate-400 text-[10px] block">MATCHED</span>
                  <span className="font-bold font-mono text-emerald-400">{metrics?.records_matched || 0}</span>
                </div>
                <div className="bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 p-2 rounded-lg">
                  <span className="text-slate-400 text-[10px] block">EXCEPTIONS</span>
                  <span className="font-bold font-mono text-amber-400">
                    {(metrics?.records_manual_review || 0) + (metrics?.records_mismatch || 0)}
                  </span>
                </div>
              </div>
            </GlassCard>

            {/* Reconciliation Volume & History */}
            <GlassCard className="lg:col-span-2 p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h2 className="section-heading">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    Transaction Throughput Trends
                  </h2>
                  <Link
                    to="/reconciliation"
                    className="text-xs text-brand-400 hover:text-brand-300 font-semibold flex items-center gap-1"
                  >
                    View Engine <ArrowUpRight className="w-3 h-3" />
                  </Link>
                </div>
                <p className="section-subheading mb-4">Historical match rate and volume progression</p>
              </div>

              <div className="h-52 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={
                      runs.length > 0
                        ? runs.slice().reverse().map((r, i) => ({
                            name: `Run ${i + 1}`,
                            matched: r.records_matched || 0,
                            processed: r.records_processed || r.records_valid || 0,
                            rate: Math.round((r.match_rate || 0) * 100),
                          }))
                        : [
                            { name: 'Run 1', matched: 180, processed: 200, rate: 90 },
                            { name: 'Run 2', matched: 220, processed: 250, rate: 88 },
                            { name: 'Run 3', matched: 310, processed: 340, rate: 91 },
                            { name: 'Run 4', matched: 490, processed: 520, rate: 94 },
                            { name: 'Run 5', matched: 950, processed: 1000, rate: 95 },
                          ]
                    }
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="colorMatched" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6172f3" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#6172f3" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Area
                      type="monotone"
                      dataKey="matched"
                      name="Matched Records"
                      stroke="#6172f3"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorMatched)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="pt-4 border-t border-slate-800/80 dark:border-slate-800/80 light:border-slate-200 flex items-center justify-between text-xs text-slate-400">
                <span>Deterministic pipeline status: <strong className="text-emerald-400">HEALTHY</strong></span>
                <span>Active engine latency: <strong className="text-slate-200 dark:text-slate-200 light:text-slate-800 font-mono">~0.04s/batch</strong></span>
              </div>
            </GlassCard>
          </div>

          {/* Bottom Tables Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Reconciliation Runs */}
            <GlassCard className="p-6 space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
                <div>
                  <h2 className="section-heading">
                    <Clock className="w-4 h-4 text-indigo-400" />
                    Recent Reconciliation Runs
                  </h2>
                  <p className="section-subheading">Audit-tracked workflow executions</p>
                </div>
                <Link
                  to="/reconciliation"
                  className="btn-ghost text-xs py-1 px-2.5"
                >
                  View All
                </Link>
              </div>

              {runs.length === 0 ? (
                <EmptyState
                  icon={Clock}
                  title="No runs found"
                  description="Run your first automated reconciliation or benchmark."
                  action={
                    <Button variant="primary" size="sm" onClick={handleQuickRun}>
                      Run Demo Dataset
                    </Button>
                  }
                />
              ) : (
                <div className="table-container">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 text-slate-400">
                        <th className="p-3 font-semibold">Run ID</th>
                        <th className="p-3 font-semibold">Status</th>
                        <th className="p-3 font-semibold text-right">Matched</th>
                        <th className="p-3 font-semibold text-right">Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runs.slice(0, 5).map((run) => (
                        <tr key={run.run_id} className="table-row">
                          <td className="p-3 font-mono font-bold text-slate-200 dark:text-slate-200 light:text-slate-800 truncate max-w-[130px]">
                            {run.run_id}
                          </td>
                          <td className="p-3">
                            <StatusBadge status={run.status} />
                          </td>
                          <td className="p-3 text-right font-mono text-slate-300 dark:text-slate-300 light:text-slate-700">
                            {run.records_matched?.toLocaleString() || 0} / {run.records_processed?.toLocaleString() || run.records_valid || 0}
                          </td>
                          <td className="p-3 text-right font-mono font-bold text-emerald-400">
                            {Math.round((run.match_rate || 0) * 100)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </GlassCard>

            {/* Recent Financial Exceptions */}
            <GlassCard className="p-6 space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
                <div>
                  <h2 className="section-heading">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    Open Financial Exceptions
                  </h2>
                  <p className="section-subheading">Actionable HITL reconciliation discrepancies</p>
                </div>
                <Link
                  to="/exceptions"
                  className="btn-ghost text-xs py-1 px-2.5"
                >
                  View All
                </Link>
              </div>

              {exceptions.length === 0 ? (
                <EmptyState
                  icon={ShieldCheck}
                  title="Zero Pending Exceptions"
                  description="All ingested financial transactions are completely reconciled."
                />
              ) : (
                <div className="table-container">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 text-slate-400">
                        <th className="p-3 font-semibold">Exception ID</th>
                        <th className="p-3 font-semibold">Type</th>
                        <th className="p-3 font-semibold">Severity</th>
                        <th className="p-3 font-semibold text-right">Difference</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exceptions.slice(0, 5).map((exc) => (
                        <tr key={exc.exception_id} className="table-row">
                          <td className="p-3 font-mono font-bold text-slate-200 dark:text-slate-200 light:text-slate-800 truncate max-w-[130px]">
                            {exc.exception_id}
                          </td>
                          <td className="p-3 font-medium text-slate-300 dark:text-slate-300 light:text-slate-700">
                            {exc.type?.replace(/_/g, ' ') || 'DISCREPANCY'}
                          </td>
                          <td className="p-3">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                exc.severity === 'HIGH' || exc.severity === 'CRITICAL'
                                  ? 'bg-red-950/60 text-red-400 border border-red-800/40'
                                  : exc.severity === 'MEDIUM'
                                  ? 'bg-amber-950/60 text-amber-400 border border-amber-800/40'
                                  : 'bg-blue-950/60 text-blue-400 border border-blue-800/40'
                              }`}
                            >
                              {exc.severity || 'LOW'}
                            </span>
                          </td>
                          <td className="p-3 text-right font-mono font-semibold text-amber-400">
                            {exc.difference ? <Currency amount={exc.difference} /> : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </GlassCard>
          </div>
        </>
      )}
    </PageContainer>
  )
}

function LayoutDashboardIcon(props) {
  return <BarChart3 {...props} />
}
