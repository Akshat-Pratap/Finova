import React, { useState } from 'react'
import {
  FileDown, Download, CheckCircle2, FileText, Table, Filter,
  Calendar, ShieldCheck, Sparkles, Layers
} from 'lucide-react'
import { exportReport } from '../api'

const REPORT_TYPES = [
  {
    id: 'RECONCILIATION',
    title: 'Reconciliation Results Ledger',
    desc: 'Matched, mismatch, duplicate, and AI investigated transactions with match scores and signal breakdowns.',
    icon: Table,
  },
  {
    id: 'EXCEPTIONS',
    title: 'Financial Exceptions & Triage',
    desc: 'Active discrepancies, human-in-the-loop assignments, notes, and audited ledger adjustments.',
    icon: FileText,
  },
  {
    id: 'AUDIT_LOG',
    title: 'Tamper-Evident Audit Trail',
    desc: 'Cryptographic SHA-256 hash-chained event timeline with immutable chronological event hashes.',
    icon: ShieldCheck,
  },
  {
    id: 'PROCESSING_RUN',
    title: 'Processing Runs Summary',
    desc: 'Batch processing runs performance, match rates, precision, recall, and F1 benchmarks.',
    icon: Layers,
  },
]

export default function Reports() {
  const [selectedType, setSelectedType] = useState('RECONCILIATION')
  const [selectedFormat, setSelectedFormat] = useState('CSV')
  const [downloading, setDownloading] = useState(false)
  const [successMsg, setSuccessMsg] = useState(null)

  const handleExport = async () => {
    setDownloading(true)
    setSuccessMsg(null)
    try {
      const blobData = await exportReport({
        report_type: selectedType,
        format: selectedFormat,
      })

      // Trigger automatic browser download
      const url = window.URL.createObjectURL(new Blob([blobData]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `finova_${selectedType.toLowerCase()}_report.${selectedFormat.toLowerCase()}`)
      document.body.appendChild(link)
      link.click()
      link.parentNode.removeChild(link)
      window.URL.revokeObjectURL(url)

      setSuccessMsg(`Successfully generated and exported ${selectedType} report as ${selectedFormat}.`)
    } catch (err) {
      console.error('Export failed:', err)
      setSuccessMsg(`Export failed: ${err.message}`)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="space-y-8 font-sans">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <FileDown className="w-6 h-6 text-indigo-400" />
          Financial Reports & Data Exports
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Export standardized financial statements, exceptions registers, and tamper-evident audit packages for compliance and audits.
        </p>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-950/40 border border-emerald-800/60 rounded-xl flex items-center space-x-3 text-emerald-300 text-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Report Selection Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {REPORT_TYPES.map((type) => {
          const Icon = type.icon
          const isSelected = selectedType === type.id
          return (
            <div
              key={type.id}
              onClick={() => setSelectedType(type.id)}
              className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                isSelected
                  ? 'bg-slate-900 border-indigo-500 ring-2 ring-indigo-500/20 shadow-xl'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/80'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className={`p-2.5 rounded-xl ${isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <input
                  type="radio"
                  name="reportType"
                  checked={isSelected}
                  onChange={() => setSelectedType(type.id)}
                  className="mt-1 text-indigo-600 focus:ring-indigo-500"
                />
              </div>
              <h3 className="text-sm font-bold text-white">{type.title}</h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">{type.desc}</p>
            </div>
          )
        })}
      </div>

      {/* Format & Download Controls */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Export Format
            </label>
            <div className="flex items-center space-x-3">
              {['CSV', 'JSON'].map((fmt) => (
                <button
                  key={fmt}
                  type="button"
                  onClick={() => setSelectedFormat(fmt)}
                  className={`flex-1 py-3 px-4 rounded-xl text-xs font-bold border transition-all ${
                    selectedFormat === fmt
                      ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-600/30'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  {fmt} Document (.{fmt.toLowerCase()})
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col justify-end">
            <button
              onClick={handleExport}
              disabled={downloading}
              className="w-full py-3.5 px-6 rounded-xl text-sm font-bold text-white bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 shadow-xl shadow-indigo-600/30 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              <span>{downloading ? 'Preparing Financial Export...' : `Download ${selectedFormat} Export`}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
