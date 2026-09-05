/**
 * Finova — Premium Shared UI Components
 * Vibrant Liquid design system — count-up, shimmer, shine, pulse-ring.
 */

import React, { useState, useEffect, useRef } from 'react'
import {
  AlertTriangle, CheckCircle, Info, XCircle, Sun, Moon,
  ChevronRight, ArrowUpRight, TrendingUp, TrendingDown,
  ShieldCheck, Brain, Clock, Zap, RefreshCw, X
} from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

// tiny rAF count-up hook
export function useCountUp(target, { duration = 700, enabled = true } = {}) {
  const [val, setVal] = useState(0)
  const raf = useRef(null)
  const start = useRef(null)
  const from = useRef(0)

  useEffect(() => {
    if (!enabled) { setVal(target); return }
    // parse numeric part if string like "94%"
    const numeric = typeof target === 'string' ? parseFloat(target.replace(/[^0-9.\-]/g, '')) : Number(target)
    const suffix = typeof target === 'string' ? target.replace(/[0-9.\-,\s]/g, '') : ''
    const isNumeric = !Number.isNaN(numeric)
    if (!isNumeric) { setVal(target); return }
    from.current = 0
    start.current = null
    const step = (ts) => {
      if (start.current === null) start.current = ts
      const p = Math.min((ts - start.current) / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3) // ease-out cubic
      const cur = from.current + (numeric - from.current) * eased
      // keep formatting: if target had + % keep roughly integer
      setVal(suffix ? `${Math.round(cur)}${suffix}` : Math.round(cur).toLocaleString())
      if (p < 1) raf.current = requestAnimationFrame(step)
      else setVal(target)
    }
    raf.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf.current)
  }, [target, duration, enabled])
  return val
}

// Page Container Wrapper
export function PageContainer({ children, className = '' }) {
  return (
    <div className={`max-w-7xl mx-auto space-y-6 animate-fade-in ${className}`}>
      {children}
    </div>
  )
}

// Page Header
export function PageHeader({ title, subtitle, badge, icon: Icon, actions }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/40 dark:border-slate-800/40 light:border-slate-200">
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600/30 to-indigo-500/20 border border-brand-500/30 flex items-center justify-center text-brand-400 shrink-0 mt-0.5 shadow-sm animate-float">
            <Icon className="w-5 h-5" />
          </div>
        )}
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-black text-slate-100 dark:text-slate-100 light:text-slate-900 tracking-tight">
              {title}
            </h1>
            {badge && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-brand-950/60 dark:bg-brand-950/60 light:bg-brand-100 text-brand-300 dark:text-brand-300 light:text-brand-700 border border-brand-700/50 dark:border-brand-700/50 light:border-brand-300">
                {badge}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-xs sm:text-sm text-slate-400 dark:text-slate-400 light:text-slate-500 mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2.5 flex-wrap">{actions}</div>}
    </div>
  )
}

// Liquid Glass Card
export function GlassCard({ children, className = '', glow = false, accent, gradientBorder = false, onClick, ...props }) {
  const accentCls = accent ? ` border-${accent}-500/20` : ''
  const glowCls = glow ? ' shadow-glow border-brand-500/40' : ''
  const gradCls = gradientBorder ? ` gradient-border border-aurora-${accent || 'brand'}` : ''
  return (
    <div
      className={`glass-card p-5${glowCls}${gradCls}${accentCls} ${className}`}
      onClick={onClick}
      {...props}
    >
      {children}
    </div>
  )
}

