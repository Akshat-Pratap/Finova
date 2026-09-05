import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Layers, Plus, CheckCircle2, AlertCircle, RefreshCw, Key, ArrowRight,
  ShieldCheck, Trash2, Activity, Play, Zap, ExternalLink, Globe,
  Copy, Check
} from 'lucide-react'
import { listIntegrations, connectIntegration, testIntegration, syncIntegration, disconnectIntegration } from '../api'
import { PageContainer, PageHeader, GlassCard, Button, Alert, Modal } from '../components/ui'

export default function Integrations() {
  const [integrations, setIntegrations] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [keyId, setKeyId] = useState('rzp_test_finova2026')
  const [keySecret, setKeySecret] = useState('secret_finova_demo_key_9988')
  const [syncingId, setSyncingId] = useState(null)
  const [testingId, setTestingId] = useState(null)
  const [notification, setNotification] = useState(null)
  const [copiedWebhook, setCopiedWebhook] = useState(false)
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
        setNotification({ type: 'success', title: 'Provider Connected', message: res.message || 'Razorpay gateway connected successfully.' })
        setModalOpen(false)
        fetchIntegrations()
      }
    } catch (err) {
      setNotification({ type: 'error', title: 'Connection Failed', message: err.message || 'Unable to authenticate provider credentials.' })
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
        title: res.success ? 'Connection Test Passed' : 'Connection Test Failed',
        message: res.message || 'Provider API test completed.',
      })
    } catch (err) {
      setNotification({ type: 'error', title: 'Test Failed', message: err.message || 'Connection test failed.' })
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
          title: 'Sync & Reconciliation Completed',
          message: `Imported ${res.payments_imported} payments and reconciled against invoices (${(res.match_rate * 100).toFixed(1)}% match rate).`,
        })
        fetchIntegrations()
        setTimeout(() => {
          navigate(`/reconciliation?run_id=${res.run_id}`)
        }, 1500)
      }
    } catch (err) {
      setNotification({ type: 'error', title: 'Sync Error', message: err.message || 'Sync failed.' })
    } finally {
      setSyncingId(null)
    }
  }

  const handleDisconnect = async (id) => {
    if (!confirm('Are you sure you want to disconnect this payment provider?')) return
    try {
      await disconnectIntegration(id)
      setNotification({ type: 'success', title: 'Disconnected', message: 'Provider has been disconnected.' })
      fetchIntegrations()
    } catch (err) {
      setNotification({ type: 'error', title: 'Error', message: err.message || 'Disconnect failed.' })
    }
  }

  const copyWebhook = () => {
    navigator.clipboard.writeText('https://api.finova.ai/v1/webhooks/razorpay/sync')
    setCopiedWebhook(true)
    setTimeout(() => setCopiedWebhook(false), 2000)
  }

  return (
    <PageContainer>
      <PageHeader
        title="Payment Gateway & Bank Integrations"
        subtitle="Connect payment processors, merchant settlement feeds, and core banking webhooks for automated financial ingestion."
        icon={Layers}
        actions={
          <Button
            variant="primary"
            size="sm"
            onClick={() => setModalOpen(true)}
            icon={Plus}
          >
            Connect Provider
          </Button>
        }
      />

      {notification && (
        <Alert
          type={notification.type}
          title={notification.title}
          message={notification.message}
          dismissible
          onDismiss={() => setNotification(null)}
        />
      )}

      {/* Connected Providers List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Active Razorpay Card */}
        <GlassCard className="p-6 space-y-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3.5">
              <div className="w-12 h-12 bg-blue-600/15 border border-blue-500/30 rounded-2xl flex items-center justify-center font-black text-blue-600 dark:text-blue-400 text-xl shadow-inner">
                R
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">Razorpay Payment Gateway</h3>
                  <span className="bg-blue-500/10 border border-blue-500/30 text-blue-600 dark:text-blue-400 text-[10px] font-bold px-2 py-0.5 rounded-full">
                    LIVE FEED
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">UPI, Cards, Netbanking & Automated Settlement Payouts</p>
              </div>
            </div>

            <div className="flex items-center space-x-1.5 bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 rounded-full text-emerald-600 dark:text-emerald-400 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Connected</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 py-3 border-y border-slate-200 dark:border-dark-700 text-xs">
            <div>
              <span className="text-slate-400 dark:text-slate-500 text-[10px] font-semibold uppercase tracking-wider">Masked API Key</span>
              <div className="font-mono text-slate-800 dark:text-slate-200 font-medium mt-0.5">rzp_test_••••••••</div>
            </div>
            <div>
              <span className="text-slate-400 dark:text-slate-500 text-[10px] font-semibold uppercase tracking-wider">Sync Cadence</span>
              <div className="text-slate-800 dark:text-slate-200 font-medium mt-0.5">Real-time / On-Demand</div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleTest('int_razorpay')}
                loading={testingId === 'int_razorpay'}
                icon={Activity}
              >
                Test Ping
              </Button>

              <Button
                variant="primary"
                size="sm"
                onClick={() => handleSync('int_razorpay')}
                loading={syncingId === 'int_razorpay'}
                icon={RefreshCw}
              >
                {syncingId === 'int_razorpay' ? 'Syncing...' : 'Sync & Reconcile'}
              </Button>
            </div>

            <button
              onClick={() => handleDisconnect('int_razorpay')}
              className="text-slate-400 hover:text-rose-500 dark:text-slate-500 dark:hover:text-rose-400 p-2 rounded-lg transition-colors"
              title="Disconnect Integration"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </GlassCard>

        {/* Stripe Preview Card */}
        <GlassCard className="p-6 space-y-4 border-dashed flex flex-col justify-between opacity-85">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3.5">
              <div className="w-12 h-12 bg-purple-600/15 border border-purple-500/30 rounded-2xl flex items-center justify-center font-black text-purple-600 dark:text-purple-400 text-xl shadow-inner">
                S
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">Stripe Global Settlements</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Multi-currency USD, EUR, GBP settlement reconciliation</p>
              </div>
            </div>
            <span className="text-[10px] bg-slate-100 dark:bg-dark-800 text-slate-600 dark:text-slate-400 px-2.5 py-1 rounded-full border border-slate-200 dark:border-dark-700 font-semibold">
              Available
            </span>
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            Automate international cross-border payment matching, foreign exchange fee variance analysis, and instant chargeback tracking.
          </p>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setModalOpen(true)}
            className="w-full"
          >
            Configure Stripe Feed
          </Button>
        </GlassCard>
      </div>

      {/* Webhook Endpoint Reference Card */}
      <GlassCard className="p-6">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1 flex items-center gap-2">
          <Globe className="w-4 h-4 text-brand-500" />
          Enterprise Ingestion Webhooks
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
          Configure real-time event webhooks in your payment processor or ERP console to stream settlement events directly into Finova.
        </p>

        <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-dark-900 rounded-xl border border-slate-200 dark:border-dark-700">
          <div className="font-mono text-xs text-slate-700 dark:text-slate-300 truncate mr-3">
            https://api.finova.ai/v1/webhooks/razorpay/sync
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={copyWebhook}
            icon={copiedWebhook ? Check : Copy}
          >
            {copiedWebhook ? 'Copied' : 'Copy URL'}
          </Button>
        </div>
      </GlassCard>

      {/* Connect Modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Connect Payment Gateway"
        size="md"
      >
        <form onSubmit={handleConnect} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">
              Razorpay Key ID
            </label>
            <input
              type="text"
              required
              value={keyId}
              onChange={(e) => setKeyId(e.target.value)}
              className="input text-xs w-full"
              placeholder="rzp_test_..."
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">
              Razorpay Key Secret
            </label>
            <input
              type="password"
              required
              value={keySecret}
              onChange={(e) => setKeySecret(e.target.value)}
              className="input text-xs w-full"
              placeholder="••••••••••••••••"
            />
          </div>

          <div className="p-3 bg-brand-500/10 border border-brand-500/20 rounded-xl text-xs text-brand-600 dark:text-brand-300">
            Credentials are encrypted in transit with TLS 1.3 and stored with AES-256 envelope encryption. Secrets are never returned to client apps.
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              variant="secondary"
              type="button"
              onClick={() => setModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              loading={loading}
            >
              Authenticate & Connect
            </Button>
          </div>
        </form>
      </Modal>
    </PageContainer>
  )
}
