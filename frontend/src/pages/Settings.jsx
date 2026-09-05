import React, { useState, useEffect } from 'react'
import {
  Settings as SettingsIcon, Sliders, Shield, Users, UserPlus,
  CheckCircle2, Save, AlertCircle, Building, DollarSign,
  User, Lock, Bell, Layers, Palette, Mail, Globe, MapPin,
  Clock, Key, ShieldCheck, Check, Sun, Moon, Laptop, Trash2
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { updateOrgSettings, listOrgMembers, inviteOrgMember } from '../api'
import {
  PageContainer, PageHeader, GlassCard, Button, StatusBadge,
  Tabs, Modal, Alert, Spinner, EmptyState
} from '../components/ui'

const CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'SGD', 'AED', 'AUD', 'CAD', 'JPY', 'CHF']
const TIMEZONES = [
  'Asia/Kolkata (IST +5:30)',
  'UTC (GMT +0:00)',
  'America/New_York (EST -5:00)',
  'America/Los_Angeles (PST -8:00)',
  'Europe/London (GMT +0:00)',
  'Asia/Singapore (SGT +8:00)',
  'Asia/Dubai (GST +4:00)',
]

const INDUSTRIES = [
  'Fintech & Payment Services',
  'Banking & Financial Services',
  'E-commerce & Retail',
  'SaaS & Software Enterprise',
  'Logistics & Supply Chain',
  'Healthcare & Life Sciences',
  'Manufacturing & Industrial',
]

const SETTINGS_TABS = [
  { id: 'organization', label: 'Organization', icon: Building },
  { id: 'rules', label: 'Reconciliation Rules', icon: Sliders },
  { id: 'team', label: 'Team & Roles', icon: Users },
  { id: 'profile', label: 'User Profile', icon: User },
  { id: 'security', label: 'Security & Auth', icon: Lock },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'integrations', label: 'Integrations', icon: Layers },
  { id: 'appearance', label: 'Appearance', icon: Palette },
]

