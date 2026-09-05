import React, { useState, useEffect } from 'react'
import {
  AlertTriangle, Brain, CheckCircle, XCircle, Eye, ChevronDown, ChevronUp,
  UserPlus, MessageSquare, DollarSign, ArrowRight, ShieldCheck, RefreshCw, Send,
  Filter, Check, User, Clock, FileText, CheckCircle2
} from 'lucide-react'
import {
  listExceptions, resolveException, rejectException, ignoreException,
  triggerInvestigation, assignException, addExceptionNote, recordAdjustment
} from '../api'
import {
  PageContainer, GlassCard, Button, StatusBadge,
  Alert, Spinner, EmptyState, Currency, Tabs
} from '../components/ui'
import { PageHero } from '../components/templates'

const SEVERITY_COLORS = {
  CRITICAL: 'bg-red-950/60 text-red-400 border-red-700/50 shadow-glow-sm',
  HIGH: 'bg-orange-950/60 text-orange-400 border-orange-700/50',
  MEDIUM: 'bg-amber-950/60 text-amber-400 border-amber-700/50',
  LOW: 'bg-fuchsia-950/40 text-fuchsia-300 border-fuchsia-700/40 shadow-glow-fuchsia-sm',
}

function ExceptionRow({ exc, onAction }) {
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [aiResult, setAiResult] = useState(exc.ai_finding ? exc : null)
  const [actionError, setActionError] = useState(null)
  const [actionSuccess, setActionSuccess] = useState(null)
  const [assignOpen, setAssignOpen] = useState(false)
  const [assigneeEmail, setAssigneeEmail] = useState('')
  const [adjustOpen, setAdjustOpen] = useState(false)
  const [adjustAmount, setAdjustAmount] = useState(exc.difference || 0)
  const [adjustType, setAdjustType] = useState('FEE_CORRECTION')
  const [adjustReason, setAdjustReason] = useState('')
  const [noteContent, setNoteContent] = useState('')
  const [notes, setNotes] = useState(exc.notes || [])

  const handleInvestigate = async () => {
    setLoading(true); setActionError(null)
    try { const result = await triggerInvestigation(exc.exception_id); setAiResult(result); setActionSuccess('AI investigation completed with cryptographic evidence.') } catch (e) { setActionError(e.message) } finally { setLoading(false) }
  }
  const handleAction = async (action) => {
    setLoading(true); setActionError(null)
    try {
      const payload = { resolution: action, actor: 'finance_officer' }
      if (action === 'RESOLVE') await resolveException(exc.exception_id, { ...payload, resolution: 'Manually resolved after finance review' })
      else if (action === 'REJECT') await rejectException(exc.exception_id, payload)
      else if (action === 'IGNORE') await ignoreException(exc.exception_id, payload)
      onAction()
    } catch (e) { setActionError(e.message) } finally { setLoading(false) }
  }
  const handleAssign = async (e) => {
    e.preventDefault(); if (!assigneeEmail) return; setLoading(true)
    try { await assignException(exc.exception_id, assigneeEmail); setAssignOpen(false); setActionSuccess(`Assigned to ${assigneeEmail}`); onAction() } catch (e) { setActionError(e.message) } finally { setLoading(false) }
  }
  const handleAddNote = async (e) => {
    e.preventDefault(); if (!noteContent.trim()) return; setLoading(true)
    try { const res = await addExceptionNote(exc.exception_id, noteContent); if (res.note) setNotes((prev) => [...prev, res.note]); setNoteContent('') } catch (e) { setActionError(e.message) } finally { setLoading(false) }
  }
  const handleRecordAdjustment = async (e) => {
    e.preventDefault(); setLoading(true)
    try { await recordAdjustment(exc.exception_id, { amount: parseFloat(adjustAmount), adjustment_type: adjustType, reason: adjustReason, actor: 'finance_controller' }); setAdjustOpen(false); setActionSuccess('Financial adjustment recorded in audit ledger.'); onAction() } catch (e) { setActionError(e.message) } finally { setLoading(false) }
  }

  return (
    <GlassCard className="p-5 space-y-4 hover:border-fuchsia-500/20 transition-colors" accent="fuchsia">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-xl bg-fuchsia-500/10 border border-fuchsia-500/30 flex items-center justify-center text-fuchsia-400 shrink-0 mt-0.5 animate-float" style={{ animationDuration: '6s' }}>
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono font-bold text-xs text-slate-100">{exc.exception_id}</span>
              <span className={`px-2 py-0.2 rounded-full text-[10px] font-bold border ${SEVERITY_COLORS[exc.severity] || SEVERITY_COLORS.MEDIUM}`}>{exc.severity || 'MEDIUM'}</span>
              <StatusBadge status={exc.status} />
            </div>
            <p className="text-xs text-slate-300 mt-1">{exc.description || exc.type?.replace(/_/g, ' ') || 'Reconciliation Discrepancy'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {exc.difference && <div className="text-right"><span className="text-[10px] text-slate-400 uppercase block">Variance</span><span className="text-sm font-bold font-mono text-fuchsia-300"><Currency amount={exc.difference} /></span></div>}
          <Button variant="ghost" size="sm" onClick={() => setExpanded(!expanded)} className="group">
            {expanded ? <ChevronUp className="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" /> : <ChevronDown className="w-4 h-4 group-hover:translate-y-0.5 transition-transform" />}
            <span>{expanded ? 'Collapse' : 'Details & HITL'}</span>
          </Button>
        </div>
      </div>

      {actionError && <Alert type="error" message={actionError} onDismiss={() => setActionError(null)} />}
      {actionSuccess && <Alert type="success" message={actionSuccess} onDismiss={() => setActionSuccess(null)} />}

      {expanded && (
        <div className="pt-4 border-t border-slate-800/80 space-y-4 animate-slide-up">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs stagger">
            {[
              { l: 'Transaction ID', v: exc.transaction_id || '—' },
              { l: 'Expected Amount', v: exc.expected_value ? <Currency amount={exc.expected_value} /> : '—' },
              { l: 'Actual Ingested', v: exc.actual_value ? <Currency amount={exc.actual_value} /> : '—' },
              { l: 'Assignee', v: <span className="text-fuchsia-400 font-semibold">{exc.assigned_to || 'Unassigned'}</span> },
            ].map(x => (
              <div key={x.l} className="p-3 bg-slate-900/50 border border-slate-800 rounded-xl hover:border-fuchsia-500/15 transition-colors"><span className="text-[10px] text-slate-400 uppercase block">{x.l}</span><span className="font-mono font-bold text-slate-200">{x.v}</span></div>
            ))}
          </div>

          <div className="p-4 rounded-xl bg-gradient-to-r from-fuchsia-950/30 via-slate-900/60 to-indigo-950/30 border border-fuchsia-700/30 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2"><Brain className="w-4 h-4 text-fuchsia-400" /><span className="text-xs font-bold text-fuchsia-300 uppercase tracking-wider">AI Investigation Diagnostic</span></div>
              {!aiResult && <Button variant="outline" size="sm" onClick={handleInvestigate} loading={loading} icon={Brain} className="border-fuchsia-500/40 text-fuchsia-300 hover:bg-fuchsia-500/10">Analyze with AI</Button>}
            </div>
            {aiResult ? (
              <div className="space-y-2 text-xs">
                <div className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-lg space-y-1"><span className="text-[10px] text-slate-400 uppercase font-semibold">Finding:</span><p className="text-slate-200 leading-relaxed font-mono text-[11px]">{aiResult.ai_finding || aiResult.finding || 'Ambiguous reference structure detected.'}</p></div>
                {aiResult.ai_recommendation && <div className="flex items-center gap-2"><span className="text-[10px] text-slate-400 uppercase font-semibold">Recommendation:</span><span className="font-bold text-emerald-400 font-mono">{aiResult.ai_recommendation}</span></div>}
              </div>
            ) : <p className="text-xs text-slate-400">Deterministic rule evaluation flagged discrepancy. Click 'Analyze with AI' to generate LLM reasoning.</p>}
          </div>

          <div className="space-y-2">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5"><MessageSquare className="w-3.5 h-3.5 text-fuchsia-400" />Audited Collaboration Thread</span>
            {notes.length > 0 ? (
              <div className="space-y-1.5 max-h-36 overflow-y-auto">
                {notes.map((n, i) => (
                  <div key={i} className="p-2.5 bg-slate-900/60 border border-slate-800 rounded-lg text-xs space-y-0.5"><div className="flex justify-between text-[10px] text-slate-400"><span className="font-semibold text-slate-300">{n.author || 'finance_officer'}</span><span className="font-mono">{new Date(n.created_at || Date.now()).toLocaleTimeString()}</span></div><p className="text-slate-200">{n.content}</p></div>
                ))}
              </div>
            ) : <p className="text-[11px] text-slate-500 italic">No notes posted yet.</p>}
            <form onSubmit={handleAddNote} className="flex gap-2 pt-1">
              <input type="text" value={noteContent} onChange={(e) => setNoteContent(e.target.value)} placeholder="Post a note or audit justification..." className="input py-1 text-xs flex-1" />
              <Button type="submit" variant="primary" size="sm" disabled={!noteContent.trim() || loading} icon={Send} className="from-fuchsia-600 to-purple-600">Post</Button>
            </form>
          </div>

          <div className="flex flex-wrap items-center justify-between pt-3 border-t border-slate-800/80 gap-3">
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={() => setAssignOpen(!assignOpen)} icon={UserPlus}>Assign</Button>
              <Button variant="secondary" size="sm" onClick={() => setAdjustOpen(!adjustOpen)} icon={DollarSign}>Adjustment</Button>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => handleAction('IGNORE')} disabled={loading}>Ignore</Button>
              <Button variant="danger" size="sm" onClick={() => handleAction('REJECT')} disabled={loading}>Reject Record</Button>
              <Button variant="success" size="sm" onClick={() => handleAction('RESOLVE')} disabled={loading} icon={CheckCircle2}>Approve & Resolve</Button>
            </div>
          </div>

          {assignOpen && (
            <form onSubmit={handleAssign} className="p-3 bg-slate-900 border border-slate-800 rounded-xl flex gap-2 items-center animate-slide-down">
              <input type="email" required value={assigneeEmail} onChange={(e) => setAssigneeEmail(e.target.value)} placeholder="analyst@finova.ai" className="input py-1 text-xs flex-1" />
              <Button type="submit" variant="primary" size="sm" loading={loading}>Confirm Assign</Button>
            </form>
          )}
          {adjustOpen && (
            <form onSubmit={handleRecordAdjustment} className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3 animate-slide-down">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider">Record Audited Financial Adjustment</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div><label className="text-[10px] text-slate-400 uppercase mb-1 block">Adjustment Type</label><select value={adjustType} onChange={(e) => setAdjustType(e.target.value)} className="select py-1 text-xs"><option value="FEE_CORRECTION">Fee Correction</option><option value="TAX_CORRECTION">Tax Correction</option><option value="WRITE_OFF">Write Off</option><option value="CURRENCY_CONVERSION">Currency Conversion</option></select></div>
                <div><label className="text-[10px] text-slate-400 uppercase mb-1 block">Adjustment Amount</label><input type="number" step="0.01" required value={adjustAmount} onChange={(e) => setAdjustAmount(e.target.value)} className="input py-1 text-xs font-mono" /></div>
              </div>
              <div><label className="text-[10px] text-slate-400 uppercase mb-1 block">Audit Justification</label><input type="text" required placeholder="e.g. Gateway fee deduction verified via settlement UTR" value={adjustReason} onChange={(e) => setAdjustReason(e.target.value)} className="input py-1 text-xs" /></div>
              <div className="flex justify-end gap-2"><Button variant="ghost" size="sm" onClick={() => setAdjustOpen(false)}>Cancel</Button><Button type="submit" variant="primary" size="sm" loading={loading}>Post Adjustment</Button></div>
            </form>
          )}
        </div>
      )}
    </GlassCard>
  )
}