// KPI Stat Card — vibrant mapping + count-up + breathing chip
export function StatCard({
  label,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendDirection = 'up',
  color = 'brand',
  accent,
  className = '',
}) {
  const colorKey = accent || color
  const colorMap = {
    brand: {
      text: 'text-brand-400 dark:text-brand-400 light:text-indigo-600',
      bg: 'bg-brand-500/10 dark:bg-brand-500/10 light:bg-indigo-50 border-brand-500/30',
      icon: 'text-brand-400',
      glow: 'shadow-glow-sm',
    },
    cyan: {
      text: 'text-cyan-400 dark:text-cyan-300 light:text-cyan-600',
      bg: 'bg-cyan-500/10 dark:bg-cyan-500/10 light:bg-cyan-50 border-cyan-500/30',
      icon: 'text-cyan-400',
      glow: 'shadow-glow-cyan-sm',
    },
    fuchsia: {
      text: 'text-fuchsia-400 dark:text-fuchsia-300 light:text-fuchsia-600',
      bg: 'bg-fuchsia-500/10 dark:bg-fuchsia-500/10 light:bg-fuchsia-50 border-fuchsia-500/30',
      icon: 'text-fuchsia-400',
      glow: 'shadow-glow-fuchsia-sm',
    },
    teal: {
      text: 'text-teal-400 dark:text-teal-300 light:text-teal-600',
      bg: 'bg-teal-500/10 dark:bg-teal-500/10 light:bg-teal-50 border-teal-500/30',
      icon: 'text-teal-400',
      glow: 'shadow-glow-teal-sm',
    },
    emerald: {
      text: 'text-emerald-400 dark:text-emerald-400 light:text-emerald-600',
      bg: 'bg-emerald-500/10 dark:bg-emerald-500/10 light:bg-emerald-50 border-emerald-500/30',
      icon: 'text-emerald-400',
      glow: 'shadow-glow-emerald',
    },
    green: {
      text: 'text-emerald-400 dark:text-emerald-400 light:text-emerald-600',
      bg: 'bg-emerald-500/10 dark:bg-emerald-500/10 light:bg-emerald-50 border-emerald-500/30',
      icon: 'text-emerald-400',
      glow: 'shadow-glow-emerald',
    },
    amber: {
      text: 'text-amber-400 dark:text-amber-400 light:text-amber-600',
      bg: 'bg-amber-500/10 dark:bg-amber-500/10 light:bg-amber-50 border-amber-500/30',
      icon: 'text-amber-400',
      glow: 'shadow-glow-amber',
    },
    red: {
      text: 'text-red-400 dark:text-red-400 light:text-red-600',
      bg: 'bg-red-500/10 dark:bg-red-500/10 light:bg-red-50 border-red-500/30',
      icon: 'text-red-400',
      glow: '',
    },
    purple: {
      text: 'text-fuchsia-400 dark:text-fuchsia-300 light:text-purple-600',
      bg: 'bg-fuchsia-500/10 dark:bg-fuchsia-500/10 light:bg-purple-50 border-fuchsia-500/30',
      icon: 'text-fuchsia-400',
      glow: 'shadow-glow-fuchsia-sm',
    },
  }

  const chosen = colorMap[colorKey] || colorMap.brand
  const displayValue = useCountUp(value, { duration: 700 })

  return (
    <div className={`stat-card group ${chosen.glow} ${className}`}>
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-400 light:text-slate-500">
          {label}
        </p>
        {Icon && (
          <div className={`w-8 h-8 rounded-lg border flex items-center justify-center shrink-0 ${chosen.bg} group-hover:scale-110 group-hover:rotate-3 transition-transform duration-300 animate-float`} style={{ animationDuration: '5s' }}>
            <Icon className={`w-4 h-4 ${chosen.icon}`} />
          </div>
        )}
      </div>

      <div className="flex items-baseline justify-between gap-2">
        <p className={`text-2xl sm:text-3xl font-black font-mono tracking-tight ${chosen.text}`}>
          {displayValue}
        </p>
        {trend && (
          <span
            className={`inline-flex items-center gap-0.5 text-xs font-semibold group-hover:translate-x-0.5 transition-transform duration-200 ${
              trendDirection === 'up' ? 'text-emerald-400' : 'text-amber-400'
            }`}
          >
            {trendDirection === 'up' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {trend}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-500 mt-1.5 truncate">
          {subtitle}
        </p>
      )}
    </div>
  )
}

// Status Badge Mapping — updated to vibrant color-meaning system
export function StatusBadge({ status }) {
  const map = {
    MATCHED: 'badge-matched',
    AI_REVIEW: 'badge-ai',
    MANUAL_REVIEW: 'badge-manual',
    DUPLICATE: 'badge-duplicate',
    MISMATCH: 'badge-mismatch',
    MISSING: 'badge-mismatch',
    NO_COUNTERPART_SOURCE: 'badge-manual',
    STORAGE_LIMIT_REACHED: 'badge-mismatch',
    QUEUED: 'badge-info',
    PROCESSING: 'badge-ai',
    COMPLETED: 'badge-matched',
    FAILED: 'badge-mismatch',
    VALIDATED: 'badge-matched',
    PROCESSED: 'badge-matched',
    RECONCILE: 'badge-matched',
    REJECT: 'badge-mismatch',
  }

  const labels = {
    MATCHED: '✓ Matched',
    AI_REVIEW: '🤖 AI Review',
    MANUAL_REVIEW: '👤 Manual Review',
    DUPLICATE: '⊘ Duplicate',
    MISMATCH: '✗ Mismatch',
    MISSING: '? Missing',
    NO_COUNTERPART_SOURCE: '⚠ No Counterpart',
    STORAGE_LIMIT_REACHED: '⚠ Storage Limit',
    QUEUED: '⏳ Queued',
    PROCESSING: '⚡ Processing',
    COMPLETED: '✓ Completed',
    FAILED: '✕ Failed',
    VALIDATED: '✓ Validated',
    PROCESSED: '✓ Processed',
    RECONCILE: '✓ Reconcile',
    REJECT: '✕ Reject',
  }

  const cls = map[status] || 'badge bg-slate-800 text-slate-300 border-slate-700'
  return <span className={cls}>{labels[status] || status}</span>
}

// Animated Confidence Progress Bar — shimmer sweep
export function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100)
  const color =
    pct >= 90 ? 'bg-emerald-500' :
    pct >= 70 ? 'bg-cyan-500' :
    pct >= 50 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-800 dark:bg-slate-800 light:bg-slate-200 rounded-full overflow-hidden relative">
        <div
          className={`h-full rounded-full ${color} relative overflow-hidden`}
          style={{
            width: `${Math.min(100, Math.max(0, pct))}%`,
            transition: 'width 0.9s cubic-bezier(0.16,1,0.3,1)',
          }}
        >
          <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent" style={{ animation: 'sheen 1.8s ease-out infinite' }} />
        </div>
      </div>
      <span className="text-xs font-mono font-semibold text-slate-400 dark:text-slate-400 light:text-slate-600 w-9 text-right">
        {pct}%
      </span>
    </div>
  )
}

