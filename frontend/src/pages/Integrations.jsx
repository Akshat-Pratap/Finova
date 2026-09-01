import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Layers, Plus, CheckCircle2, AlertCircle, RefreshCw, Key, ArrowRight,
  ShieldCheck, Trash2, Activity, Play, Zap, ExternalLink
} from 'lucide-react'
import { listIntegrations, connectIntegration, testIntegration, syncIntegration, disconnectIntegration } from '../api'

export default function Integrations() {
  const [integrations, setIntegrations] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [keyId, setKeyId] = useState('rzp_test_finova2026')
  const [keySecret, setKeySecret] = useState('secret_finova_demo_key_9988')
  const [syncingId, setSyncingId] = useState(null)
  const [testingId, setTestingId] = useState(null)
  const [notification, setNotification] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchIntegrations()
  }, [])

  const fetchIntegrations = async () => {
    try {
      const res = await listIntegrations()
      if (res.success) {
        setIntegrations(res.integrations || [])
      }
    } catch (err) {
      console.warn('Failed to fetch integrations:', err.message)
    }
  }

  const handleConnect = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await connectIntegration({
        provider: 'RAZORPAY',
        key_id: keyId,
        key_secret: keySecret,
      })
      if (res.success) {
        setNotification({ type: 'success', message: res.message || 'Razorpay connected successfully.' })
        setModalOpen(false)
        fetchIntegrations()
      }
    } catch (err) {
      setNotification({ type: 'error', message: err.message || 'Connection failed.' })
    } finally {
      setLoading(false)
    }
  }

  const handleTest = async (id) => {
    setTestingId(id)
    try {
      const res = await testIntegration(id)
      setNotification({
        type: res.success ? 'success' : 'error',
        message: res.message || 'Test complete.',
      })
    } catch (err) {
      setNotification({ type: 'error', message: err.message || 'Connection test failed.' })
    } finally {
      setTestingId(null)
    }
  }

  const handleSync = async (id) => {
    setSyncingId(id)
    try {
      const res = await syncIntegration(id, 50)
      if (res.success) {
        setNotification({
          type: 'success',
          message: `Synced ${res.payments_imported} payments! Matched ${res.records_matched} records (${(res.match_rate * 100).toFixed(1)}% match rate).`,
        })
        fetchIntegrations()
        setTimeout(() => {
          navigate(`/reconciliation?run_id=${res.run_id}`)
        }, 1500)
      }
    } catch (err) {
      setNotification({ type: 'error', message: err.message || 'Sync failed.' })
    } finally {
      setSyncingId(null)
    }
  }

  const handleDisconnect = async (id) => {
    if (!confirm('Are you sure you want to disconnect this provider?')) return
    try {
      await disconnectIntegration(id)
      setNotification({ type: 'success', message: 'Integration disconnected.' })
      fetchIntegrations()
    } catch (err) {
      setNotification({ type: 'error', message: err.message || 'Disconnect failed.' })
    }
  }

  return (
    <div className="space-y-8 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Layers className="w-6 h-6 text-indigo-400" />
            Payment Gateway & Bank Integrations
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Connect live payment processors, merchant settlement feeds, and ERP webhooks for automated ingestion.
          </p>
        </div>

        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center space-x-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 transition-all shadow-lg shadow-indigo-600/25"
        >
          <Plus className="w-4 h-4" />
          <span>Connect Provider</span>
        </button>
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

      {/* Connected Providers List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Active Razorpay Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-5 shadow-xl relative overflow-hidden">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-blue-950/80 border border-blue-800/60 rounded-xl flex items-center justify-center font-bold text-blue-400 text-lg">
                R
              </div>
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  Razorpay Payment Gateway
                  <span className="bg-blue-950 border border-blue-800 text-blue-300 text-[10px] font-semibold px-2 py-0.5 rounded-full">
                    LIVE / SANDBOX
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Automated UPI, Cards, Netbanking & Settlement Payouts</p>
              </div>
            </div>

            <div className="flex items-center space-x-1.5 bg-emerald-950/60 border border-emerald-800/60 px-2.5 py-1 rounded-full text-emerald-400 text-[11px] font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Ready</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 py-3 border-y border-slate-800/80 text-xs">
            <div>
              <span className="text-slate-500 text-[10px] uppercase">API Key</span>
              <div className="font-mono text-slate-300 mt-0.5">rzp_test_••••••••</div>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] uppercase">Sync Cadence</span>
              <div className="text-slate-300 mt-0.5">On-Demand / Real-time</div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleTest('int_razorpay')}
                disabled={testingId === 'int_razorpay'}
                className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 transition-colors flex items-center space-x-1.5"
              >
                <Activity className={`w-3.5 h-3.5 ${testingId === 'int_razorpay' ? 'animate-spin' : ''}`} />
                <span>Test Ping</span>
              </button>

              <button
                onClick={() => handleSync('int_razorpay')}
                disabled={syncingId === 'int_razorpay'}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-md shadow-indigo-600/30 transition-all flex items-center space-x-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${syncingId === 'int_razorpay' ? 'animate-spin' : ''}`} />
                <span>{syncingId === 'int_razorpay' ? 'Importing...' : 'Sync & Reconcile'}</span>
              </button>
            </div>

            <button
              onClick={() => handleDisconnect('int_razorpay')}
              className="text-slate-500 hover:text-red-400 text-xs p-2 transition-colors"
              title="Disconnect Integration"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Stripe Card (Preview) */}
        <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-6 space-y-4 text-slate-500 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-slate-800/50 rounded-xl flex items-center justify-center font-bold text-slate-400 text-lg">
                S
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-300">Stripe Connect & Global Payouts</h3>
                <p className="text-xs text-slate-500 mt-0.5">Multi-currency USD, EUR, GBP settlement reconciliation</p>
              </div>
            </div>
            <span className="text-[10px] bg-slate-800 px-2.5 py-1 rounded-full text-slate-400">Available</span>
          </div>

          <p className="text-xs text-slate-400">
            Automate international cross-border payment matching and multi-currency foreign exchange reconciliation.
          </p>

          <button
            onClick={() => setModalOpen(true)}
            className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-colors"
          >
            Configure Stripe Feed
          </button>
        </div>
      </div>

      {/* Connect Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-indigo-400" />
                Connect Razorpay Gateway
              </h3>
              <button onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleConnect} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Razorpay Key ID
                </label>
                <input
                  type="text"
                  required
                  value={keyId}
                  onChange={(e) => setKeyId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-600 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  placeholder="rzp_test_..."
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Razorpay Key Secret
                </label>
                <input
                  type="password"
                  required
                  value={keySecret}
                  onChange={(e) => setKeySecret(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-600 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  placeholder="••••••••••••••••"
                />
              </div>

              <div className="p-3 bg-indigo-950/40 border border-indigo-900/40 rounded-xl text-[11px] text-indigo-300">
                Credentials are encrypted in transit and masked in audit storage.
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-md shadow-indigo-600/30"
                >
                  {loading ? 'Authenticating...' : 'Connect Provider'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
