import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ShieldCheck, Lock, Mail, ArrowRight, AlertCircle, Loader2 } from 'lucide-react'
import { ThemeToggle } from '../components/ui'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const cardRef = useRef(null)

  // Force clear on mount — guarantees empty fields after signout / first load
  useEffect(() => {
    setEmail('')
    setPassword('')
  }, [])

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

  const handleCardMove = (e) => {
    const el = cardRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const cx = rect.width / 2
    const cy = rect.height / 2
    const rx = ((y - cy) / cy) * -4
    const ry = ((x - cx) / cx) * 5
    el.style.transform = `perspective(1000px) rotateX(${rx}deg) rotateY(${ry}deg) translateZ(0)`
  }

  const handleCardLeave = () => {
    const el = cardRef.current
    if (el) el.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0)'
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-dark-950 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden transition-colors duration-300">
      {/* ===== 3D Liquid Glass Background Layer ===== */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* Subtle grid */}
        <div
          className="absolute inset-0 opacity-[0.035] dark:opacity-[0.05]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(97,114,243,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(97,114,243,0.4) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />
        {/* Aurora wave */}
        <div
          className="absolute -top-32 left-1/2 -translate-x-1/2 w-[120%] h-[420px] rounded-full blur-3xl opacity-60"
          style={{
            background:
              'radial-gradient(ellipse at 50% 50%, rgba(97,114,243,0.18) 0%, rgba(56,189,248,0.12) 30%, rgba(139,92,246,0.10) 55%, transparent 75%)',
            animation: 'auroraDrift 18s ease-in-out infinite alternate',
          }}
        />
        {/* Orb 1 */}
        <div
          className="absolute rounded-full blur-[90px] will-change-transform"
          style={{
            top: '-8%',
            left: '18%',
            width: '600px',
            height: '600px',
            background: 'radial-gradient(circle, rgba(97,114,243,0.22) 0%, rgba(79,83,232,0.14) 45%, transparent 72%)',
            animation: 'float1 12s ease-in-out infinite alternate',
          }}
        />
        {/* Orb 2 */}
        <div
          className="absolute rounded-full blur-[110px] will-change-transform"
          style={{
            bottom: '-12%',
            right: '3%',
            width: '700px',
            height: '500px',
            background: 'radial-gradient(circle, rgba(6,182,212,0.14) 0%, rgba(56,189,248,0.09) 40%, transparent 70%)',
            animation: 'float2 15s ease-in-out infinite alternate',
            animationDelay: '-2s',
          }}
        />
        {/* Orb 3 */}
        <div
          className="absolute rounded-full blur-[90px] will-change-transform"
          style={{
            top: '42%',
            right: '22%',
            width: '420px',
            height: '420px',
            background: 'radial-gradient(circle, rgba(139,92,246,0.16) 0%, rgba(97,114,243,0.10) 50%, transparent 72%)',
            animation: 'float3 10s ease-in-out infinite alternate',
            animationDelay: '-4s',
          }}
        />
        {/* Bottom vignette */}
        <div className="absolute inset-0 bg-gradient-to-t from-dark-950/40 via-transparent to-transparent dark:from-dark-950/60" />
      </div>

      {/* Top right theme toggle */}
      <div className="absolute top-6 right-6 z-20">
        <ThemeToggle />
      </div>

      {/* Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md z-10">
        <div className="flex items-center justify-center space-x-3 mb-3">
          <div
            className="w-14 h-14 bg-gradient-to-tr from-brand-600 via-indigo-500 to-cyan-400 rounded-2xl flex items-center justify-center shadow-xl shadow-brand-500/20 relative"
            style={{ animation: 'logoFloat 3.2s ease-in-out infinite alternate' }}
          >
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-white/25 to-transparent opacity-60 pointer-events-none" />
            <ShieldCheck className="w-7 h-7 text-white relative drop-shadow-sm" />
          </div>
          <span className="text-4xl font-black tracking-tight text-slate-900 dark:text-white drop-shadow-sm">
            FINOVA
          </span>
        </div>
        <h2 className="text-center text-sm font-medium text-slate-600 dark:text-slate-400/90">
          Autonomous AI Financial Controller & Multi-Pass Reconciliation
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md z-10">
        {/* Liquid glass card */}
        <div
          ref={cardRef}
          onMouseMove={handleCardMove}
          onMouseLeave={handleCardLeave}
          className="relative py-8 px-6 sm:px-10 sm:rounded-[2rem] overflow-hidden animate-slide-up"
          style={{
            background: 'rgba(17,25,46,0.62)',
            backdropFilter: 'blur(24px) saturate(180%)',
            WebkitBackdropFilter: 'blur(24px) saturate(180%)',
            border: '1px solid rgba(255,255,255,0.12)',
            boxShadow:
              'inset 0 1px 0 0 rgba(255,255,255,0.14), 0 20px 60px -12px rgba(0,0,0,0.55), 0 0 40px rgba(97,114,243,0.14)',
            transition: 'transform 0.35s ease, box-shadow 0.3s ease',
          }}
        >
          {/* Specular top highlight */}
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent pointer-events-none" />
          {/* Inner glow */}
          <div className="absolute -top-24 -right-24 w-72 h-72 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-20 -left-20 w-64 h-64 bg-cyan-400/10 rounded-full blur-3xl pointer-events-none" />

          {/* Light mode override via inline style fix - Tailwind handles dark: */}
          <style>{`
            .light-card-override { background: rgba(255,255,255,0.78) !important; border-color: rgba(0,0,0,0.07) !important; box-shadow: inset 0 1px 0 0 rgba(255,255,255,0.9), 0 20px 60px -12px rgba(0,0,0,0.10), 0 0 30px rgba(97,114,243,0.08) !important; }
            :global(.light) [data-glass-card] { background: rgba(255,255,255,0.78) !important; }
          `}</style>

          <form
            className="space-y-5 relative stagger"
            onSubmit={handleSubmit}
            autoComplete="off"
            data-lpignore="true"
            data-form-type="other"
          >
            {/* Honeypot fields to trap Chrome autofill — excluded from stagger */}
            <input className="no-stagger" type="text" name="prevent_autofill_username" autoComplete="off" tabIndex={-1} aria-hidden="true" style={{ position: 'absolute', left: '-9999px', opacity: 0, height: 0, width: 0 }} />
            <input className="no-stagger" type="password" name="prevent_autofill_password" autoComplete="off" tabIndex={-1} aria-hidden="true" style={{ position: 'absolute', left: '-9999px', opacity: 0, height: 0, width: 0 }} />

            {error && (
              <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center space-x-2.5 text-rose-600 dark:text-rose-400 text-xs font-medium backdrop-blur">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                Work Email
              </label>
              <div className="relative group">
                <Mail className="w-4 h-4 text-slate-400 group-focus-within:text-brand-400 absolute left-3.5 top-3.5 transition-colors" />
                <input
                  type="email"
                  name="finova-work-email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="off"
                  spellCheck={false}
                  data-lpignore="true"
                  data-form-type="other"
                  readOnly={false}
                  onFocus={(e) => e.target.removeAttribute('readOnly')}
                  className="w-full bg-white/80 dark:bg-slate-900/50 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700/60 rounded-2xl pl-10 pr-3.5 py-3.5 text-xs placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-brand-500/50 focus:ring-2 focus:ring-brand-500/20 focus:shadow-[0_0_20px_rgba(97,114,243,0.15)] transition-all duration-200 backdrop-blur"
                  placeholder="name@company.com"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative group">
                <Lock className="w-4 h-4 text-slate-400 group-focus-within:text-brand-400 absolute left-3.5 top-3.5 transition-colors" />
                <input
                  type="password"
                  name="finova-work-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  autoCorrect="off"
                  autoCapitalize="off"
                  spellCheck={false}
                  data-lpignore="true"
                  data-form-type="other"
                  data-1p-ignore="true"
                  onFocus={(e) => e.target.removeAttribute('readOnly')}
                  className="w-full bg-white/80 dark:bg-slate-900/50 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-slate-700/60 rounded-2xl pl-10 pr-3.5 py-3.5 text-xs placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-brand-500/50 focus:ring-2 focus:ring-brand-500/20 focus:shadow-[0_0_20px_rgba(97,114,243,0.15)] transition-all duration-200 backdrop-blur"
                  placeholder="••••••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="relative w-full py-3.5 text-sm font-bold rounded-2xl flex items-center justify-center gap-2 overflow-hidden bg-gradient-to-r from-brand-600 via-indigo-600 to-brand-500 hover:from-brand-500 hover:to-indigo-500 text-white shadow-xl shadow-brand-500/20 hover:shadow-brand-500/30 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 btn-shine group"
            >
              {/* Shimmer sweep */}
              <span
                className="absolute inset-0 pointer-events-none opacity-0 hover:opacity-100"
                style={{
                  background:
                    'linear-gradient(105deg, transparent 30%, rgba(255,255,255,0.18) 45%, rgba(255,255,255,0.25) 50%, transparent 65%)',
                  transform: 'translateX(-100%)',
                  animation: 'shimmer 2.6s ease-in-out infinite',
                }}
              />
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Console</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-7 pt-6 border-t border-slate-200/60 dark:border-white/10 relative">
            <div className="text-center text-xs text-slate-500 dark:text-slate-400">
              New organization?{' '}
              <Link to="/register" className="text-brand-600 dark:text-brand-400 hover:underline font-semibold">
                Create workspace account
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Keyframes */}
      <style>{`
        @keyframes float1 {
          0% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(-26px, 22px) scale(1.06); }
          100% { transform: translate(14px, -12px) scale(1); }
        }
        @keyframes float2 {
          0% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(20px, -18px) scale(1.05); }
          100% { transform: translate(-12px, 16px) scale(1); }
        }
        @keyframes float3 {
          0% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(-16px, -16px) scale(1.07); }
          100% { transform: translate(10px, 12px) scale(1); }
        }
        @keyframes auroraDrift {
          0% { transform: translateX(-50%) translateY(0) scale(1); opacity: 0.6; }
          100% { transform: translateX(-48%) translateY(10px) scale(1.04); opacity: 0.85; }
        }
        @keyframes logoFloat {
          0% { transform: translateY(0); }
          100% { transform: translateY(-4px); }
        }
        @keyframes shimmer {
          0% { transform: translateX(-120%) skewX(-12deg); }
          55% { transform: translateX(120%) skewX(-12deg); }
          100% { transform: translateX(120%) skewX(-12deg); }
        }
      `}</style>
    </div>
  )
}
