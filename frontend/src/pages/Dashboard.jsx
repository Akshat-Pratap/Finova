import { useState, useEffect } from 'react'
import {
  GitMerge, CreditCard, AlertTriangle, Activity, TrendingUp,
  Zap, CheckCircle, Clock, Brain, BarChart3
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, Legend
} from 'recharts'
import { getAnalyticsSummary, getRunMetrics, listRuns, listExceptions, startReconciliation } from '../api'
import { StatCard, StatusBadge, ConfidenceBar, Spinner, Currency } from '../components/ui'

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

  const fetchData = async () => {
    try {
      const [runsData, excsData] = await Promise.allSettled([
        listRuns({ limit: 5 }),
        listExceptions({ limit: 5 }),
      ])
      if (runsData.status === 'fulfilled') setRuns(runsData.value.runs || [])
      if (excsData.status === 'fulfilled') setExceptions(excsData.value.exceptions || [])

      // Get latest run metrics
      if (runsData.status === 'fulfilled' && runsData.value.runs?.length > 0) {
        const latest = runsData.value.runs[0]
        try {
          const m = await getRunMetrics(latest.run_id)
          setMetrics({ ...m.run, breakdown: m.status_breakdown })
        } catch {}
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

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
    : []

  const matchRate = metrics ? Math.round((metrics.match_rate || 0) * 100) : 0
  const avgConf = metrics ? Math.round((metrics.average_confidence || 0) * 100) : 0

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            <span className="text-gradient">Financial Operations</span> Dashboard
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Real-time reconciliation metrics and AI investigation status
          </p>
        </div>
        <button
          id="run-reconciliation-btn"
          onClick={handleQuickRun}
          disabled={running}
          className="btn-primary gap-2"
        >
          {running ? (
            <><Spinner size="sm" /> Processing…</>
          ) : (
            <><Zap className="w-4 h-4" /> Run Reconciliation</>
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Last run result banner */}
      {lastRunResult && (
        <div className="bg-green-900/20 border border-green-700/50 rounded-lg p-4 flex items-center gap-4 animate-slide-up">
          <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-green-300 font-medium text-sm">Reconciliation complete — {lastRunResult.run_id}</p>
            <p className="text-gray-400 text-xs mt-0.5">
              {lastRunResult.records_matched}/{lastRunResult.records_processed} matched &middot;
              {' '}{lastRunResult.records_ai_reviewed} AI reviewed &middot;
              {' '}{Math.round((lastRunResult.match_rate || 0) * 100)}% match rate &middot;
              {' '}{lastRunResult.processing_time_seconds?.toFixed(3)}s
            </p>
          </div>
          <button onClick={() => setLastRunResult(null)} className="text-gray-500 hover:text-gray-300 text-lg">&times;</button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-center space-y-3">
            <Spinner size="lg" />
            <p className="text-gray-400 text-sm">Loading dashboard…</p>
          </div>
        </div>
      ) : (
        <>
          {/* Stats row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Match Rate"
              value={`${matchRate}%`}
              subtitle={metrics ? `${metrics.records_matched || 0} of ${metrics.records_received || 0} records` : 'No runs yet'}
              icon={CheckCircle}
              color="green"
            />
            <StatCard
              label="Avg. Confidence"
              value={`${avgConf}%`}
              subtitle="Weighted confidence score"
              icon={Activity}
              color="brand"
            />
            <StatCard
              label="AI Investigated"
              value={metrics?.records_ai_reviewed ?? 0}
              subtitle="Ambiguous cases resolved by AI"
              icon={Brain}
              color="purple"
            />
            <StatCard
              label="Open Exceptions"
              value={exceptions.length}
              subtitle="Requiring human review"
              icon={AlertTriangle}
              color="amber"
            />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Status breakdown pie */}
            <div className="card p-5">
              <h3 className="section-heading mb-4">Status Distribution</h3>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#151d38', border: '1px solid #2d3b6b', borderRadius: 8, fontSize: 12 }}
                      formatter={(v, name) => [v, name]}
                    />
                    <Legend formatter={(v) => <span className="text-xs text-gray-300">{v}</span>} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
                  Run a reconciliation to see the breakdown
                </div>
              )}
            </div>

            {/* Recent runs bar chart */}
            <div className="card p-5">
              <h3 className="section-heading mb-4">Recent Runs</h3>
              {runs.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={runs.slice(0, 5).reverse()} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(45,59,107,0.5)" />
                    <XAxis dataKey="run_id" tick={{ fontSize: 10, fill: '#9ca3af' }} tickFormatter={v => v.slice(-6)} />
                    <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} />
                    <Tooltip
                      contentStyle={{ background: '#151d38', border: '1px solid #2d3b6b', borderRadius: 8, fontSize: 12 }}
                    />
                    <Bar dataKey="records_matched" name="Matched" fill="#22c55e" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="records_ai_reviewed" name="AI Review" fill="#6172f3" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
                  No runs yet — click "Run Reconciliation" to start
                </div>
              )}
            </div>
          </div>

          {/* Recent exceptions */}
          <div className="card">
            <div className="p-5 border-b border-dark-600 flex items-center justify-between">
              <h3 className="section-heading mb-0">Recent Exceptions</h3>
              <a href="/exceptions" className="text-xs text-brand-400 hover:text-brand-300">View all →</a>
            </div>
            <div className="divide-y divide-dark-600">
              {exceptions.length === 0 ? (
                <div className="p-8 text-center text-gray-500 text-sm">No exceptions yet</div>
              ) : (
                exceptions.map((exc) => (
                  <div key={exc.exception_id} className="table-row px-5 py-3 flex items-center gap-4">
                    <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white font-medium truncate">{exc.exception_id}</p>
                      <p className="text-xs text-gray-400 truncate">{exc.description}</p>
                    </div>
                    <span className={`badge text-xs ${
                      exc.severity === 'CRITICAL' ? 'bg-red-900/50 text-red-400 border border-red-700/50' :
                      exc.severity === 'HIGH' ? 'bg-orange-900/50 text-orange-400 border border-orange-700/50' :
                      'bg-amber-900/50 text-amber-400 border border-amber-700/50'
                    }`}>{exc.severity}</span>
                    <Currency amount={exc.difference} />
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
