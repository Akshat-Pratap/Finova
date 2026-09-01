/**
 * Finova — Shared UI Components
 */

import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'

// Status badge mapping
export function StatusBadge({ status }) {
  const map = {
    MATCHED: 'badge-matched',
    AI_REVIEW: 'badge-ai',
    MANUAL_REVIEW: 'badge-manual',
    DUPLICATE: 'badge-duplicate',
    MISMATCH: 'badge-mismatch',
    MISSING: 'badge-mismatch',
  }
  const labels = {
    MATCHED: '✓ Matched',
    AI_REVIEW: '🤖 AI Review',
    MANUAL_REVIEW: '👤 Manual',
    DUPLICATE: '⊘ Duplicate',
    MISMATCH: '✗ Mismatch',
    MISSING: '? Missing',
  }
  const cls = map[status] || 'badge bg-gray-700 text-gray-300'
  return <span className={cls}>{labels[status] || status}</span>
}

// Confidence bar
export function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100)
  const color =
    pct >= 90 ? 'bg-green-500' :
    pct >= 70 ? 'bg-brand-500' :
    pct >= 50 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-dark-600 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-gray-400 w-10 text-right">{pct}%</span>
    </div>
  )
}

// Stat card
export function StatCard({ label, value, subtitle, icon: Icon, trend, color = 'brand' }) {
  const colors = {
    brand: 'text-brand-400',
    green: 'text-green-400',
    amber: 'text-amber-400',
    red: 'text-red-400',
    purple: 'text-purple-400',
  }
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs text-gray-400 uppercase tracking-wider font-medium">{label}</p>
        {Icon && <Icon className={`w-4 h-4 ${colors[color]}`} />}
      </div>
      <p className={`text-2xl font-bold ${colors[color]}`}>{value}</p>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    </div>
  )
}

// Loading spinner
export function Spinner({ size = 'sm' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' }
  return (
    <div className={`${sizes[size]} border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin`} />
  )
}

// Empty state
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {Icon && <Icon className="w-12 h-12 text-gray-600 mb-4" />}
      <h3 className="text-gray-300 font-medium text-lg mb-1">{title}</h3>
      <p className="text-gray-500 text-sm mb-6 max-w-sm">{description}</p>
      {action}
    </div>
  )
}

// Alert banner
export function Alert({ type = 'info', title, message }) {
  const types = {
    info: { cls: 'bg-blue-900/30 border-blue-700/50 text-blue-300', Icon: Info },
    success: { cls: 'bg-green-900/30 border-green-700/50 text-green-300', Icon: CheckCircle },
    warning: { cls: 'bg-amber-900/30 border-amber-700/50 text-amber-300', Icon: AlertTriangle },
    error: { cls: 'bg-red-900/30 border-red-700/50 text-red-300', Icon: XCircle },
  }
  const { cls, Icon } = types[type]
  return (
    <div className={`flex gap-3 p-4 rounded-lg border ${cls}`}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div>
        {title && <p className="font-medium text-sm">{title}</p>}
        {message && <p className="text-sm opacity-80 mt-0.5">{message}</p>}
      </div>
    </div>
  )
}

// Format currency
export function Currency({ amount, currency = '₹' }) {
  const n = parseFloat(amount) || 0
  return (
    <span className="font-mono">
      {currency}{n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
    </span>
  )
}

// Page header
export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="text-xl font-bold text-white">{title}</h1>
        {subtitle && <p className="text-sm text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  )
}
