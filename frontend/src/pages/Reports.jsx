import React, { useState } from 'react'
import {
  FileDown, Download, CheckCircle2, FileText, Table, Filter,
  Calendar, ShieldCheck, Sparkles, Layers, FileSpreadsheet,
  Check, AlertCircle
} from 'lucide-react'
import { exportReport } from '../api'
import { PageContainer, PageHeader, GlassCard, Button, Alert } from '../components/ui'

const REPORT_TYPES = [
  {
    id: 'RECONCILIATION',
    title: 'Reconciliation Results Ledger',
    desc: 'Complete ledger of matched, mismatch, duplicate, and AI investigated transactions with match scores and signal breakdowns.',
    icon: Table,
    tag: 'Primary Financial Ledger',
  },
  {
    id: 'EXCEPTIONS',
    title: 'Financial Exceptions & Triage Register',
    desc: 'Active discrepancies, human-in-the-loop assignments, collaboration notes, and audited manual financial adjustments.',
    icon: FileText,
    tag: 'Compliance & Audit',
  },
  {
    id: 'AUDIT_LOG',
    title: 'Tamper-Evident Audit Trail Package',
    desc: 'Cryptographic SHA-256 hash-chained event timeline with immutable chronological parent hashes for SOX/SOC2 compliance.',
    icon: ShieldCheck,
    tag: 'Cryptographic Proof',
  },
  {
    id: 'PROCESSING_RUN',
    title: 'Processing Runs Summary & Benchmarks',
    desc: 'Batch processing runs performance, throughput rates, match rates, precision, recall, and ML F1 benchmarks.',
    icon: Layers,
    tag: 'Performance Analytics',
  },
]

export default function Reports() {
  const [selectedType, setSelectedType] = useState('RECONCILIATION')
  const [selectedFormat, setSelectedFormat] = useState('CSV')
  const [downloading, setDownloading] = useState(false)
  const [notification, setNotification] = useState(null)

  const handleExport = async () => {
    setDownloading(true)
    setNotification(null)
    try {
      const blobData = await exportReport({
        report_type: selectedType,
        format: selectedFormat,
      })

      // Trigger browser file download
      const url = window.URL.createObjectURL(new Blob([blobData]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `finova_${selectedType.toLowerCase()}_report.${selectedFormat.toLowerCase()}`)
      document.body.appendChild(link)
      link.click()
      link.parentNode.removeChild(link)
      window.URL.revokeObjectURL(url)

      setNotification({
        type: 'success',
        title: 'Export Successful',
        message: `Successfully generated and downloaded ${selectedType} report as .${selectedFormat.toLowerCase()}`,
      })
    } catch (err) {
      console.error('Export failed:', err)
      setNotification({
        type: 'error',
        title: 'Export Failed',
        message: err.message || 'Unable to generate export report.',
      })
    } finally {
      setDownloading(false)
    }
  }

  return (
    <PageContainer>
      <PageHeader
        title="Financial Reports & Data Exports"
        subtitle="Export standardized financial statements, exception registers, and tamper-evident audit packages for compliance and audit sign-off."
        icon={FileDown}
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

      {/* Report Selection Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {REPORT_TYPES.map((type) => {
          const Icon = type.icon
          const isSelected = selectedType === type.id
          return (
            <div
              key={type.id}
              onClick={() => setSelectedType(type.id)}
              className={`p-5 rounded-2xl border cursor-pointer transition-all duration-200 ${
                isSelected
                  ? 'bg-brand-500/10 dark:bg-brand-500/15 border-brand-500 ring-2 ring-brand-500/30 shadow-lg shadow-brand-500/10'
                  : 'bg-white/70 dark:bg-dark-900/60 border-slate-200/80 dark:border-dark-700/80 hover:border-brand-400 dark:hover:border-dark-600 hover:bg-white dark:hover:bg-dark-800/80'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className={`p-3 rounded-xl transition-colors ${
                  isSelected
                    ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                    : 'bg-slate-100 dark:bg-dark-800 text-slate-500 dark:text-slate-400'
                }`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-dark-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-dark-700">
                    {type.tag}
                  </span>
                  <div className={`w-5 h-5 rounded-full border flex items-center justify-center transition-colors ${
                    isSelected
                      ? 'border-brand-500 bg-brand-600 text-white'
                      : 'border-slate-300 dark:border-dark-600 bg-transparent'
                  }`}>
                    {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                  </div>
                </div>
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">{type.title}</h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">{type.desc}</p>
            </div>
          )
        })}
      </div>

      {/* Format & Download Controls Card */}
      <GlassCard className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2.5">
              Select Export Format
            </label>
            <div className="grid grid-cols-2 gap-3">
              {[
                { id: 'CSV', label: 'CSV Spreadsheet', desc: 'Standard Comma-Separated Values (.csv)', icon: FileSpreadsheet },
                { id: 'JSON', label: 'JSON Dataset', desc: 'Raw Structured Ledger Objects (.json)', icon: FileText },
              ].map((fmt) => {
                const FmtIcon = fmt.icon
                const isSelected = selectedFormat === fmt.id
                return (
                  <button
                    key={fmt.id}
                    type="button"
                    onClick={() => setSelectedFormat(fmt.id)}
                    className={`p-3.5 rounded-xl text-left border transition-all ${
                      isSelected
                        ? 'bg-brand-600 text-white border-brand-500 shadow-md shadow-brand-600/25'
                        : 'bg-slate-50 dark:bg-dark-800/80 border-slate-200 dark:border-dark-700 text-slate-700 dark:text-slate-300 hover:border-slate-300 dark:hover:border-dark-600'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <FmtIcon className="w-4 h-4" />
                      <span className="text-xs font-bold">{fmt.label}</span>
                    </div>
                    <p className={`text-[11px] leading-tight ${isSelected ? 'text-white/80' : 'text-slate-500 dark:text-slate-400'}`}>
                      {fmt.desc}
                    </p>
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <Button
              variant="primary"
              size="lg"
              onClick={handleExport}
              loading={downloading}
              icon={Download}
              className="w-full py-4 text-sm font-bold shadow-xl shadow-brand-500/25"
            >
              {downloading ? 'Compiling Financial Data...' : `Download ${selectedFormat} Export`}
            </Button>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 text-center mt-2">
              Generated reports include digital integrity checksums and timestamps.
            </p>
          </div>
        </div>
      </GlassCard>
    </PageContainer>
  )
}
