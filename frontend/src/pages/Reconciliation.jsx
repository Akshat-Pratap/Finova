import { useState, useEffect, useRef } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import {
  Zap, BarChart3, Clock, CheckCircle, Brain, Database,
  Sparkles, AlertTriangle, XCircle, ArrowUpRight, RefreshCw, Layers,
  Activity, Play, Check
} from 'lucide-react'
import { startReconciliation, getRunStatus, getRunDetails } from '../api'
import {
  PageContainer, GlassCard, StatCard,
  Button, Spinner, Alert
} from '../components/ui'
import { PageHero, HealthMonitor } from '../components/templates'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'
import { useTheme } from '../context/ThemeContext'

export default function Reconciliation() {
  const [searchParams] = useSearchParams()
  const datasetId = searchParams.get('dataset_id')
  const isDatasetMode = Boolean(datasetId)

  const [numRecords, setNumRecords] = useState(250)
  const [seed, setSeed] = useState(42)
  const [running, setRunning] = useState(false)
  const [currentRunId, setCurrentRunId] = useState(null)
  const [liveProgress, setLiveProgress] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const { isDark } = useTheme()

  const pollTimerRef = useRef(null)

  useEffect(() => {
    return () => { if (pollTimerRef.current) clearInterval(pollTimerRef.current) }
  }, [])

  useEffect(() => {
    const savedRunId = localStorage.getItem('finova_active_run_id')
    if (savedRunId) { setCurrentRunId(savedRunId); setRunning(true); startPolling(savedRunId) }
  }, [])

  const startPolling = (runId) => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    const poll = async () => {
      try {
        const res = await getRunStatus(runId)
        if (!res) return
        const status = res.status || res.run?.status
        const total = res.total_records || res.run?.records_total || 0
        const processed = res.processed_records || res.run?.records_processed || 0
        const progressPct = res.progress_percent ?? (total > 0 ? (processed / total) * 100 : 0)
        setLiveProgress({
          run_id: runId, status, total_records: total, processed_records: processed, progress_percent: progressPct,
          matched_records: res.matched_records ?? res.run?.records_matched ?? 0,
          unmatched_records: res.unmatched_records ?? res.run?.records_unmatched ?? 0,
          exception_count: res.exception_count ?? 0,
          ai_investigated: res.ai_investigated ?? res.run?.records_ai_reviewed ?? 0,
          processing_rate: res.processing_rate ?? res.run?.processing_rate ?? 0,
          elapsed_seconds: res.elapsed_seconds ?? res.run?.elapsed_seconds ?? res.run?.processing_time_seconds ?? 0,
          error: res.error,
        })
        if (['COMPLETED', 'FAILED', 'CANCELLED', 'NO_COUNTERPART_SOURCE', 'STORAGE_LIMIT_REACHED'].includes(status)) {
          clearInterval(pollTimerRef.current); pollTimerRef.current = null; setRunning(false); localStorage.removeItem('finova_active_run_id')
          try {
            const fullDetails = await getRunDetails(runId)
            const runDoc = fullDetails.run || fullDetails
            setResult({ ...res, ...runDoc, status, records_processed: processed, records_matched: res.matched_records ?? runDoc.records_matched ?? 0, records_ai_reviewed: res.ai_investigated ?? runDoc.records_ai_reviewed ?? 0, records_manual_review: runDoc.records_manual_review ?? 0, records_duplicate: runDoc.records_duplicate ?? 0, records_mismatch: runDoc.records_mismatch ?? 0, exceptions_created: res.exception_count ?? 0, match_rate: runDoc.match_rate ?? (total > 0 ? (res.matched_records || 0) / total : 0), processing_time_seconds: res.elapsed_seconds ?? runDoc.processing_time_seconds ?? 0, analytics: runDoc.analytics || res.analytics || {} })
          } catch { setResult(res) }
          if (status === 'FAILED') setError(res.error || 'Reconciliation execution failed.')
        }
      } catch (err) { console.warn('Polling error:', err) }
    }
    poll(); pollTimerRef.current = setInterval(poll, 1500)
  }

  const handleRun = async () => {
    setRunning(true); setError(null); setResult(null); setLiveProgress(null)
    try {
      const payload = isDatasetMode ? { source: 'dataset', dataset_id: datasetId, async_mode: true } : { source: 'synthetic', num_records: numRecords, seed, async_mode: true }
      const res = await startReconciliation(payload)
      const runId = res.run_id
      if (runId) {
        setCurrentRunId(runId); localStorage.setItem('finova_active_run_id', runId)
        setLiveProgress({ run_id: runId, status: res.status || 'QUEUED', total_records: res.total_records || (isDatasetMode ? 0 : numRecords), processed_records: 0, progress_percent: 0, matched_records: 0, unmatched_records: 0, exception_count: 0, ai_investigated: 0, processing_rate: 0, elapsed_seconds: 0 })
        startPolling(runId)
      } else if (res.status) { setResult(res); setRunning(false) }
    } catch (e) { setError(e.message); setRunning(false) }
  }

  const chartData = result && result.status !== 'NO_COUNTERPART_SOURCE' ? [
    { name: 'Matched', value: result.records_matched || 0, fill: '#10b981' },
    { name: 'AI Review', value: result.records_ai_reviewed || 0, fill: '#06b6d4' },
    { name: 'Manual Review', value: result.records_manual_review || 0, fill: '#f59e0b' },
    { name: 'Duplicate', value: result.records_duplicate || 0, fill: '#e879f9' },
  ] : []

  const matchPct = result ? Math.round((result.match_rate || 0) * 100) : 0
  const estRemainingSec = (liveProgress?.processing_rate > 0 && liveProgress?.total_records > liveProgress?.processed_records) ? Math.round((liveProgress.total_records - liveProgress.processed_records) / liveProgress.processing_rate) : null

  return (
    <PageContainer>
      <PageHero
        title="Reconciliation Processing Engine"
        subtitle="Multi-pass deterministic matching, counterpart verification, and autonomous AI discrepancy triage."
        icon={Zap}
        accent="cyan"
        actions={running && (
          <div className="flex items-center gap-2 px-3.5 py-1.5 bg-cyan-500/10 border border-cyan-500/30 rounded-full text-cyan-600 dark:text-cyan-300 text-xs font-mono font-semibold">
            <span className="w-2 h-2 rounded-full bg-cyan-400 pulse-ring" style={{ color: '#22d3ee' }} />
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            Active Job In Progress
          </div>
        )}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <GlassCard className="p-6" accent="cyan" gradientBorder>
            <h2 className="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <Zap className="w-4 h-4 text-cyan-400" />
              Processing Configuration & Parameters
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 uppercase tracking-wider">Data Source Feed</label>
                <div className="input flex items-center justify-between text-slate-800 dark:text-slate-200">
                  {isDatasetMode ? (
                    <>
                      <span className="flex items-center gap-1.5 truncate"><Database className="w-3.5 h-3.5 text-cyan-500 shrink-0" /><span className="font-mono text-xs text-cyan-600 dark:text-cyan-300 truncate" title={datasetId}>{datasetId}</span></span>
                      <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded px-2 py-0.5 shrink-0 ml-2">UPLOADED</span>
                    </>
                  ) : (
                    <>
                      <span className="flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5 text-cyan-500" /><span>Synthetic Benchmark Feed</span></span>
                      <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded px-2 py-0.5">SYNTHETIC</span>
                    </>
                  )}
                </div>
              </div>
              {!isDatasetMode && (
                <div>
                  <div className="flex justify-between items-center mb-2"><label className="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">Volume ({numRecords} records)</label></div>
                  <input id="num-records-slider" type="range" min={50} max={1000} step={50} value={numRecords} onChange={(e) => setNumRecords(+e.target.value)} className="w-full accent-cyan-500 mt-2 cursor-pointer" disabled={running} />
                  <div className="flex justify-between text-[11px] text-slate-400 mt-1"><span>50</span><span>500</span><span>1000</span></div>
                </div>
              )}
              {!isDatasetMode && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 uppercase tracking-wider">Random Seed Number</label>
                  <input id="seed-input" type="number" value={seed} onChange={(e) => setSeed(+e.target.value)} className="input w-full text-xs" min={1} max={9999} disabled={running} />
                </div>
              )}
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-4 pt-4 border-t border-slate-800/50">
              <Button id="start-reconciliation-btn" variant="primary" size="md" onClick={handleRun} disabled={running} loading={running} icon={Zap} className="shadow-lg shadow-cyan-500/20 from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500">
                {running ? (isDatasetMode ? 'Processing dataset…' : `Processing ${numRecords} records…`) : 'Start Reconciliation Engine'}
              </Button>
              {running && <p className="text-xs text-slate-500 dark:text-slate-400 animate-pulse">Executing deterministic passes and queuing AI ambiguity scoring…</p>}
            </div>
          </GlassCard>
        </div>
        <HealthMonitor accent="teal" latency={liveProgress ? `${(liveProgress.elapsed_seconds || 0).toFixed(1)}s elapsed` : '~0.04s/batch'} uptime="99.98%" lastRun={result ? `${result.processing_time_seconds?.toFixed(2)}s ago` : '—'} status={running ? 'healthy' : result?.status === 'COMPLETED' ? 'healthy' : 'healthy'} metrics={liveProgress ? [{ label: 'Throughput', value: liveProgress.processing_rate > 0 ? `${Math.round(liveProgress.processing_rate)} rec/s` : '…' }, { label: 'Progress', value: `${(liveProgress.progress_percent||0).toFixed(1)}%` }] : []} />
      </div>

      {running && liveProgress && (
        <GlassCard className="p-6 border-cyan-500/30 space-y-4 banner-slide-in" accent="cyan">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-300 border border-cyan-500/20">{liveProgress.status || 'PROCESSING'}</span>
              <span className="text-xs text-slate-500 font-mono">Run: {liveProgress.run_id}</span>
            </div>
            <span className="text-sm font-bold text-cyan-600 dark:text-cyan-400 font-mono">{liveProgress.progress_percent?.toFixed(1)}%</span>
          </div>
          <div className="w-full h-3 bg-slate-100 dark:bg-dark-800 rounded-full overflow-hidden p-0.5 border border-slate-200 dark:border-dark-700 relative">
            <div className="h-full bg-gradient-to-r from-cyan-600 via-teal-500 to-emerald-500 rounded-full transition-all duration-500 ease-out relative overflow-hidden" style={{ width: `${Math.min(100, Math.max(0, liveProgress.progress_percent || 0))}%` }}>
              <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent" style={{ animation: 'shimmer 1.6s ease-in-out infinite' }} />
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 pt-2 text-xs stagger">
            {[
              { k: 'Processed', v: `${liveProgress.processed_records?.toLocaleString()} / ${liveProgress.total_records?.toLocaleString() || '…'}` },
              { k: 'Throughput', v: liveProgress.processing_rate > 0 ? `${Math.round(liveProgress.processing_rate).toLocaleString()} rec/s` : '…', c: 'text-emerald-400' },
              { k: 'Elapsed', v: `${liveProgress.elapsed_seconds?.toFixed(1)}s`, c: 'text-cyan-400' },
              { k: 'Est. Remaining', v: estRemainingSec !== null ? `${estRemainingSec}s` : '…', c: 'text-amber-400' },
              { k: 'Matched', v: liveProgress.matched_records?.toLocaleString(), c: 'text-emerald-400' },
              { k: 'Exceptions', v: liveProgress.exception_count?.toLocaleString(), c: 'text-amber-400' },
            ].map(s => (
              <div key={s.k} className="bg-slate-50 dark:bg-dark-800/80 p-2.5 rounded-xl border border-slate-200 dark:border-dark-700 hover:border-cyan-500/20 transition-colors">
                <span className="text-slate-400 block mb-0.5">{s.k}</span><span className={`font-mono font-semibold ${s.c || 'text-slate-900 dark:text-white'}`}>{s.v}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {error && <Alert type="error" title="Reconciliation Execution Failed" message={error} />}

      {result && result.status === 'NO_COUNTERPART_SOURCE' && (
        <GlassCard className="p-6 border-amber-500/40 bg-amber-500/5 space-y-4" accent="amber">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-600 dark:text-amber-400 shrink-0 mt-0.5 animate-float"><AlertTriangle className="w-6 h-6" /></div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-amber-700 dark:text-amber-300">Reconciliation Paused: No Counterpart Source Available</h3>
              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">{result.error_message || result.error || `This dataset contains ${(result.records_processed || result.total_records || 0).toLocaleString()} transactions, but no counterpart datasets exist to reconcile against.`}</p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 stagger">
            {[{ l: 'Transactions Ingested', v: (result.records_processed || result.total_records || 0).toLocaleString() }, { l: 'Exceptions Generated', v: '0 (None created)' }, { l: 'AI Tokens Consumed', v: '0 (Skipped)' }].map(x => (
              <div key={x.l} className="bg-white/80 dark:bg-dark-800/80 p-3 rounded-xl border border-slate-200 dark:border-dark-700"><p className="text-[11px] text-slate-500">{x.l}</p><p className="text-base font-bold font-mono mt-0.5">{x.v}</p></div>
            ))}
          </div>
          <div className="pt-2 flex items-center justify-between">
            <span className="text-xs text-slate-500">Upload a complementary counterpart source to match against.</span>
            <Link to="/datasets" className="btn-secondary text-xs flex items-center gap-1.5 py-1.5 px-3"><Layers className="w-3.5 h-3.5 text-cyan-500" /><span>Upload Counterpart Source</span><ArrowUpRight className="w-3 h-3" /></Link>
          </div>
        </GlassCard>
      )}

      {result && result.status === 'STORAGE_LIMIT_REACHED' && <Alert type="error" title="Storage Limit Protection Activated" message={result.error_message || "MongoDB Atlas storage quota reached. Reconciliation persistence was safely paused."} />}

      {result && result.status === 'COMPLETED' && (
        <div className="space-y-6">
          <Alert type="success" title={`Run ${result.run_id} Completed in ${result.processing_time_seconds?.toFixed(3)}s`} message={`${(result.records_processed || result.total_records || 0).toLocaleString()} records processed. Match rate: ${matchPct}%.`} />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 stagger">
            <StatCard label="Auto Matched" value={(result.records_matched || 0).toLocaleString()} icon={CheckCircle} color="emerald" subtitle={`${matchPct}% auto-reconciled`} />
            <StatCard label="AI Investigated" value={(result.records_ai_reviewed || 0).toLocaleString()} icon={Brain} color="cyan" subtitle="Ambiguous signals scored" />
            <StatCard label="Exceptions Created" value={(result.exceptions_created || result.records_manual_review || 0).toLocaleString()} icon={BarChart3} color="amber" subtitle="Human triage queue" />
            <StatCard label="Processing Speed" value={`${(result.processing_time_seconds || 0).toFixed(3)}s`} icon={Clock} color="fuchsia" subtitle={`${(result.records_processed || result.total_records || numRecords).toLocaleString()} total records`} />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <GlassCard className="p-6" accent="emerald" gradientBorder>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4">Status Distribution Breakdown</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={isDark ? 'rgba(75,85,99,0.2)' : 'rgba(226,232,240,0.8)'} />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: isDark ? '#94a3b8' : '#64748b' }} />
                  <YAxis tick={{ fontSize: 11, fill: isDark ? '#94a3b8' : '#64748b' }} />
                  <Tooltip contentStyle={{ background: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)', border: isDark ? '1px solid rgba(51, 65, 85, 0.8)' : '1px solid rgba(226, 232, 240, 0.9)', borderRadius: 12, fontSize: 12, color: isDark ? '#f8fafc' : '#0f172a' }} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]} animationDuration={800}>
                    {chartData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>
            {result.analytics?.ground_truth_available && (
              <GlassCard className="p-6" accent="brand">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4">Classification Metrics (Ground Truth)</h3>
                <div className="space-y-4 stagger">
                  {[{ label: 'Precision Rate', value: result.analytics.precision, color: 'text-emerald-400' }, { label: 'Recall Rate', value: result.analytics.recall, color: 'text-cyan-400' }, { label: 'F1 Balanced Benchmark', value: result.analytics.f1_score, color: 'text-fuchsia-400' }].map(({ label, value, color }) => (
                    <div key={label}>
                      <div className="flex justify-between text-xs mb-1 font-medium"><span className="text-slate-600 dark:text-slate-400">{label}</span><span className={`font-bold font-mono ${color}`}>{(value * 100).toFixed(1)}%</span></div>
                      <div className="h-2 bg-slate-100 dark:bg-dark-800 rounded-full overflow-hidden"><div className={`h-full rounded-full ${color.replace('text-', 'bg-')}`} style={{ width: `${(value * 100).toFixed(1)}%`, transition: 'width 0.9s cubic-bezier(0.16,1,0.3,1)' }} /></div>
                    </div>
                  ))}
                  <div className="mt-4 pt-4 border-t border-slate-200 dark:border-dark-700 grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-slate-50 dark:bg-dark-800/80 rounded-xl p-2.5 border border-slate-200 dark:border-dark-700"><p className="text-slate-500 text-[11px]">True Positives</p><p className="text-emerald-400 font-bold text-base mt-0.5">{result.analytics.true_positives}</p></div>
                    <div className="bg-slate-50 dark:bg-dark-800/80 rounded-xl p-2.5 border border-slate-200 dark:border-dark-700"><p className="text-slate-500 text-[11px]">False Positives</p><p className="text-rose-400 font-bold text-base mt-0.5">{result.analytics.false_positives}</p></div>
                  </div>
                </div>
              </GlassCard>
            )}
          </div>
        </div>
      )}
    </PageContainer>
  )
}