// Standard Button — with shine + icon nudge
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  loading = false,
  disabled = false,
  onClick,
  type = 'button',
  className = '',
  ...props
}) {
  const variantMap = {
    primary: 'btn-primary btn-shine',
    secondary: 'btn-secondary',
    danger: 'btn-danger btn-shine',
    success: 'btn-success btn-shine',
    outline: 'btn-outline',
    ghost: 'btn-ghost',
  }

  const sizeMap = {
    sm: 'py-1.5 px-3 text-[11px]',
    md: 'py-2 px-4 text-xs',
    lg: 'py-2.5 px-5 text-sm',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${variantMap[variant] || variantMap.primary} ${sizeMap[size] || sizeMap.md} group ${className}`}
      {...props}
    >
      {loading ? (
        <Spinner size="sm" />
      ) : Icon ? (
        <Icon className="w-3.5 h-3.5 shrink-0 group-hover:translate-x-0.5 group-hover:scale-110 transition-transform duration-200" />
      ) : null}
      {children}
      {variant === 'primary' && !loading && (
        <span className="absolute inset-0 rounded-xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{ boxShadow: '0 0 0 2px rgba(97,114,243,0.25)' }} />
      )}
    </button>
  )
}

// Loading Spinner
export function Spinner({ size = 'sm' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' }
  return (
    <div className={`${sizes[size]} border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin shrink-0`} />
  )
}

// Empty State View
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="glass-card flex flex-col items-center justify-center py-12 px-6 text-center">
      {Icon && (
        <div className="w-12 h-12 rounded-2xl bg-brand-500/10 dark:bg-brand-500/10 light:bg-brand-50 border border-brand-500/20 flex items-center justify-center text-brand-400 mb-3 shadow-inner animate-float">
          <Icon className="w-6 h-6" />
        </div>
      )}
      <h3 className="text-slate-200 dark:text-slate-200 light:text-slate-800 font-bold text-base mb-1">
        {title}
      </h3>
      <p className="text-slate-400 dark:text-slate-400 light:text-slate-500 text-xs max-w-sm mb-5 leading-relaxed">
        {description}
      </p>
      {action}
    </div>
  )
}

// Alert Notification Banner — with slide-in
export function Alert({ type = 'info', title, message, onDismiss, className = '' }) {
  const types = {
    info: {
      cls: 'bg-blue-950/40 dark:bg-blue-950/40 light:bg-blue-50 border-blue-800/60 dark:border-blue-800/60 light:border-blue-200 text-blue-300 dark:text-blue-300 light:text-blue-900',
      iconCls: 'text-blue-400',
      Icon: Info,
    },
    success: {
      cls: 'bg-emerald-950/40 dark:bg-emerald-950/40 light:bg-emerald-50 border-emerald-800/60 dark:border-emerald-800/60 light:border-emerald-200 text-emerald-300 dark:text-emerald-300 light:text-emerald-900',
      iconCls: 'text-emerald-400',
      Icon: CheckCircle,
    },
    warning: {
      cls: 'bg-amber-950/40 dark:bg-amber-950/40 light:bg-amber-50 border-amber-800/60 dark:border-amber-800/60 light:border-amber-200 text-amber-300 dark:text-amber-300 light:text-amber-900',
      iconCls: 'text-amber-400',
      Icon: AlertTriangle,
    },
    error: {
      cls: 'bg-red-950/40 dark:bg-red-950/40 light:bg-red-50 border-red-800/60 dark:border-red-800/60 light:border-red-200 text-red-300 dark:text-red-300 light:text-red-900',
      iconCls: 'text-red-400',
      Icon: XCircle,
    },
  }

  const { cls, iconCls, Icon } = types[type] || types.info

  return (
    <div className={`flex items-start gap-3 p-4 rounded-xl border banner-slide-in ${cls} ${className}`}>
      <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${iconCls}`} />
      <div className="flex-1 text-xs">
        {title && <p className="font-bold mb-0.5">{title}</p>}
        {message && <p className="opacity-90 leading-relaxed">{message}</p>}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="p-1 rounded-lg opacity-70 hover:opacity-100 hover:bg-black/10 transition-opacity"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}

