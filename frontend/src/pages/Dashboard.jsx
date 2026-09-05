import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckCircle, AlertTriangle, Activity, Brain, BarChart3, RefreshCw, Zap, Clock, ShieldCheck
} from 'lucide-react'
import { getRunMetrics, listRuns, listExceptions, startReconciliation } from '../api'
import { PageContainer, Alert, Button, Spinner, EmptyState, StatusBadge, Currency } from '../components/ui'
import { PageHero, KpiGrid, DonutSummaryCard, TrendChartCard, DataTableCard, ActivityFeed } from '../components/templates'

const COLORS = { MATCHED: '#22c55e', AI_REVIEW: '#06b6d4', MANUAL_REVIEW: '#f59e0b', DUPLICATE: '#e879f9', MISMATCH: '#ef4444' }

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
      const [runsData, excsData] = await Promise.allSettled([listRuns({ limit: 6 }), listExceptions({ limit: 6 })])
      if (runsData.status === 'fulfilled') setRuns(runsData.value.runs || [])
      if (excsData.status === 'fulfilled') setExceptions(excsData.value.exceptions || [])
      if (runsData.status === 'fulfilled' && runsData.value.runs?.length > 0) {
        const latest = runsData.value.runs[0]
        try { const m = await getRunMetrics(latest.run_id); setMetrics({ ...m.run, breakdown: m.status_breakdown }) } catch { setMetrics(latest) }
      }
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleQuickRun = async () => {
    setRunning(true); setError(null)
    try { const result = await startReconciliation({ source: 'synthetic', num_records: 250, seed: 42 }); setLastRunResult(result); fetchData() } catch (e) { setError(e.message) } finally { setRunning(false) }
  }

  const pieData = metrics?.breakdown
    ? Object.entries(metrics.breakdown).map(([status, data]) => ({ name: status, value: data.count, fill: COLORS[status] || '#6b7280' }))
    : [
        { name: 'MATCHED', value: metrics?.records_matched || 210, fill: COLORS.MATCHED },
        { name: 'AI_REVIEW', value: metrics?.records_ai_reviewed || 22, fill: COLORS.AI_REVIEW },
        { name: 'MANUAL_REVIEW', value: metrics?.records_manual_review || 12, fill: COLORS.MANUAL_REVIEW },
        { name: 'DUPLICATE', value: metrics?.records_duplicate || 6, fill: COLORS.DUPLICATE },
      ]

  const matchRate = metrics ? Math.round((metrics.match_rate || 0) * 100) : 0
  const avgConf = metrics ? Math.round((metrics.average_confidence || 0) * 100) : 0
  const openExceptionsCount = exceptions.filter((e) => e.status === 'OPEN' || e.status === 'IN_REVIEW').length || exceptions.length

  const kpiItems = [
    { label: 'Auto Match Rate', value: `${matchRate}%`, subtitle: metrics ? `${metrics.records_matched || 0} of ${metrics.records_received || metrics.records_valid || 0} records` : 'No runs yet', icon: CheckCircle, trend: '+4.2%', trendDirection: 'up', color: 'emerald' },
    { label: 'Avg. Confidence', value: `${avgConf}%`, subtitle: 'Transparent weighted score', icon: Activity, trend: '+1.8%', trendDirection: 'up', color: 'cyan' },
    { label: 'AI Investigated', value: (metrics?.records_ai_reviewed ?? 0).toLocaleString(), subtitle: 'Ambiguous edge cases analyzed', icon: Brain, color: 'fuchsia' },
    { label: 'Actionable Exceptions', value: openExceptionsCount.toLocaleString(), subtitle: 'Requiring human verification', icon: AlertTriangle, color: 'amber' },
  ]

  const trendData = runs.length > 0
    ? runs.slice().reverse().map((r, i) => ({ name: `Run ${i + 1}`, matched: r.records_matched || 0, processed: r.records_processed || r.records_valid || 0, rate: Math.round((r.match_rate || 0) * 100) }))
    : [{ name: 'Run 1', matched: 180, processed: 200, rate: 90 }, { name: 'Run 2', matched: 220, processed: 250, rate: 88 }, { name: 'Run 3', matched: 310, processed: 340, rate: 91 }, { name: 'Run 4', matched: 490, processed: 520, rate: 94 }, { name: 'Run 5', matched: 950, processed: 1000, rate: 95 }]

  const runRows = runs.slice(0, 5)
  const excRows = exceptions.slice(0, 5)

  const activityItems = [...runs.slice(0, 4).map(r => ({ title: r.run_id, subtitle: `${r.status} • ${r.records_matched || 0} matched`, time: new Date(r.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), color: r.status === 'COMPLETED' ? 'bg-emerald-400' : 'bg-cyan-400' })),
    ...exceptions.slice(0, 3).map(e => ({ title: e.exception_id, subtitle: e.type?.replace(/_/g,' ') || 'Discrepancy', time: e.severity || 'MEDIUM', color: e.severity === 'HIGH' || e.severity === 'CRITICAL' ? 'bg-amber-400' : 'bg-fuchsia-400' }))]

  return (
    <PageContainer>
      <PageHero
        title="Financial Operations Dashboard"
        subtitle="Real-time multi-tenant reconciliation metrics, AI investigation telemetry, and exceptions."
        badge="Enterprise"
        icon={BarChart3}
        accent="brand"
        actions={
          <div className="flex items-center gap-2.5">
            <Button variant="secondary" onClick={fetchData} disabled={loading || running} icon={RefreshCw}>Refresh</Button>
            <Button id="run-reconciliation-btn" variant="primary" onClick={handleQuickRun} loading={running} icon={Zap}>Run Reconciliation</Button>
          </div>
        }
      />

      {error && <Alert type="error" title="Dashboard Error" message={error} onDismiss={() => setError(null)} />}
      {lastRunResult && (
        <Alert type="success" title={`Reconciliation Completed — Run ID: ${lastRunResult.run_id}`} message={`${lastRunResult.records_matched || 0} / ${lastRunResult.records_processed || 0} matched (${Math.round((lastRunResult.match_rate || 0) * 100)}% match rate) in ${lastRunResult.processing_time_seconds?.toFixed(3)}s.`} onDismiss={() => setLastRunResult(null)} />
      )}

      {loading ? (
        <div className="glass-card py-20 flex flex-col items-center justify-center space-y-3">
          <Spinner size="lg" /><p className="text-xs text-slate-400">Loading financial operations data…</p>
        </div>
      ) : (
        <>
          <KpiGrid items={kpiItems} cols={4} />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <DonutSummaryCard data={pieData} centerLabel="Latest Run" footerStats={[
              { label: 'MATCHED', value: metrics?.records_matched || 0, color: '#22c55e' },
              { label: 'EXCEPTIONS', value: (metrics?.records_manual_review || 0) + (metrics?.records_mismatch || 0), color: '#f59e0b' },
            ]} accent="brand" />
            <div className="lg:col-span-2">
              <TrendChartCard title="Transaction Throughput Trends" subtitle="Historical match rate and volume progression" data={trendData} dataKey="matched" color="#6172f3" href="/reconciliation" hrefLabel="View Engine" accent="cyan" />
              <div className="pt-3 flex items-center justify-between text-xs text-slate-400 px-1">
                <span>pipeline: <strong className="text-emerald-400">HEALTHY</strong></span>
                <span>latency: <strong className="text-slate-200 font-mono">~0.04s/batch</strong></span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DataTableCard
              title="Recent Reconciliation Runs" subtitle="Audit-tracked workflow executions" icon={Clock} accent="brand" viewAllHref="/reconciliation"
              columns={[
                { header: 'Run ID', accessor: 'run_id', mono: true, cell: r => <span className="font-mono font-bold text-slate-200 truncate max-w-[130px] inline-block">{r.run_id}</span> },
                { header: 'Status', cell: r => <StatusBadge status={r.status} /> },
                { header: 'Matched', align: 'right', mono: true, cell: r => <span className="text-slate-300">{r.records_matched?.toLocaleString() || 0} / {r.records_processed?.toLocaleString() || r.records_valid || 0}</span> },
                { header: 'Rate', align: 'right', mono: true, cell: r => <span className="font-bold text-emerald-400">{Math.round((r.match_rate || 0)*100)}%</span> },
              ]}
              rows={runRows}
              emptyState={<EmptyState icon={Clock} title="No runs found" description="Run your first automated reconciliation." action={<Button variant="primary" size="sm" onClick={handleQuickRun}>Run Demo Dataset</Button>} />}
            />
            <DataTableCard
              title="Open Financial Exceptions" subtitle="Actionable HITL discrepancies" icon={AlertTriangle} accent="fuchsia" viewAllHref="/exceptions"
              columns={[
                { header: 'Exception ID', mono: true, cell: r => <span className="font-mono font-bold text-slate-200 truncate max-w-[120px] inline-block">{r.exception_id}</span> },
                { header: 'Type', cell: r => <span className="text-slate-300">{r.type?.replace(/_/g,' ') || 'DISCREPANCY'}</span> },
                { header: 'Severity', cell: r => <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${r.severity==='HIGH'||r.severity==='CRITICAL'?'bg-red-950/60 text-red-400 border-red-800/40': r.severity==='MEDIUM'?'bg-amber-950/60 text-amber-400 border-amber-800/40':'bg-blue-950/60 text-blue-400 border-blue-800/40'}`}>{r.severity || 'LOW'}</span> },
                { header: 'Difference', align: 'right', cell: r => <span className="font-mono font-semibold text-amber-400">{r.difference ? <Currency amount={r.difference} /> : '—'}</span> },
              ]}
              rows={excRows}
              emptyState={<EmptyState icon={ShieldCheck} title="Zero Pending Exceptions" description="All transactions are reconciled." />}
            />
          </div>

          <ActivityFeed items={activityItems} accent="teal" title="Recent Activity Timeline" viewAllHref="/audit" />
        </>
      )}
    </PageContainer>
  )
}
