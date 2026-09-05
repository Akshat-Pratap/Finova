import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ShieldCheck, Lock, Mail, User, Building, ArrowRight, AlertCircle } from 'lucide-react'
import { ThemeToggle } from '../components/ui'

export default function Register() {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [orgName, setOrgName] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await register(email, password, fullName, orgName)
      navigate('/')
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-dark-950 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden transition-colors duration-300">
      {/* Aurora orbs — layer over global body::before */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-28 left-1/2 -translate-x-1/2 w-[110%] h-[360px] rounded-full blur-3xl opacity-50" style={{ background: 'radial-gradient(ellipse at 50% 50%, rgba(97,114,243,0.16) 0%, rgba(232,121,249,0.08) 45%, transparent 72%)', animation: 'auroraDrift 20s ease-in-out infinite alternate' }} />
        <div className="absolute top-1/4 left-[12%] w-[480px] h-[480px] rounded-full blur-[90px]" style={{ background: 'radial-gradient(circle, rgba(97,114,243,0.18) 0%, transparent 70%)', animation: 'float 10s ease-in-out infinite alternate' }} />
        <div className="absolute bottom-[8%] right-[6%] w-[520px] h-[420px] rounded-full blur-[100px]" style={{ background: 'radial-gradient(circle, rgba(20,184,166,0.10) 0%, transparent 70%)', animation: 'float 12s ease-in-out infinite alternate', animationDelay: '-3s' }} />
      </div>

      <div className="absolute top-6 right-6 z-20">
        <ThemeToggle />
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md z-10">
        <div className="flex items-center justify-center space-x-3 mb-3">
          <div className="w-12 h-12 bg-gradient-to-tr from-brand-600 via-brand-500 to-cyan-400 rounded-2xl flex items-center justify-center shadow-lg shadow-brand-500/25 animate-float">
            <ShieldCheck className="w-7 h-7 text-white" />
          </div>
          <span className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">
            FINOVA
          </span>
        </div>
        <h2 className="text-center text-sm font-medium text-slate-600 dark:text-slate-400">
          Set up your organization & financial workspace
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md z-10">
        <div className="relative py-8 px-6 shadow-2xl sm:rounded-[2rem] sm:px-10 overflow-hidden" style={{ background: 'rgba(17,25,46,0.62)', backdropFilter: 'blur(24px) saturate(180%)', WebkitBackdropFilter: 'blur(24px) saturate(180%)', border: '1px solid rgba(255,255,255,0.12)', boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.12), 0 20px 60px -12px rgba(0,0,0,0.5)' }}>
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent pointer-events-none" />
          <form className="space-y-4 stagger" onSubmit={handleSubmit} autoComplete="off" data-lpignore="true">
            {error && (
              <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center space-x-2.5 text-rose-600 dark:text-rose-400 text-xs font-medium banner-slide-in">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">Full Name</label>
              <div className="relative group">
                <User className="w-4 h-4 text-slate-400 group-focus-within:text-brand-400 absolute left-3.5 top-3.5 transition-colors" />
                <input type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full bg-white/80 dark:bg-slate-900/50 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700/60 rounded-2xl pl-10 pr-3.5 py-3 text-xs placeholder-slate-400 focus:outline-none focus:border-brand-500/50 focus:ring-2 focus:ring-brand-500/20 transition-all backdrop-blur" placeholder="Sarah Jenkins" autoComplete="off" data-lpignore="true" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">Organization Name</label>
              <div className="relative group">
                <Building className="w-4 h-4 text-slate-400 group-focus-within:text-teal-400 absolute left-3.5 top-3.5 transition-colors" />
                <input type="text" required value={orgName} onChange={(e) => setOrgName(e.target.value)} className="w-full bg-white/80 dark:bg-slate-900/50 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700/60 rounded-2xl pl-10 pr-3.5 py-3 text-xs placeholder-slate-400 focus:outline-none focus:border-brand-500/50 focus:ring-2 focus:ring-brand-500/20 transition-all backdrop-blur" placeholder="Acme FinTech Ltd" autoComplete="off" data-lpignore="true" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">Work Email</label>
              <div className="relative group">
                <Mail className="w-4 h-4 text-slate-400 group-focus-within:text-cyan-400 absolute left-3.5 top-3.5 transition-colors" />
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full bg-white/80 dark:bg-slate-900/50 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700/60 rounded-2xl pl-10 pr-3.5 py-3 text-xs placeholder-slate-400 focus:outline-none focus:border-brand-500/50 focus:ring-2 focus:ring-brand-500/20 transition-all backdrop-blur" placeholder="sarah@acme.com" autoComplete="off" data-lpignore="true" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">Password</label>
              <div className="relative group">
                <Lock className="w-4 h-4 text-slate-400 group-focus-within:text-fuchsia-400 absolute left-3.5 top-3.5 transition-colors" />
                <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full bg-white/80 dark:bg-slate-900/50 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700/60 rounded-2xl pl-10 pr-3.5 py-3 text-xs placeholder-slate-400 focus:outline-none focus:border-fuchsia-500/40 focus:ring-2 focus:ring-fuchsia-500/20 transition-all backdrop-blur" placeholder="••••••••••••" autoComplete="new-password" data-lpignore="true" />
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary btn-shine group w-full mt-2 py-3.5 text-sm font-bold shadow-xl shadow-brand-500/25 flex items-center justify-center gap-2 relative overflow-hidden rounded-2xl">
              <span className="group-hover:translate-x-0.5 transition-transform duration-200">{loading ? 'Creating Organization...' : 'Create Organization Workspace'}</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200" />
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-slate-500 dark:text-slate-400">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-600 dark:text-brand-400 hover:underline font-semibold">
              Sign in to console
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
