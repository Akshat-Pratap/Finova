import React, { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Database, GitMerge, CreditCard, AlertTriangle,
  Layers, FileDown, TrendingUp, ShieldCheck, Settings, LogOut,
  Building2, ChevronDown, Check, User
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

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
  const [orgDropdownOpen, setOrgDropdownOpen] = useState(false)
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 font-sans text-slate-100">
      {/* Left Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col flex-shrink-0 z-20">
        {/* Brand Header */}
        <div className="p-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-white font-black text-lg tracking-tight leading-none">FINOVA</h1>
              <p className="text-indigo-400 text-[11px] font-semibold tracking-wide uppercase mt-0.5">Finance Controller</p>
            </div>
          </div>
        </div>

        {/* Tenant Organization Switcher */}
        <div className="p-3 border-b border-slate-800 relative">
          <button
            type="button"
            onClick={() => setOrgDropdownOpen(!orgDropdownOpen)}
            className="w-full flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 hover:bg-slate-950 border border-slate-800/80 transition-colors text-left"
          >
            <div className="flex items-center gap-2.5 truncate">
              <Building2 className="w-4 h-4 text-indigo-400 shrink-0" />
              <div className="truncate">
                <div className="text-xs font-bold text-white truncate">{activeOrg?.name || 'Primary Org'}</div>
                <div className="text-[10px] text-slate-400 flex items-center gap-1">
                  <span>{activeOrg?.base_currency || 'INR'}</span>
                  <span>•</span>
                  <span className="text-indigo-400 font-semibold">{role}</span>
                </div>
              </div>
            </div>
            <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${orgDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* Org Switcher Dropdown */}
          {orgDropdownOpen && (
            <div className="absolute top-full left-3 right-3 mt-1.5 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl z-50 p-1.5 space-y-1">
              <div className="text-[10px] uppercase font-bold text-slate-500 px-2 py-1">Workspaces</div>
              {organizations.map((org) => {
                const isSelected = org.organization_id === activeOrg?.organization_id
                return (
                  <button
                    key={org.organization_id}
                    onClick={() => {
                      switchOrganization(org)
                      setOrgDropdownOpen(false)
                    }}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                      isSelected ? 'bg-indigo-600/20 text-indigo-300 font-semibold' : 'text-slate-300 hover:bg-slate-800'
                    }`}
                  >
                    <span className="truncate">{org.name}</span>
                    {isSelected && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-150 ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/25'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User Footer & Logout */}
        <div className="p-3 border-t border-slate-800">
          <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/40 border border-slate-800/60">
            <div className="flex items-center gap-2.5 truncate">
              <div className="w-7 h-7 rounded-lg bg-indigo-950 border border-indigo-800/50 flex items-center justify-center text-indigo-400 font-bold text-xs">
                {user?.full_name ? user.full_name.charAt(0) : 'U'}
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-white truncate">{user?.full_name || 'User'}</div>
                <div className="text-[10px] text-slate-500 truncate">{user?.email || 'user@finova.ai'}</div>
              </div>
            </div>

            <button
              onClick={handleLogout}
              className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main App Page */}
      <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-950 relative">
        <Outlet />
      </main>
    </div>
  )
}