export default function Exceptions() {
  const [exceptions, setExceptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')

  const fetch = async () => {
    setLoading(true)
    try { const data = await listExceptions({ status: statusFilter || undefined, severity: severityFilter || undefined, limit: 100 }); setExceptions(data.exceptions || []) } catch (err) { console.warn('Failed to fetch exceptions:', err.message) } finally { setLoading(false) }
  }

  useEffect(() => { fetch() }, [statusFilter, severityFilter])

  return (
    <PageContainer>
      <PageHero title="Exceptions Management & HITL Triage" subtitle="Review ledger discrepancies, collaborate on resolution threads, and approve financial adjustments with SHA-256 audit trails." icon={AlertTriangle} accent="fuchsia" actions={
        <div className="flex items-center gap-2">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="select py-1.5 px-3 text-xs w-36"><option value="">All Statuses</option><option value="OPEN">OPEN</option><option value="RESOLVED">RESOLVED</option><option value="REJECTED">REJECTED</option><option value="IGNORED">IGNORED</option></select>
          <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="select py-1.5 px-3 text-xs w-36"><option value="">All Severities</option><option value="CRITICAL">CRITICAL</option><option value="HIGH">HIGH</option><option value="MEDIUM">MEDIUM</option><option value="LOW">LOW</option></select>
          <Button variant="secondary" size="sm" onClick={fetch} icon={RefreshCw}>Refresh</Button>
        </div>
      } />

      <div className="space-y-4 stagger">
        {loading ? (
          <div className="glass-card py-20 flex flex-col items-center justify-center space-y-3"><Spinner size="lg" /><p className="text-xs text-slate-400">Loading exceptions queue…</p></div>
        ) : exceptions.length === 0 ? (
          <EmptyState icon={ShieldCheck} title="Zero Pending Exceptions" description="No reconciliation discrepancies match the selected filters." />
        ) : (
          exceptions.map((exc) => <ExceptionRow key={exc.exception_id} exc={exc} onAction={fetch} />)
        )}
      </div>
    </PageContainer>
  )
}