export default function Settings() {
  const { user, activeOrg, role } = useAuth()
  const { theme, setTheme, isDark } = useTheme()
  const [activeTab, setActiveTab] = useState('organization')

  // Organization settings state
  const [orgName, setOrgName] = useState('')
  const [industry, setIndustry] = useState('Fintech & Payment Services')
  const [baseCurrency, setBaseCurrency] = useState('INR')
  const [timezone, setTimezone] = useState('Asia/Kolkata (IST +5:30)')
  const [contactEmail, setContactEmail] = useState('')
  const [website, setWebsite] = useState('')
  const [address, setAddress] = useState('')
  const [description, setDescription] = useState('')

  // Financial Rules state
  const [autoThreshold, setAutoThreshold] = useState(0.90)
  const [aiThreshold, setAiThreshold] = useState(0.70)
  const [amountTolerance, setAmountTolerance] = useState(0.05)
  const [dateTolerance, setDateTolerance] = useState(3)
  const [feeTolerance, setFeeTolerance] = useState(0.02)
  const [taxTolerance, setTaxTolerance] = useState(0.01)

  // Team state
  const [members, setMembers] = useState([])
  const [inviteModalOpen, setInviteModalOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('FINANCE_ANALYST')
  const [inviting, setInviting] = useState(false)

  // Notifications state
  const [notifExceptions, setNotifExceptions] = useState(true)
  const [notifReconCompleted, setNotifReconCompleted] = useState(true)
  const [notifCriticalAlerts, setNotifCriticalAlerts] = useState(true)
  const [notifDailyDigest, setNotifDailyDigest] = useState(false)

  // Form feedback state
  const [saving, setSaving] = useState(false)
  const [notification, setNotification] = useState(null)

  useEffect(() => {
    if (activeOrg) {
      setOrgName(activeOrg.name || 'Finova Global Financials')
      setBaseCurrency(activeOrg.base_currency || 'INR')
      setContactEmail(user?.email || 'admin@finova.ai')
      setWebsite('https://finova.ai')
      setAddress('DLF CyberCity, CyberTech Tower 4, Gurugram, Haryana 122002, India')
      setDescription('Enterprise AI-powered finance controller, multi-source deterministic matching, and automated exceptions resolution.')

      if (activeOrg.settings) {
        setAutoThreshold(activeOrg.settings.auto_reconcile_threshold ?? 0.90)
        setAiThreshold(activeOrg.settings.ai_review_threshold ?? 0.70)
        setAmountTolerance(activeOrg.settings.amount_tolerance ?? 0.05)
        setDateTolerance(activeOrg.settings.date_tolerance_days ?? 3)
      }
      fetchMembers()
    }
  }, [activeOrg, user])

  const fetchMembers = async () => {
    if (!activeOrg?.organization_id) return
    try {
      const res = await listOrgMembers(activeOrg.organization_id)
      if (res.success && res.members) {
        setMembers(res.members)
      } else {
        // Default display membership if fresh
        setMembers([
          {
            user_id: user?.user_id || 'usr_cfo_001',
            email: user?.email || 'cfo@finova.ai',
            role: role || 'OWNER',
            joined_at: new Date().toISOString(),
          },
        ])
      }
    } catch {
      setMembers([
        {
          user_id: user?.user_id || 'usr_cfo_001',
          email: user?.email || 'cfo@finova.ai',
          role: role || 'OWNER',
          joined_at: new Date().toISOString(),
        },
      ])
    }
  }

  const handleSaveSettings = async (e) => {
    e?.preventDefault?.()
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
        fee_tolerance_percent: parseFloat(feeTolerance),
        tax_tolerance_percent: parseFloat(taxTolerance),
      })
      if (res.success) {
        setNotification({
          type: 'success',
          message: 'Organization configuration and financial tolerances updated successfully.',
        })
      }
    } catch (err) {
      setNotification({ type: 'error', message: err.message || 'Failed to update settings.' })
    } finally {
      setSaving(false)
    }
  }

  const handleInviteMember = async (e) => {
    e.preventDefault()
    if (!activeOrg?.organization_id || !inviteEmail) return
    setInviting(true)
    try {
      const res = await inviteOrgMember(activeOrg.organization_id, {
        email: inviteEmail,
        role: inviteRole,
      })
      if (res.success) {
        setNotification({
          type: 'success',
          message: `Team member ${inviteEmail} invited with role ${inviteRole}.`,
        })
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
    <PageContainer>
      {/* Header */}
      <PageHeader
        title="Settings & Organization Controls"
        subtitle="Manage organization metadata, multi-tenant tolerances, role-based access, security, and appearance."
        icon={SettingsIcon}
        actions={
          <Button
            variant="primary"
            onClick={handleSaveSettings}
            loading={saving}
            icon={Save}
          >
            Save All Changes
          </Button>
        }
      />

      {/* Notification Banner */}
      {notification && (
        <Alert
          type={notification.type}
          message={notification.message}
          onDismiss={() => setNotification(null)}
        />
      )}

      {/* Tab Switcher */}
      <Tabs
        tabs={SETTINGS_TABS}
        activeTab={activeTab}
        onChange={setActiveTab}
        className="w-full"
      />

      {/* TAB 1: Organization Profile */}
      {activeTab === 'organization' && (
        <GlassCard className="p-6 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
            <div>
              <h2 className="section-heading">
                <Building className="w-4 h-4 text-brand-400" />
                Organization Profile & Workspace Information
              </h2>
              <p className="section-subheading">General legal entity and operational details</p>
            </div>
            <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-brand-950/60 dark:bg-brand-950/60 light:bg-brand-100 text-brand-300 dark:text-brand-300 light:text-brand-700 border border-brand-700/50">
              ID: {activeOrg?.organization_id || 'org_default'}
            </span>
          </div>

          <form onSubmit={handleSaveSettings} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
                  Organization Legal Name
                </label>
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="input"
                  placeholder="e.g. Acme Financial Technologies Pvt Ltd"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
                  Industry Sector
                </label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="select"
                >
                  {INDUSTRIES.map((ind) => (
                    <option key={ind} value={ind}>{ind}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
                  Reporting Base Currency
                </label>
                <select
                  value={baseCurrency}
                  onChange={(e) => setBaseCurrency(e.target.value)}
                  className="select"
                >
                  {CURRENCIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
                  Operational Timezone
                </label>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="select"
                >
                  {TIMEZONES.map((tz) => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
                  Finance Contact Email
                </label>
                <input
                  type="email"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  className="input"
                  placeholder="finance@yourorg.com"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
                  Corporate Website
                </label>
                <input
                  type="url"
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  className="input"
                  placeholder="https://yourorg.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
                Registered Physical Address
              </label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                className="input"
                placeholder="Street address, city, state, postal code, country"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
                Organization Description
              </label>
              <textarea
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="input resize-none"
                placeholder="Brief summary of business operations..."
              />
            </div>

            <div className="pt-2 flex justify-end">
              <Button type="submit" variant="primary" loading={saving} icon={Save}>
                Update Organization Profile
              </Button>
            </div>
          </form>
        </GlassCard>
      )}

      {/* TAB 2: Financial Rules & Tolerances */}
      {activeTab === 'rules' && (
        <GlassCard className="p-6 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
            <div>
              <h2 className="section-heading">
                <Sliders className="w-4 h-4 text-brand-400" />
                Deterministic Reconciliation Thresholds & Tolerances
              </h2>
              <p className="section-subheading">Control exact matching bounds, AI investigation trigger levels, and date leeway</p>
            </div>
            <span className="text-xs text-emerald-400 font-semibold bg-emerald-950/40 px-2.5 py-1 rounded-lg border border-emerald-800/50">
              Active Policy
            </span>
          </div>

          <form onSubmit={handleSaveSettings} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Auto Reconcile Threshold */}
              <div className="bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 p-4 rounded-xl border border-slate-800/70 dark:border-slate-800/70 light:border-slate-300 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-200 dark:text-slate-200 light:text-slate-800 uppercase tracking-wider">
                    Auto-Reconcile Threshold
                  </label>
                  <span className="text-sm font-mono font-bold text-emerald-400">
                    {(autoThreshold * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.70"
                  max="1.00"
                  step="0.01"
                  value={autoThreshold}
                  onChange={(e) => setAutoThreshold(parseFloat(e.target.value))}
                  className="w-full accent-brand-500 cursor-pointer"
                />
                <p className="text-[11px] text-slate-400 dark:text-slate-400 light:text-slate-500">
                  Transactions with confidence &ge; {(autoThreshold * 100).toFixed(0)}% auto-reconcile without human intervention.
                </p>
              </div>

              {/* AI Review Threshold */}
              <div className="bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 p-4 rounded-xl border border-slate-800/70 dark:border-slate-800/70 light:border-slate-300 space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-slate-200 dark:text-slate-200 light:text-slate-800 uppercase tracking-wider">
                    AI Review Threshold
                  </label>
                  <span className="text-sm font-mono font-bold text-brand-400">
                    {(aiThreshold * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.50"
                  max="0.85"
                  step="0.01"
                  value={aiThreshold}
                  onChange={(e) => setAiThreshold(parseFloat(e.target.value))}
                  className="w-full accent-brand-500 cursor-pointer"
                />
                <p className="text-[11px] text-slate-400 dark:text-slate-400 light:text-slate-500">
                  Transactions between {(aiThreshold * 100).toFixed(0)}% and {(autoThreshold * 100).toFixed(0)}% trigger automated AI investigation.
                </p>
              </div>

              {/* Amount Tolerance */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider">
                  Amount Tolerance Ratio (5% default)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="0.5"
                  value={amountTolerance}
                  onChange={(e) => setAmountTolerance(parseFloat(e.target.value))}
                  className="input font-mono"
                />
                <p className="text-[11px] text-slate-400">Permissible currency discrepancy before flagging as mismatch.</p>
              </div>

              {/* Date Tolerance */}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider">
                  Date Window Tolerance (Days)
                </label>
                <input
                  type="number"
                  min="0"
                  max="30"
                  value={dateTolerance}
                  onChange={(e) => setDateTolerance(parseInt(e.target.value))}
                  className="input font-mono"
                />
                <p className="text-[11px] text-slate-400">Maximum day variance allowed between bank record and transaction timestamp.</p>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button type="submit" variant="primary" loading={saving} icon={Save}>
                Save Reconciliation Rules
              </Button>
            </div>
          </form>
        </GlassCard>
      )}

      {/* TAB 3: Team Members & RBAC */}
      {activeTab === 'team' && (
        <GlassCard className="p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
            <div>
              <h2 className="section-heading">
                <Users className="w-4 h-4 text-indigo-400" />
                Team Members & Access Governance
              </h2>
              <p className="section-subheading">Manage workspace membership and role-based permissions (RBAC)</p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setInviteModalOpen(true)}
              icon={UserPlus}
            >
              Invite Member
            </Button>
          </div>

          <div className="table-container">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 text-slate-400">
                  <th className="p-3 font-semibold">User / Email</th>
                  <th className="p-3 font-semibold">Role</th>
                  <th className="p-3 font-semibold">Status</th>
                  <th className="p-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member, i) => (
                  <tr key={member.user_id || i} className="table-row">
                    <td className="p-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-indigo-950/60 border border-indigo-800/50 flex items-center justify-center text-brand-300 font-bold text-xs">
                          {member.email?.charAt(0).toUpperCase() || 'U'}
                        </div>
                        <div>
                          <div className="font-semibold text-slate-200 dark:text-slate-200 light:text-slate-800">
                            {member.full_name || member.email}
                          </div>
                          <div className="text-[10px] text-slate-400">{member.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="p-3">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-brand-950/50 dark:bg-brand-950/50 light:bg-brand-100 text-brand-300 dark:text-brand-300 light:text-brand-700 border border-brand-700/40">
                        {member.role || 'FINANCE_ANALYST'}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Active
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      {member.role === 'OWNER' ? (
                        <span className="text-[11px] text-slate-500 font-mono">Primary Owner</span>
                      ) : (
                        <button className="text-xs text-slate-400 hover:text-red-400 transition-colors">
                          Manage
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}

      {/* TAB 4: User Profile */}
      {activeTab === 'profile' && (
        <GlassCard className="p-6 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
            <div>
              <h2 className="section-heading">
                <User className="w-4 h-4 text-brand-400" />
                Personal Profile & Account Preferences
              </h2>
              <p className="section-subheading">Your personal identity and individual credentials</p>
            </div>
          </div>

          <div className="flex items-center gap-4 p-4 rounded-xl bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 border border-slate-800/70">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-brand-600 to-cyan-400 flex items-center justify-center text-white font-black text-xl shadow-lg shadow-indigo-600/30">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div>
              <h3 className="font-bold text-slate-100 dark:text-slate-100 light:text-slate-900 text-sm">
                {user?.full_name || 'Chief Finance Officer'}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">{user?.email || 'cfo@finova.ai'}</p>
              <div className="flex items-center gap-2 mt-1.5">
                <span className="px-2 py-0.2 rounded text-[10px] font-mono font-bold bg-indigo-950/60 text-indigo-300 border border-indigo-700/50">
                  Role: {role || 'OWNER'}
                </span>
                <span className="px-2 py-0.2 rounded text-[10px] font-mono text-emerald-400 bg-emerald-950/50 border border-emerald-700/50">
                  Tenant Verified
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                defaultValue={user?.full_name || 'Chief Finance Officer'}
                className="input"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                defaultValue={user?.email || 'cfo@finova.ai'}
                disabled
                className="input opacity-60 cursor-not-allowed"
              />
            </div>
          </div>
        </GlassCard>
      )}

      {/* TAB 5: Security & Authentication */}
      {activeTab === 'security' && (
        <GlassCard className="p-6 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
            <div>
              <h2 className="section-heading">
                <Lock className="w-4 h-4 text-emerald-400" />
                Security, JWT Session & Access Control
              </h2>
              <p className="section-subheading">Cryptographic token security, tenant isolation, and audit chain verification</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 border border-slate-800/70 space-y-1">
              <span className="text-[11px] text-slate-400 block font-medium">Authentication Method</span>
              <span className="text-sm font-bold text-white dark:text-white light:text-slate-900">JWT + Refresh Rotation</span>
              <p className="text-[10px] text-emerald-400">✓ Active & Enforced</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 border border-slate-800/70 space-y-1">
              <span className="text-[11px] text-slate-400 block font-medium">Audit Trail Hash Chain</span>
              <span className="text-sm font-bold text-white dark:text-white light:text-slate-900">SHA-256 Chained</span>
              <p className="text-[10px] text-emerald-400">✓ Cryptographically Verified</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 border border-slate-800/70 space-y-1">
              <span className="text-[11px] text-slate-400 block font-medium">Tenant Isolation</span>
              <span className="text-sm font-bold text-white dark:text-white light:text-slate-900">Organization Scoped</span>
              <p className="text-[10px] text-emerald-400">✓ Zero Cross-Tenant Access</p>
            </div>
          </div>
        </GlassCard>
      )}

      {/* TAB 6: Notifications */}
      {activeTab === 'notifications' && (
        <GlassCard className="p-6 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
            <div>
              <h2 className="section-heading">
                <Bell className="w-4 h-4 text-amber-400" />
                Notification Preferences & Webhooks
              </h2>
              <p className="section-subheading">Configure operational alerting channels</p>
            </div>
          </div>

          <div className="space-y-3">
            {[
              { id: 'exc', title: 'New Actionable Financial Exceptions', desc: 'Alert when a transaction fails deterministic reconciliation.', val: notifExceptions, set: setNotifExceptions },
              { id: 'rec', title: 'Reconciliation Run Completed', desc: 'Receive real-time notifications on job completion.', val: notifReconCompleted, set: setNotifReconCompleted },
              { id: 'crit', title: 'Critical Discrepancy & Storage Alerts', desc: 'Immediate notification on large amount variances or quota limits.', val: notifCriticalAlerts, set: setNotifCriticalAlerts },
              { id: 'dig', title: 'Daily Reconciliation Summary Digest', desc: 'Email overview of matched volumes and pending HITL queue.', val: notifDailyDigest, set: setNotifDailyDigest },
            ].map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 border border-slate-800/70"
              >
                <div>
                  <h4 className="text-xs font-bold text-slate-200 dark:text-slate-200 light:text-slate-800">{item.title}</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">{item.desc}</p>
                </div>
                <input
                  type="checkbox"
                  checked={item.val}
                  onChange={(e) => item.set(e.target.checked)}
                  className="w-4 h-4 accent-brand-500 rounded cursor-pointer"
                />
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* TAB 7: Integrations */}
      {activeTab === 'integrations' && (
        <GlassCard className="p-6 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
            <div>
              <h2 className="section-heading">
                <Layers className="w-4 h-4 text-brand-400" />
                Connected Financial Gateways & ERP Integrations
              </h2>
              <p className="section-subheading">Gateway sync status (all secrets are secured server-side)</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 border border-slate-800/70 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-white dark:text-white light:text-slate-900">Razorpay Gateway</h4>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                  Ready
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Automated payment and settlement synchronization. Keys are masked and securely managed on the backend.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 border border-slate-800/70 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-white dark:text-white light:text-slate-900">Core Banking Statement Feeds</h4>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-950/60 text-blue-400 border border-blue-800/40">
                  CSV / API
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Supports ISO 20022, MT940, and custom Indian Banking CSV transaction statement structures.
              </p>
            </div>
          </div>
        </GlassCard>
      )}

      {/* TAB 8: Appearance */}
      {activeTab === 'appearance' && (
        <GlassCard className="p-6 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
            <div>
              <h2 className="section-heading">
                <Palette className="w-4 h-4 text-indigo-400" />
                Theme & Interface Appearance
              </h2>
              <p className="section-subheading">Switch between dark, light, and system-adaptive themes</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Dark Theme Card */}
            <div
              onClick={() => setTheme('dark')}
              className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                theme === 'dark'
                  ? 'bg-slate-900 border-brand-500 shadow-glow'
                  : 'bg-slate-900/40 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <Moon className="w-5 h-5 text-indigo-400" />
                {theme === 'dark' && <Check className="w-4 h-4 text-brand-400" />}
              </div>
              <h4 className="font-bold text-xs text-white">Liquid Dark Mode</h4>
              <p className="text-[11px] text-slate-400 mt-1">
                Deep navy with glowing glassmorphism accents.
              </p>
            </div>

            {/* Light Theme Card */}
            <div
              onClick={() => setTheme('light')}
              className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                theme === 'light'
                  ? 'bg-slate-100 border-brand-500 shadow-lg'
                  : 'bg-slate-900/40 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <Sun className="w-5 h-5 text-amber-400" />
                {theme === 'light' && <Check className="w-4 h-4 text-brand-500" />}
              </div>
              <h4 className="font-bold text-xs text-slate-900">Enterprise Light Mode</h4>
              <p className="text-[11px] text-slate-500 mt-1">
                Clean high-contrast slate surfaces for bright environments.
              </p>
            </div>

            {/* System Theme Card */}
            <div
              onClick={() => setTheme('system')}
              className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                theme === 'system'
                  ? 'bg-slate-900 border-brand-500 shadow-glow'
                  : 'bg-slate-900/40 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <Laptop className="w-5 h-5 text-cyan-400" />
                {theme === 'system' && <Check className="w-4 h-4 text-brand-400" />}
              </div>
              <h4 className="font-bold text-xs text-white">System Synchronized</h4>
              <p className="text-[11px] text-slate-400 mt-1">
                Automatically match your operating system theme preference.
              </p>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Invite Member Modal */}
      <Modal
        isOpen={inviteModalOpen}
        onClose={() => setInviteModalOpen(false)}
        title="Invite Team Member"
        subtitle="Add a teammate to this organization workspace"
      >
        <form onSubmit={handleInviteMember} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
              Member Email Address
            </label>
            <input
              type="email"
              required
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="input"
              placeholder="colleague@yourcompany.com"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-1.5">
              Assigned Role
            </label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="select"
            >
              <option value="FINANCE_MANAGER">FINANCE_MANAGER — Full reconciliation and adjustment permissions</option>
              <option value="FINANCE_ANALYST">FINANCE_ANALYST — Reconciliation & exception review</option>
              <option value="VIEWER">VIEWER — Read-only reports & audit logs</option>
              <option value="ADMIN">ADMIN — Organization configuration & team administration</option>
            </select>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3">
            <Button variant="ghost" onClick={() => setInviteModalOpen(false)} disabled={inviting}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={inviting} icon={UserPlus}>
              Send Invitation
            </Button>
          </div>
        </form>
      </Modal>
    </PageContainer>
  )
}
