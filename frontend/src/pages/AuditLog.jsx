import React, { useState, useEffect } from 'react'
import {
  FileText, Activity, Brain, CheckCircle, AlertTriangle, Zap,
  ShieldCheck, ShieldAlert, RefreshCw, Key, Copy, Check
} from 'lucide-react'
import { getAuditLogs, verifyAuditIntegrity } from '../api'

const EVENT_ICONS = {
  PROCESSING_STARTED: { Icon: Zap, color: 'text-indigo-400', bg: 'bg-indigo-950/80' },
  PROCESSING_COMPLETED: { Icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-950/80' },
  AI_INVESTIGATION_STARTED: { Icon: Brain, color: 'text-purple-400', bg: 'bg-purple-950/80' },
  AI_INVESTIGATION_COMPLETED: { Icon: Brain, color: 'text-purple-300', bg: 'bg-purple-950/80' },
  EXCEPTION_CREATED: { Icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-950/80' },
  EXCEPTION_RESOLVED: { Icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-950/80' },
  EXCEPTION_REJECTED: { Icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-950/80' },
  EXCEPTION_IGNORED: { Icon: Activity, color: 'text-slate-400', bg: 'bg-slate-800' },
  DATASET_GENERATED: { Icon: FileText, color: 'text-blue-400', bg: 'bg-blue-950/80' },
  DATASET_UPLOADED: { Icon: FileText, color: 'text-cyan-400', bg: 'bg-cyan-950/80' },
  INTEGRATION_SYNCED: { Icon: RefreshCw, color: 'text-indigo-400', bg: 'bg-indigo-950/80' },
  SETTINGS_CHANGED: { Icon: Activity, color: 'text-amber-300', bg: 'bg-amber-950/80' },
  MEMBER_INVITED: { Icon: Activity, color: 'text-teal-400', bg: 'bg-teal-950/80' },
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
    <div className="space-y-8 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-indigo-400" />
            Cryptographic Audit Trail
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Immutable, SHA-256 hash-chained ledger of every system reconciliation, decision, and manual adjustment.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <input
            type="text"
            placeholder="Filter by Run ID…"
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none w-48"
          />

          <button
            onClick={handleVerifyIntegrity}
            disabled={verifying}
            className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-700/25 flex items-center space-x-2 transition-all"
          >
            <ShieldCheck className={`w-4 h-4 ${verifying ? 'animate-spin' : ''}`} />
            <span>{verifying ? 'Verifying Hashes...' : 'Verify Cryptographic Chain'}</span>
          </button>
        </div>
      </div>

      {/* Verification Shield Banner */}
      {verificationResult && (
        <div className={`p-4 rounded-2xl border flex items-start justify-between ${
          verificationResult.verified
            ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
            : 'bg-red-950/40 border-red-800/60 text-red-300'
        }`}>
          <div className="flex items-start space-x-3">
            {verificationResult.verified ? (
              <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <ShieldAlert className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
            )}
            <div className="space-y-1">
              <div className="text-sm font-bold">
                {verificationResult.verified
                  ? 'Audit Chain Verified & Tamper-Evident'
                  : 'Audit Chain Verification Failed'}
              </div>
              <p className="text-xs text-slate-300">
                {verificationResult.message || `All ${verificationResult.total_events_checked} sequential records match cryptographic hash parent chains.`}
              </p>
              {verificationResult.latest_hash && (
                <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5 mt-1">
                  <span>Head Hash:</span>
                  <span className="text-indigo-300">{verificationResult.latest_hash}</span>
                </div>
              )}
            </div>
          </div>

          <button onClick={() => setVerificationResult(null)} className="text-slate-400 hover:text-white text-xs">
            ✕
          </button>
        </div>
      )}

      {/* Timeline List */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        {loading ? (
          <div className="py-12 text-center text-slate-500 text-xs">
            Loading cryptographic audit logs...
          </div>
        ) : logs.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs">
            No audit records found matching criteria.
          </div>
        ) : (
          <div className="space-y-3">
            {logs.map((log, idx) => {
              const meta = EVENT_ICONS[log.event_type] || { Icon: Activity, color: 'text-slate-400', bg: 'bg-slate-800' }
              const Icon = meta.Icon
              return (
                <div
                  key={log.log_id || idx}
                  className="p-4 bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 rounded-xl transition-all space-y-2"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start space-x-3">
                      <div className={`w-8 h-8 rounded-xl ${meta.bg} border border-slate-800 flex items-center justify-center shrink-0 mt-0.5`}>
                        <Icon className={`w-4 h-4 ${meta.color}`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-xs font-bold ${meta.color}`}>
                            {log.event_type?.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[11px] text-slate-500">•</span>
                          <span className="text-xs text-slate-400">by <strong className="text-slate-200">{log.actor || 'system'}</strong></span>
                          {log.processing_run_id && (
                            <span className="text-[10px] font-mono text-indigo-400 bg-indigo-950/60 border border-indigo-800/40 px-1.5 py-0.5 rounded">
                              {log.processing_run_id}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-300 mt-1">{log.message}</p>
                      </div>
                    </div>

                    <span className="text-[11px] text-slate-500 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>

                  {/* Cryptographic SHA-256 Hash Chain Proof */}
                  {log.event_hash && (
                    <div className="pt-2 border-t border-slate-900 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <div className="flex items-center space-x-2 truncate max-w-lg">
                        <span className="text-slate-600">SHA-256:</span>
                        <span className="text-slate-400 truncate">{log.event_hash}</span>
                      </div>

                      <button
                        onClick={() => copyToClipboard(log.event_hash, log.log_id || idx)}
                        className="text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1 shrink-0 ml-2"
                      >
                        {copiedHash === (log.log_id || idx) ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3" />
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
      </div>
    </div>
  )
}
