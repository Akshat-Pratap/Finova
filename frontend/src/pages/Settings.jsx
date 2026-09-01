import React, { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import {
  Settings as SettingsIcon, Sliders, Shield, Users, UserPlus,
  CheckCircle2, Save, AlertCircle, Building, DollarSign
} from 'lucide-react'
import { updateOrgSettings, listOrgMembers, inviteOrgMember } from '../api'

const CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'SGD', 'AED', 'AUD', 'CAD']

export default function Settings() {
  const { activeOrg, role } = useAuth()
  const [baseCurrency, setBaseCurrency] = useState('INR')
  const [autoThreshold, setAutoThreshold] = useState(0.90)
  const [aiThreshold, setAiThreshold] = useState(0.70)
  const [amountTolerance, setAmountTolerance] = useState(0.05)
  const [dateTolerance, setDateTolerance] = useState(3)
  const [members, setMembers] = useState([])
  const [saving, setSaving] = useState(false)
  const [notification, setNotification] = useState(null)

  // Invite modal state
  const [inviteModalOpen, setInviteModalOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('FINANCE_ANALYST')
  const [inviting, setInviting] = useState(false)

  useEffect(() => {
    if (activeOrg) {
      setBaseCurrency(activeOrg.base_currency || 'INR')
      if (activeOrg.settings) {
        setAutoThreshold(activeOrg.settings.auto_reconcile_threshold ?? 0.90)
        setAiThreshold(activeOrg.settings.ai_review_threshold ?? 0.70)
        setAmountTolerance(activeOrg.settings.amount_tolerance ?? 0.05)
        setDateTolerance(activeOrg.settings.date_tolerance_days ?? 3)
      }
      fetchMembers()
    }
  }, [activeOrg])

  const fetchMembers = async () => {
    if (!activeOrg?.organization_id) return
    try {
      const res = await listOrgMembers(activeOrg.organization_id)
      if (res.success) {
        setMembers(res.members || [])
      }
    } catch (err) {
      console.warn('Failed to load members:', err.message)
    }
  }

  const handleSaveSettings = async (e) => {
    e.preventDefault()
    if (!activeOrg?.organization_id) return
    setSaving(true)
    setNotification(null)
    try {
      const res = await updateOrgSettings(activeOrg.organization_id, {
        base_currency: baseCurrency,
        auto_reconcile_threshold: parseFloat(autoThreshold),
        ai_review_threshold: parseFloat(aiThreshold),
        amount_tolerance: parseFloat(amountTolerance),
        date_tolerance_days: parseInt(dateTolerance),
      })
      if (res.success) {
        setNotification({ type: 'success', message: 'Organization reconciliation rules updated successfully.' })
      }
    } catch (err) {
      setNotification({ type: 'error', message: err.message || 'Failed to update settings.' })
    } finally {
      setSaving(false)
    }
  }

  const handleInviteMember = async (e) => {
    e.preventDefault()
    if (!activeOrg?.organization_id) return
    setInviting(true)
    try {
      const res = await inviteOrgMember(activeOrg.organization_id, {
        email: inviteEmail,
        role: inviteRole,
      })
      if (res.success) {
        setNotification({ type: 'success', message: `Invited ${inviteEmail} as ${inviteRole}.` })
        setInviteModalOpen(false)
        setInviteEmail('')
        fetchMembers()
      }
    } catch (err) {
      setNotification({ type: 'error', message: err.message || 'Invitation failed.' })
    } finally {
      setInviting(false)
    }
  }

  return (
    <div className="space-y-8 font-sans max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <SettingsIcon className="w-6 h-6 text-indigo-400" />
          Organization Settings & Finance Controls
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Configure multi-tenant reconciliation tolerances, base reporting currencies, and role-based access control.
        </p>
      </div>

      {notification && (
        <div className={`p-4 rounded-xl text-xs flex items-center justify-between border ${
          notification.type === 'success'
            ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
            : 'bg-red-950/40 border-red-800/60 text-red-300'
        }`}>
          <span>{notification.message}</span>
          <button onClick={() => setNotification(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Organization Info & Rules Form */}
      <form onSubmit={handleSaveSettings} className="space-y-6">
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-indigo-400" />
            Financial Rules & Tolerances
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Primary Base Currency
              </label>
              <select
                value={baseCurrency}
                onChange={(e) => setBaseCurrency(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Amount Tolerance (Base Unit)
              </label>
              <input
                type="number"
                step="0.01"
                value={amountTolerance}
                onChange={(e) => setAmountTolerance(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Auto-Reconciliation Confidence Threshold ({(autoThreshold * 100).toFixed(0)}%)
              </label>
              <input
                type="range"
                min="0.70"
                max="0.99"
                step="0.01"
                value={autoThreshold}
                onChange={(e) => setAutoThreshold(e.target.value)}
                className="w-full accent-indigo-500"
              />
              <div className="flex justify-between text-[11px] text-slate-500 mt-1">
                <span>70% (Aggressive)</span>
                <span>90% (Standard)</span>
                <span>99% (Strict)</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Date Tolerance (±{dateTolerance} Days)
              </label>
              <input
                type="number"
                min="0"
                max="30"
                value={dateTolerance}
                onChange={(e) => setDateTolerance(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/30 transition-all flex items-center space-x-2"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? 'Saving...' : 'Save Configuration'}</span>
            </button>
          </div>
        </div>
      </form>

      {/* Team & RBAC Members */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-400" />
              Organization Team & Access Roles
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Manage finance managers, analysts, and auditors with tenant boundaries.</p>
          </div>

          <button
            onClick={() => setInviteModalOpen(true)}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-xl border border-slate-700 transition-colors flex items-center space-x-1.5"
          >
            <UserPlus className="w-3.5 h-3.5 text-indigo-400" />
            <span>Invite Team Member</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-[11px] text-slate-400 uppercase bg-slate-950/60 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Member</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Joined Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {members.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-slate-500">
                    No other team members found in this workspace.
                  </td>
                </tr>
              ) : (
                members.map((m, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-white">{m.full_name || m.email}</div>
                      <div className="text-[11px] text-slate-500">{m.email}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                        {m.role}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-emerald-400 font-medium">Active</td>
                    <td className="py-3 px-4 text-slate-400">
                      {m.joined_at ? new Date(m.joined_at).toLocaleDateString() : 'Active'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invite Modal */}
      {inviteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-indigo-400" />
                Invite Team Member
              </h3>
              <button onClick={() => setInviteModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleInviteMember} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Member Email
                </label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-600 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  placeholder="analyst@finova.ai"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  RBAC Role
                </label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  <option value="ADMIN">ADMIN (Full organization control)</option>
                  <option value="FINANCE_MANAGER">FINANCE_MANAGER (Approve exceptions & adjustments)</option>
                  <option value="FINANCE_ANALYST">FINANCE_ANALYST (Reconciliation & review)</option>
                  <option value="VIEWER">VIEWER (Read-only reports)</option>
                </select>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setInviteModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviting}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-md shadow-indigo-600/30"
                >
                  {inviting ? 'Sending Invite...' : 'Send Invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
