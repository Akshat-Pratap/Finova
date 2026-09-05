import React, { useState } from 'react'
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Database, GitMerge, CreditCard, AlertTriangle,
  Layers, FileDown, TrendingUp, ShieldCheck, Settings, LogOut,
  Building2, ChevronDown, Check, Menu, X, Bell, User, Sparkles
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { ThemeToggle, ConfirmationDialog } from './ui'

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/datasets', icon: Database, label: 'Datasets & Mapping' },
  { to: '/reconciliation', icon: GitMerge, label: 'Reconciliation' },
  { to: '/transactions', icon: CreditCard, label: 'Transactions' },
  { to: '/exceptions', icon: AlertTriangle, label: 'Exceptions & HITL' },
  { to: '/integrations', icon: Layers, label: 'Integrations Hub' },
  { to: '/reports', icon: FileDown, label: 'Financial Reports' },
  { to: '/forecast', icon: TrendingUp, label: 'Cash Forecast' },
  { to: '/audit', icon: ShieldCheck, label: 'Audit Trail' },
  { to: '/settings', icon: Settings, label: 'Settings & Team' },
]

export default function Layout() {
  const { user, activeOrg, organizations, role, logout, switchOrganization } = useAuth()
  const { isDark } = useTheme()
  const [orgDropdownOpen, setOrgDropdownOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [logoutModalOpen, setLogoutModalOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const handleConfirmLogout = () => {
    logout()
    setLogoutModalOpen(false)
    navigate('/login')
  }

  // Get current page label for header breadcrumb
  const currentNav = NAV_ITEMS.find((item) =>
    item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)
  )

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-600/30 text-white shrink-0">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h1 className="font-black text-lg tracking-tight text-slate-100 dark:text-slate-100 light:text-slate-900 leading-none">
                  FINOVA
                </h1>
                <span className="px-1.5 py-0.2 rounded text-[9px] font-extrabold bg-gradient-to-r from-brand-500 to-cyan-400 text-white">
                  PRO
                </span>
              </div>
              <p className="text-brand-400 dark:text-brand-400 light:text-indigo-600 text-[10px] font-bold tracking-wider uppercase mt-1">
                AI Finance Controller
              </p>
            </div>
          </div>

          {/* Close button on mobile */}
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-100 dark:hover:text-slate-100 light:hover:text-slate-900 hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Tenant Organization Switcher */}
      <div className="p-3 border-b border-slate-800/60 dark:border-slate-800/60 light:border-slate-200 relative">
        <button
          type="button"
          onClick={() => setOrgDropdownOpen(!orgDropdownOpen)}
          className="w-full flex items-center justify-between p-2.5 rounded-xl bg-slate-900/70 dark:bg-slate-900/70 light:bg-slate-100 hover:bg-slate-850 dark:hover:bg-slate-850 light:hover:bg-slate-200 border border-slate-800/80 dark:border-slate-800/80 light:border-slate-300 transition-all text-left group shadow-sm"
        >
          <div className="flex items-center gap-2.5 truncate">
            <div className="w-7 h-7 rounded-lg bg-brand-500/15 dark:bg-brand-500/15 light:bg-brand-100 border border-brand-500/30 flex items-center justify-center text-brand-400 shrink-0">
              <Building2 className="w-4 h-4" />
            </div>
            <div className="truncate">
              <div className="text-xs font-bold text-slate-100 dark:text-slate-100 light:text-slate-900 truncate">
                {activeOrg?.name || 'Finova Global Financials'}
              </div>
              <div className="text-[10px] text-slate-400 dark:text-slate-400 light:text-slate-500 flex items-center gap-1.5 font-mono mt-0.5">
                <span>{activeOrg?.base_currency || 'INR'}</span>
                <span>•</span>
                <span className="text-brand-400 dark:text-brand-400 light:text-indigo-600 font-semibold">{role || 'OWNER'}</span>
              </div>
            </div>
          </div>
          <ChevronDown
            className={`w-3.5 h-3.5 text-slate-400 group-hover:text-slate-200 transition-transform ${
              orgDropdownOpen ? 'rotate-180' : ''
            }`}
          />
        </button>

        {/* Org Switcher Dropdown */}
        {orgDropdownOpen && (
          <div className="absolute top-full left-3 right-3 mt-1.5 bg-slate-900 dark:bg-slate-900 light:bg-white border border-slate-800 dark:border-slate-800 light:border-slate-200 rounded-xl shadow-2xl z-50 p-1.5 space-y-1 animate-slide-down">
            <div className="text-[10px] uppercase font-bold text-slate-500 px-2 py-1">Organizations</div>
            {organizations.length > 0 ? (
              organizations.map((org) => {
                const isSelected = org.organization_id === activeOrg?.organization_id
                return (
                  <button
                    key={org.organization_id}
                    onClick={() => {
                      switchOrganization(org)
                      setOrgDropdownOpen(false)
                    }}
                    className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs transition-colors ${
                      isSelected
                        ? 'bg-brand-600 text-white font-semibold shadow-sm'
                        : 'text-slate-300 dark:text-slate-300 light:text-slate-700 hover:bg-slate-800/80 dark:hover:bg-slate-800/80 light:hover:bg-slate-100'
                    }`}
                  >
                    <span className="truncate">{org.name}</span>
                    {isSelected && <Check className="w-3.5 h-3.5 text-white" />}
                  </button>
                )
              })
            ) : (
              <div className="text-xs text-slate-400 p-2">Default Workspace</div>
            )}
          </div>
        )}
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={() => setMobileMenuOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 group ${
                isActive
                  ? 'bg-gradient-to-r from-brand-600 to-indigo-600 text-white shadow-lg shadow-indigo-600/30 font-bold'
                  : 'text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-slate-100 dark:hover:text-slate-100 light:hover:text-slate-900 hover:bg-slate-800/50 dark:hover:bg-slate-800/50 light:hover:bg-slate-100'
              }`
            }
          >
            <item.icon className="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
            <span className="truncate">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User Footer Profile & Sign Out */}
      <div className="p-3 border-t border-slate-800/80 dark:border-slate-800/80 light:border-slate-200">
        <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-100 border border-slate-800/80 dark:border-slate-800/80 light:border-slate-200 shadow-sm">
          <div className="flex items-center gap-2.5 truncate">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-900 to-brand-900 dark:from-indigo-900 dark:to-brand-900 light:from-indigo-100 light:to-brand-100 border border-brand-500/30 flex items-center justify-center text-brand-300 dark:text-brand-300 light:text-indigo-700 font-bold text-xs shrink-0 shadow-inner">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="truncate">
              <div className="text-xs font-bold text-slate-100 dark:text-slate-100 light:text-slate-900 truncate">
                {user?.full_name || 'Chief Finance Officer'}
              </div>
              <div className="text-[10px] text-slate-400 dark:text-slate-400 light:text-slate-500 truncate">
                {user?.email || 'cfo@finova.ai'}
              </div>
            </div>
          </div>

          <button
            onClick={() => setLogoutModalOpen(true)}
            className="p-1.5 text-slate-400 hover:text-red-400 dark:hover:text-red-400 light:hover:text-red-600 hover:bg-slate-800/60 dark:hover:bg-slate-800/60 light:hover:bg-slate-200 rounded-lg transition-colors ml-1 shrink-0"
            title="Sign Out"
            aria-label="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 dark:bg-slate-950 light:bg-slate-50 font-sans text-slate-100 dark:text-slate-100 light:text-slate-900">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex w-64 glass-panel rounded-none border-r border-slate-800/80 dark:border-slate-800/80 light:border-slate-200 flex-col flex-shrink-0 z-30 shadow-xl">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop & Sidebar */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm animate-fade-in"
            onClick={() => setMobileMenuOpen(false)}
          />
          <aside className="relative w-72 max-w-[85vw] h-full glass-panel rounded-none border-r border-slate-800 flex flex-col z-50 shadow-2xl bg-slate-900 dark:bg-slate-900 light:bg-white animate-slide-up">
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-16 px-4 sm:px-8 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200 glass-panel rounded-none flex items-center justify-between gap-4 z-20 shrink-0">
          <div className="flex items-center gap-3">
            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden p-2 rounded-xl border border-slate-800/80 dark:border-slate-800/80 light:border-slate-300 bg-slate-900/60 dark:bg-slate-900/60 light:bg-white text-slate-300 dark:text-slate-300 light:text-slate-700"
              aria-label="Open Navigation Menu"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Breadcrumb / Page Label */}
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 dark:text-slate-400 light:text-slate-500">
              <span className="hidden sm:inline">FINOVA</span>
              <span className="hidden sm:inline">/</span>
              <span className="text-slate-100 dark:text-slate-100 light:text-slate-900 font-bold">
                {currentNav?.label || 'Dashboard'}
              </span>
            </div>
          </div>

          {/* Right Header Utilities */}
          <div className="flex items-center gap-3">
            {/* Live Environment Badge */}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/50 dark:bg-emerald-950/50 light:bg-emerald-100 border border-emerald-800/50 dark:border-emerald-800/50 light:border-emerald-300 text-emerald-400 dark:text-emerald-400 light:text-emerald-800 text-[11px] font-mono font-bold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>LIVE</span>
            </div>

            {/* Theme Switcher Toggle */}
            <ThemeToggle />

            {/* Organization Tag */}
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/60 dark:bg-slate-900/60 light:bg-white border border-slate-800/80 dark:border-slate-800/80 light:border-slate-300 text-xs font-semibold text-slate-300 dark:text-slate-300 light:text-slate-700 shadow-sm">
              <Building2 className="w-3.5 h-3.5 text-brand-400" />
              <span className="truncate max-w-[140px]">{activeOrg?.name || 'Primary Org'}</span>
            </div>
          </div>
        </header>

        {/* Page Content Viewport */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 relative">
          <Outlet />
        </main>
      </div>

      {/* Logout Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={logoutModalOpen}
        onClose={() => setLogoutModalOpen(false)}
        onConfirm={handleConfirmLogout}
        title="Sign Out of FINOVA"
        message="Are you sure you want to sign out? Your active session credentials and workspace access tokens will be securely cleared."
        confirmLabel="Sign Out"
        cancelLabel="Cancel"
        variant="danger"
      />
    </div>
  )
}
