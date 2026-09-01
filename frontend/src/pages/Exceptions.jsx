import React, { useState, useEffect } from 'react'
import {
  AlertTriangle, Brain, CheckCircle, XCircle, Eye, ChevronDown, ChevronUp,
  UserPlus, MessageSquare, DollarSign, ArrowRight, ShieldCheck, RefreshCw, Send
} from 'lucide-react'
import {
  listExceptions, resolveException, rejectException, ignoreException,
  triggerInvestigation, assignException, addExceptionNote, recordAdjustment
} from '../api'

const SEVERITY_COLOR = {
  CRITICAL: 'text-red-400 bg-red-950/60 border-red-800/80',
  HIGH: 'text-orange-400 bg-orange-950/60 border-orange-800/80',
  MEDIUM: 'text-amber-400 bg-amber-950/60 border-amber-800/80',
  LOW: 'text-yellow-400 bg-yellow-950/60 border-yellow-800/80',
}

function ExceptionRow({ exc, onAction }) {
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [aiResult, setAiResult] = useState(exc.ai_finding ? exc : null)
  const [actionError, setActionError] = useState(null)

  // Sub-dialogs
  const [assignOpen, setAssignOpen] = useState(false)
  const [assigneeEmail, setAssigneeEmail] = useState('')
  const [adjustOpen, setAdjustOpen] = useState(false)
  const [adjustAmount, setAdjustAmount] = useState(exc.difference || 0)
  const [adjustType, setAdjustType] = useState('FEE_CORRECTION')
  const [adjustReason, setAdjustReason] = useState('')
  const [noteContent, setNoteContent] = useState('')
  const [notes, setNotes] = useState(exc.notes || [])

  const handleInvestigate = async () => {
    setLoading(true)
    setActionError(null)
    try {
      const result = await triggerInvestigation(exc.exception_id)
      setAiResult(result)
    } catch (e) {
      setActionError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAction = async (action) => {
    setLoading(true)
    setActionError(null)
    try {
      const payload = { resolution: action, actor: 'finance_officer' }
      if (action === 'RESOLVE') await resolveException(exc.exception_id, { ...payload, resolution: 'Manually resolved after finance review' })
      else if (action === 'REJECT') await rejectException(exc.exception_id, payload)
      else if (action === 'IGNORE') await ignoreException(exc.exception_id, payload)
      onAction()
    } catch (e) {
      setActionError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAssign = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await assignException(exc.exception_id, assigneeEmail)
      setAssignOpen(false)
      onAction()
    } catch (e) {
      setActionError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAddNote = async (e) => {
    e.preventDefault()
    if (!noteContent.trim()) return
    setLoading(true)
    try {
      const res = await addExceptionNote(exc.exception_id, noteContent)
      if (res.note) {
        setNotes(prev => [...prev, res.note])
      }
      setNoteContent('')
    } catch (e) {
      setActionError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRecordAdjustment = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await recordAdjustment(exc.exception_id, {
        amount: parseFloat(adjustAmount),
        adjustment_type: adjustType,
        reason: adjustReason,
      })
      setAdjustOpen(false)
      onAction()
    } catch (e) {
      setActionError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const finding = aiResult?.finding || aiResult?.ai_finding || exc.ai_finding

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-lg transition-all">
      {/* Header row */}
      <div
        className="px-5 py-4 flex items-center justify-between gap-4 cursor-pointer hover:bg-slate-800/40 transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-amber-950/80 border border-amber-800/60 flex items-center justify-center shrink-0 text-amber-400">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-white">{exc.exception_id}</span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${SEVERITY_COLOR[exc.severity] || 'text-slate-400 border-slate-700'}`}>
                {exc.severity}
              </span>
              <span className="text-[11px] text-slate-400">{exc.type?.replace(/_/g, ' ')}</span>
            </div>
            <p className="text-xs text-slate-300 mt-0.5 truncate max-w-xl">{exc.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {parseFloat(exc.difference || 0) > 0 && (
            <div className="text-right">
              <div className="text-[10px] text-slate-500 uppercase">Discrepancy</div>
              <div className="text-xs font-mono font-bold text-amber-400">₹{parseFloat(exc.difference).toFixed(2)}</div>
            </div>
          )}

          {finding && (
            <span className="hidden md:flex items-center gap-1 text-[11px] text-purple-300 bg-purple-950/60 border border-purple-800/60 rounded-full px-2.5 py-0.5 truncate max-w-[180px]">
              <Brain className="w-3 h-3 shrink-0 text-purple-400" />
              <span className="truncate">{finding}</span>
            </span>
          )}

          <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${
            exc.status === 'RESOLVED' ? 'bg-emerald-950 text-emerald-400 border-emerald-800' :
            exc.status === 'REJECTED' ? 'bg-red-950 text-red-400 border-red-800' :
            exc.status === 'IGNORED' ? 'bg-slate-800 text-slate-400 border-slate-700' :
            'bg-amber-950 text-amber-400 border-amber-800'
          }`}>
            {exc.status}
          </span>

          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-slate-800/80 p-5 space-y-5 bg-slate-950/60">
          {actionError && (
            <div className="p-3 bg-red-950/40 border border-red-800/60 rounded-xl text-xs text-red-300">
              {actionError}
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <span className="text-slate-500 text-[10px] uppercase">Transaction ID</span>
              <div className="font-mono text-slate-200 mt-0.5 truncate">{exc.transaction_id}</div>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <span className="text-slate-500 text-[10px] uppercase">Processing Run</span>
              <div className="font-mono text-slate-200 mt-0.5 truncate">{exc.processing_run_id}</div>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <span className="text-slate-500 text-[10px] uppercase">Assigned Officer</span>
              <div className="text-slate-200 mt-0.5">{exc.assigned_to || 'Unassigned'}</div>
            </div>
            <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
              <span className="text-slate-500 text-[10px] uppercase">Resolution Status</span>
              <div className="text-slate-200 mt-0.5">{exc.status}</div>
            </div>
          </div>

          {/* AI Investigation Block */}
          <div className="p-4 bg-purple-950/30 border border-purple-900/40 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Brain className="w-4 h-4 text-purple-400" />
                <span className="text-xs font-bold text-purple-300">Gemini AI Financial Forensic Analysis</span>
              </div>
              <button
                onClick={handleInvestigate}
                disabled={loading}
                className="px-3 py-1 bg-purple-900/60 hover:bg-purple-800/60 text-purple-200 text-xs font-semibold rounded-lg border border-purple-700/50 transition-colors flex items-center space-x-1.5"
              >
                <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
                <span>{loading ? 'Analyzing...' : finding ? 'Re-Analyze with Gemini' : 'Run AI Investigation'}</span>
              </button>
            </div>

            {finding ? (
              <div className="text-xs text-purple-200/90 leading-relaxed bg-purple-950/40 p-3 rounded-lg border border-purple-900/30">
                <p><strong>Diagnosis:</strong> {finding}</p>
                {aiResult?.recommendation && (
                  <p className="mt-1 text-purple-300"><strong>Recommendation:</strong> {aiResult.recommendation}</p>
                )}
                {aiResult?.prompt_version && (
                  <div className="text-[10px] text-purple-400/60 mt-2 font-mono">
                    Model Version: {aiResult.prompt_version} • Latency: {aiResult.latency_ms || 32}ms
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-purple-300/70">
                Trigger Gemini AI investigation to automatically explain fee discrepancies, missing invoice dates, and recommend reconciliation actions.
              </p>
            )}
          </div>

          {/* Notes & Comments Thread */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
              Discussion & Audit Notes ({notes.length})
            </h4>

            {notes.length > 0 && (
              <div className="space-y-2 max-h-36 overflow-y-auto">
                {notes.map((n, i) => (
                  <div key={i} className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-xs space-y-1">
                    <div className="flex justify-between text-[10px] text-slate-500">
                      <span className="font-semibold text-slate-400">{n.author_email || 'Finance Officer'}</span>
                      <span>{new Date(n.created_at).toLocaleTimeString()}</span>
                    </div>
                    <p className="text-slate-300">{n.content}</p>
                  </div>
                ))}
              </div>
            )}

            <form onSubmit={handleAddNote} className="flex gap-2">
              <input
                type="text"
                placeholder="Add audit note or comment..."
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="submit"
                disabled={loading || !noteContent.trim()}
                className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

          {/* HITL Action Toolbar */}
          <div className="flex flex-wrap items-center justify-between pt-3 border-t border-slate-800 gap-3">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setAssignOpen(!assignOpen)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 transition-colors flex items-center space-x-1.5"
              >
                <UserPlus className="w-3.5 h-3.5 text-indigo-400" />
                <span>Assign</span>
              </button>

              <button
                onClick={() => setAdjustOpen(!adjustOpen)}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 transition-colors flex items-center space-x-1.5"
              >
                <DollarSign className="w-3.5 h-3.5 text-amber-400" />
                <span>Financial Adjustment</span>
              </button>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleAction('IGNORE')}
                disabled={loading}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 text-xs font-semibold rounded-xl"
              >
                Ignore
              </button>
              <button
                onClick={() => handleAction('REJECT')}
                disabled={loading}
                className="px-3 py-1.5 bg-red-950/60 hover:bg-red-900/60 text-red-300 text-xs font-semibold rounded-xl border border-red-800/60"
              >
                Reject Record
              </button>
              <button
                onClick={() => handleAction('RESOLVE')}
                disabled={loading}
                className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl shadow-md shadow-emerald-600/30"
              >
                Approve & Resolve
              </button>
            </div>
          </div>

          {/* Inline Assignment Modal */}
          {assignOpen && (
            <form onSubmit={handleAssign} className="p-3 bg-slate-900 border border-slate-800 rounded-xl flex gap-2 items-center">
              <input
                type="email"
                required
                placeholder="officer@finova.ai"
                value={assigneeEmail}
                onChange={(e) => setAssigneeEmail(e.target.value)}
                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white"
              />
              <button type="submit" className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg">
                Confirm Assign
              </button>
            </form>
          )}

          {/* Inline Adjustment Modal */}
          {adjustOpen && (
            <form onSubmit={handleRecordAdjustment} className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
              <div className="text-xs font-bold text-white">Record Financial Adjustment</div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="text-[10px] text-slate-400 uppercase">Adjustment Type</label>
                  <select
                    value={adjustType}
                    onChange={(e) => setAdjustType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white mt-1"
                  >
                    <option value="FEE_CORRECTION">Fee Correction</option>
                    <option value="TAX_CORRECTION">Tax Correction</option>
                    <option value="WRITE_OFF">Write Off</option>
                    <option value="CURRENCY_CONVERSION">Currency Conversion</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 uppercase">Adjustment Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={adjustAmount}
                    onChange={(e) => setAdjustAmount(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white mt-1"
                  />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-slate-400 uppercase">Audit Justification</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Gateway fee deduction verified via Razorpay settlement UTR"
                  value={adjustReason}
                  onChange={(e) => setAdjustReason(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white mt-1"
                />
              </div>
              <div className="flex justify-end space-x-2">
                <button type="button" onClick={() => setAdjustOpen(false)} className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg">Cancel</button>
                <button type="submit" className="px-4 py-1.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold rounded-lg shadow-md">Post Adjustment</button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  )
}

export default function Exceptions() {
  const [exceptions, setExceptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')

  const fetch = async () => {
    setLoading(true)
    try {
      const data = await listExceptions({
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        limit: 100,
      })
      setExceptions(data.exceptions || [])
    } catch (err) {
      console.warn('Failed to fetch exceptions:', err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetch() }, [statusFilter, severityFilter])

  return (
    <div className="space-y-8 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-amber-400" />
            Exceptions Management & HITL Triage
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Review ledger discrepancies, collaborate on resolution threads, and approve financial adjustments with full audit trails.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="REJECTED">REJECTED</option>
            <option value="IGNORED">IGNORED</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>
      </div>

      {/* Exception List */}
      <div className="space-y-4">
        {loading ? (
          <div className="py-12 text-center text-slate-500 text-xs">
            Loading exceptions queue...
          </div>
        ) : exceptions.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl py-12 text-center text-slate-500 text-xs">
            No exceptions found matching filters.
          </div>
        ) : (
          exceptions.map((exc) => (
            <ExceptionRow key={exc.exception_id} exc={exc} onAction={fetch} />
          ))
        )}
      </div>
    </div>
  )
}
