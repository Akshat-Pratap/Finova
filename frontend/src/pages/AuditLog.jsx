import React, { useState, useEffect } from 'react'
import {
  FileText, Activity, Brain, CheckCircle, AlertTriangle, Zap,
  ShieldCheck, ShieldAlert, RefreshCw, Key, Copy, Check, Filter,
  Search, Lock
} from 'lucide-react'
import { getAuditLogs, verifyAuditIntegrity } from '../api'
import { PageContainer, PageHeader, GlassCard, Button, Alert, Spinner } from '../components/ui'

const EVENT_ICONS = {
  PROCESSING_STARTED: { Icon: Zap, color: 'text-indigo-600 dark:text-indigo-400', bg: 'bg-indigo-500/10' },
  PROCESSING_COMPLETED: { Icon: CheckCircle, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-500/10' },
  AI_INVESTIGATION_STARTED: { Icon: Brain, color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-500/10' },
  AI_INVESTIGATION_COMPLETED: { Icon: Brain, color: 'text-purple-600 dark:text-purple-300', bg: 'bg-purple-500/10' },
  EXCEPTION_CREATED: { Icon: AlertTriangle, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-500/10' },
  EXCEPTION_RESOLVED: { Icon: CheckCircle, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-500/10' },
  EXCEPTION_REJECTED: { Icon: AlertTriangle, color: 'text-rose-600 dark:text-rose-400', bg: 'bg-rose-500/10' },
  EXCEPTION_IGNORED: { Icon: Activity, color: 'text-slate-500 dark:text-slate-400', bg: 'bg-slate-500/10' },
  DATASET_GENERATED: { Icon: FileText, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-500/10' },
  DATASET_UPLOADED: { Icon: FileText, color: 'text-cyan-600 dark:text-cyan-400', bg: 'bg-cyan-500/10' },
  INTEGRATION_SYNCED: { Icon: RefreshCw, color: 'text-indigo-600 dark:text-indigo-400', bg: 'bg-indigo-500/10' },
  SETTINGS_CHANGED: { Icon: Activity, color: 'text-amber-600 dark:text-amber-300', bg: 'bg-amber-500/10' },
  MEMBER_INVITED: { Icon: Activity, color: 'text-teal-600 dark:text-teal-400', bg: 'bg-teal-500/10' },
}

export default function AuditLog() {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [runId, setRunId] = useState('')
  const [verifying, setVerifying] = useState(false)
  const [verificationResult, setVerificationResult] = useState(null)
  const [copiedHash, setCopiedHash] = useState(null)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const data = await getAuditLogs({ limit: 100, processing_run_id: runId || undefined })
      setLogs(data.logs || [])
      setTotal(data.total || 0)
    } catch (err) {
      console.warn('Failed to load audit logs:', err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [runId])

  const handleVerifyIntegrity = async () => {
    setVerifying(true)
    try {
      const res = await verifyAuditIntegrity()
      setVerificationResult(res)
    } catch (err) {
      setVerificationResult({ verified: false, error: err.message })
    } finally {
      setVerifying(false)
    }
  }

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text)
    setCopiedHash(id)
    setTimeout(() => setCopiedHash(null), 2000)
  }

  return (
    <PageContainer>
      <PageHeader
        title="Tamper-Evident Audit Trail"
        subtitle="Immutable, cryptographic SHA-256 hash-chained ledger of every system reconciliation, exception disposition, and manual adjustment."
        icon={ShieldCheck}
        actions={
          <div className="flex items-center gap-3">
            <Button
              variant="primary"
              size="sm"
              onClick={handleVerifyIntegrity}
              loading={verifying}
              icon={ShieldCheck}
              className="bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-600/25"
            >
              {verifying ? 'Verifying Chain Hashes...' : 'Verify Cryptographic Chain'}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchLogs}
              icon={RefreshCw}
            >
              Refresh
            </Button>
          </div>
        }
      />

      {/* Verification Results Banner */}
      {verificationResult && (
        <div className={`p-5 rounded-2xl border flex items-start justify-between ${
          verificationResult.verified
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-800 dark:text-emerald-200'
            : 'bg-rose-500/10 border-rose-500/30 text-rose-800 dark:text-rose-200'
        }`}>
          <div className="flex items-start space-x-3.5">
            {verificationResult.verified ? (
              <ShieldCheck className="w-6 h-6 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <ShieldAlert className="w-6 h-6 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
            )}
            <div className="space-y-1">
              <div className="text-sm font-bold">
                {verificationResult.verified
                  ? 'Audit Chain Verified & Tamper-Evident'
                  : 'Audit Chain Verification Failed'}
              </div>
              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                {verificationResult.message || `All ${verificationResult.total_events_checked} sequential records verified against SHA-256 cryptographic parent hashes.`}
              </p>
              {verificationResult.latest_hash && (
                <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 flex items-center gap-2 mt-1.5 bg-white/60 dark:bg-dark-900/60 p-2 rounded-lg border border-slate-200 dark:border-dark-700">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Chain Head Hash:</span>
                  <span className="text-indigo-600 dark:text-indigo-400 truncate">{verificationResult.latest_hash}</span>
                </div>
              )}
            </div>
          </div>

          <button
            onClick={() => setVerificationResult(null)}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-xs p-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* Filter Toolbar */}
      <GlassCard className="p-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Filter by Run ID (e.g. run_...)"
              value={runId}
              onChange={(e) => setRunId(e.target.value)}
              className="input pl-10 text-xs w-full"
            />
          </div>

          <div className="text-xs text-slate-500 dark:text-slate-400">
            Showing <strong className="text-slate-800 dark:text-slate-200">{logs.length}</strong> logged events
          </div>
        </div>
      </GlassCard>

      {/* Audit Log Timeline */}
      <GlassCard className="p-6">
        {loading ? (
          <div className="py-16 text-center">
            <Spinner size="lg" />
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Loading cryptographic audit trail...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center text-slate-500 dark:text-slate-400 text-xs">
            No audit records found matching criteria.
          </div>
        ) : (
          <div className="space-y-3">
            {logs.map((log, idx) => {
              const meta = EVENT_ICONS[log.event_type] || { Icon: Activity, color: 'text-slate-500 dark:text-slate-400', bg: 'bg-slate-500/10' }
              const Icon = meta.Icon
              return (
                <div
                  key={log.log_id || idx}
                  className="p-4 bg-slate-50/70 dark:bg-dark-900/60 border border-slate-200/80 dark:border-dark-700/80 hover:border-brand-400 dark:hover:border-dark-600 rounded-xl transition-all space-y-2.5"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start space-x-3.5">
                      <div className={`w-9 h-9 rounded-xl ${meta.bg} border border-slate-200 dark:border-dark-700 flex items-center justify-center shrink-0 mt-0.5`}>
                        <Icon className={`w-4 h-4 ${meta.color}`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-xs font-bold ${meta.color}`}>
                            {log.event_type?.replace(/_/g, ' ')}
                          </span>
                          <span className="text-slate-300 dark:text-slate-600 text-xs">•</span>
                          <span className="text-xs text-slate-600 dark:text-slate-400">
                            actor: <strong className="text-slate-900 dark:text-slate-200">{log.actor || 'system'}</strong>
                          </span>
                          {log.processing_run_id && (
                            <span className="text-[10px] font-mono text-indigo-600 dark:text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-1.5 py-0.5 rounded">
                              {log.processing_run_id}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-700 dark:text-slate-300 mt-1 leading-relaxed">{log.message}</p>
                      </div>
                    </div>

                    <span className="text-[11px] text-slate-500 dark:text-slate-400 whitespace-nowrap font-mono">
                      {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>

                  {/* Cryptographic SHA-256 Hash Chain Proof */}
                  {log.event_hash && (
                    <div className="pt-2 border-t border-slate-200 dark:border-dark-800 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                      <div className="flex items-center space-x-2 truncate max-w-xl">
                        <Lock className="w-3 h-3 text-slate-400 shrink-0" />
                        <span className="text-slate-400 dark:text-slate-500">SHA-256:</span>
                        <span className="text-slate-600 dark:text-slate-400 truncate">{log.event_hash}</span>
                      </div>

                      <button
                        onClick={() => copyToClipboard(log.event_hash, log.log_id || idx)}
                        className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300 inline-flex items-center gap-1 shrink-0 ml-2 font-sans text-xs font-semibold"
                      >
                        {copiedHash === (log.log_id || idx) ? (
                          <Check className="w-3.5 h-3.5 text-emerald-500" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                        <span>{copiedHash === (log.log_id || idx) ? 'Copied' : 'Copy Hash'}</span>
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </GlassCard>
    </PageContainer>
  )
}