// Currency Formatter
export function Currency({ amount, currency = '₹' }) {
  const n = parseFloat(amount) || 0
  return (
    <span className="font-mono font-medium">
      {currency}{n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
    </span>
  )
}

// Modal Dialog — with settle
export function Modal({ isOpen, onClose, title, subtitle, children, maxWidth = 'max-w-lg' }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md animate-fade-in">
      <div
        className={`glass-panel w-full ${maxWidth} p-6 shadow-2xl space-y-4 modal-enter border border-slate-700/80 dark:border-slate-700/80 light:border-slate-300 relative overflow-hidden`}
      >
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent pointer-events-none" />
        <div className="flex items-start justify-between pb-3 border-b border-slate-800 dark:border-slate-800 light:border-slate-200">
          <div>
            <h3 className="text-base font-bold text-slate-100 dark:text-slate-100 light:text-slate-900">{title}</h3>
            {subtitle && <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-500 mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-100 dark:hover:text-slate-100 light:hover:text-slate-900 rounded-lg hover:bg-slate-800/50 dark:hover:bg-slate-800/50 light:hover:bg-slate-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  )
}

// Confirmation Dialog Modal (e.g. for Logout, Delete)
export function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed?',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger',
  loading = false,
}) {
  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} maxWidth="max-w-md">
      <div className="space-y-4 py-2">
        <p className="text-xs text-slate-300 dark:text-slate-300 light:text-slate-600 leading-relaxed">
          {message}
        </p>
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant={variant} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// Segmented Tab Switcher
export function Tabs({ tabs, activeTab, onChange, className = '' }) {
  return (
    <div className={`flex items-center gap-1 p-1 rounded-xl bg-slate-900/80 dark:bg-slate-900/80 light:bg-slate-200/80 border border-slate-800/80 dark:border-slate-800/80 light:border-slate-300 overflow-x-auto ${className}`}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all duration-200 ${
              isActive
                ? 'bg-gradient-to-r from-brand-600 to-indigo-600 text-white shadow-md shadow-brand-600/30'
                : 'text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-slate-200 dark:hover:text-slate-200 light:hover:text-slate-900 hover:bg-slate-800/40 dark:hover:bg-slate-800/40 light:hover:bg-slate-300/60'
            }`}
          >
            {tab.icon && <tab.icon className="w-3.5 h-3.5 shrink-0" />}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                  isActive ? 'bg-white/20 text-white' : 'bg-slate-800 dark:bg-slate-800 light:bg-slate-300 text-slate-400'
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

// Light / Dark Theme Toggle Button
export function ThemeToggle({ className = '' }) {
  const { isDark, toggleTheme } = useTheme()
  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`p-2 rounded-xl border border-slate-800/80 dark:border-slate-800/80 light:border-slate-300 bg-slate-900/60 dark:bg-slate-900/60 light:bg-white text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-brand-400 dark:hover:text-brand-400 light:hover:text-brand-600 hover:border-brand-500/40 transition-all ${className}`}
      title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
      aria-label="Toggle theme"
    >
      {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-600" />}
    </button>
  )
}
