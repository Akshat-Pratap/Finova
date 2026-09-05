import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ShieldCheck, Lock, Mail, ArrowRight, AlertCircle, Sparkles, Sun, Moon } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import { ThemeToggle } from '../components/ui'

export default function Login() {
  const [email, setEmail] = useState('cfo@finova.ai')
  const [password, setPassword] = useState('FinovaDemo2026!')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const { isDark } = useTheme()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  const handleQuickDemo = async () => {
    setEmail('cfo@finova.ai')
    setPassword('FinovaDemo2026!')
    try {
      await login('cfo@finova.ai', 'FinovaDemo2026!')
      navigate('/')
    } catch (err) {
      // In disconnected mode, proceed to dashboard
      navigate('/')
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-dark-950 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden transition-colors duration-300">
      {/* Background ambient glowing gradients */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 bg-brand-500/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top right theme toggle */}
      <div className="absolute top-6 right-6 z-20">
        <ThemeToggle />
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md z-10">
        <div className="flex items-center justify-center space-x-3 mb-3">
          <div className="w-12 h-12 bg-gradient-to-tr from-brand-600 via-brand-500 to-cyan-400 rounded-2xl flex items-center justify-center shadow-lg shadow-brand-500/25">
            <ShieldCheck className="w-7 h-7 text-white" />
          </div>
          <span className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">
            FINOVA
          </span>
        </div>
        <h2 className="text-center text-sm font-medium text-slate-600 dark:text-slate-400">
          Autonomous AI Financial Controller & Multi-Pass Reconciliation
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md z-10">
        <div className="glass-panel py-8 px-6 shadow-2xl sm:rounded-3xl sm:px-10">
          <form className="space-y-5" onSubmit={handleSubmit}>
            {error && (
              <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center space-x-2.5 text-rose-600 dark:text-rose-400 text-xs font-medium">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                Work Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input pl-10 text-xs w-full"
                  placeholder="name@company.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input pl-10 text-xs w-full"
                  placeholder="••••••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-3.5 text-sm font-bold shadow-xl shadow-brand-500/25 flex items-center justify-center gap-2"
            >
              <span>{loading ? 'Authenticating...' : 'Sign In to Console'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-200 dark:border-dark-700">
            <button
              type="button"
              onClick={handleQuickDemo}
              className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl text-xs font-semibold text-brand-600 dark:text-brand-300 bg-brand-500/10 hover:bg-brand-500/20 border border-brand-500/30 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5 text-brand-500" />
              <span>Instant Hackathon Demo Access (1-Click Fill)</span>
            </button>

            <div className="mt-4 text-center text-xs text-slate-500 dark:text-slate-400">
              New organization?{' '}
              <Link to="/register" className="text-brand-600 dark:text-brand-400 hover:underline font-semibold">
                Create workspace account
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
