import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload, FileText, CheckCircle2, AlertTriangle, XCircle, ArrowRight,
  RefreshCw, Database, Layers, Sparkles, Filter, ChevronRight
} from 'lucide-react'
import { uploadDataset, listDatasets, validateDataset, generateDataset } from '../api'

const CANONICAL_TARGETS = [
  { key: 'transaction_id', label: 'Transaction ID (Required)' },
  { key: 'reference_id', label: 'Reference / UTR / RRN' },
  { key: 'customer_id', label: 'Customer ID / Payer' },
  { key: 'amount', label: 'Amount (Required)' },
  { key: 'currency', label: 'Currency' },
  { key: 'timestamp', label: 'Transaction Date / Time' },
  { key: 'invoice_id', label: 'Invoice ID' },
  { key: 'description', label: 'Description / Narration' },
]

export default function Datasets() {
  const [datasets, setDatasets] = useState([])
  const [loading, setLoading] = useState(false)
  const [activeDataset, setActiveDataset] = useState(null)
  const [columnMapping, setColumnMapping] = useState({})
  const [sampleRows, setSampleRows] = useState([])
  const [validationReport, setValidationReport] = useState(null)
  const [validating, setValidating] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const fileInputRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchDatasets()
  }, [])

  const fetchDatasets = async () => {
    try {
      const res = await listDatasets()
      if (res.success) {
        setDatasets(res.datasets || [])
      }
    } catch (err) {
      console.warn('Failed to load datasets:', err.message)
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setUploadError(null)
    setValidationReport(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await uploadDataset(formData)
      if (res.success) {
        setActiveDataset(res)
        setColumnMapping(res.detected_mapping || {})
        setSampleRows(res.sample_rows || [])
        fetchDatasets()
      }
    } catch (err) {
      setUploadError(err.message || 'File upload failed')
    } finally {
      setLoading(false)
    }
  }

  const handleMappingChange = (rawCol, canonicalTarget) => {
    setColumnMapping(prev => ({
      ...prev,
      [rawCol]: canonicalTarget || undefined
    }))
  }

  const handleRunValidation = async () => {
    if (!activeDataset) return
    setValidating(true)
    try {
      const res = await validateDataset(activeDataset.dataset_id, columnMapping)
      if (res.success) {
        setValidationReport(res.validation_report)
        fetchDatasets()
      }
    } catch (err) {
      setUploadError(err.message || 'Validation failed')
    } finally {
      setValidating(false)
    }
  }

  const handleStartReconciliation = () => {
    if (!activeDataset) return
    navigate(`/reconciliation?dataset_id=${activeDataset.dataset_id}`)
  }

  const handleGenerateSynthetic = async () => {
    setLoading(true)
    try {
      const res = await generateDataset({ num_records: 250 })
      if (res.success) {
        navigate(`/reconciliation?run_id=${res.run_id}`)
      }
    } catch (err) {
      setUploadError(err.message || 'Synthetic generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Database className="w-6 h-6 text-indigo-400" />
            Data Ingestion & Dataset Lifecycle
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Upload CSV/JSON statement files, configure intelligent column mappings, and preview data hygiene.
          </p>
        </div>

        <button
          onClick={handleGenerateSynthetic}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-indigo-300 bg-indigo-950/60 hover:bg-indigo-900/60 border border-indigo-700/50 transition-all shadow-sm"
        >
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <span>Generate 250-Row Sandbox Dataset</span>
        </button>
      </div>

      {uploadError && (
        <div className="p-4 bg-red-950/40 border border-red-800/60 rounded-xl flex items-center space-x-3 text-red-300 text-sm">
          <XCircle className="w-5 h-5 shrink-0 text-red-400" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Upload Dropzone */}
      <div className="bg-slate-900/70 border border-dashed border-slate-700/80 hover:border-indigo-500/80 rounded-2xl p-8 text-center transition-all bg-gradient-to-b from-slate-900/50 to-slate-950/50">
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json"
          className="hidden"
          onChange={handleFileUpload}
        />
        <div className="w-14 h-14 bg-indigo-950/80 border border-indigo-800/50 rounded-2xl flex items-center justify-center mx-auto mb-4 text-indigo-400 shadow-lg shadow-indigo-900/20">
          <Upload className="w-7 h-7" />
        </div>
        <h3 className="text-base font-semibold text-white">
          Upload Transaction CSV or JSON File
        </h3>
        <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
          Supports Bank feeds, Payment Provider exports, Gateway statements, and ERP ledgers up to 1GB.
        </p>

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          className="mt-5 px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 transition-colors shadow-md shadow-indigo-600/30 inline-flex items-center space-x-2"
        >
          <FileText className="w-4 h-4" />
          <span>{loading ? 'Parsing Dataset...' : 'Select File from Computer'}</span>
        </button>
      </div>

      {/* Column Mapping & Validation Section */}
      {activeDataset && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-2">
            <div>
              <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Active Ingestion</span>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-slate-400" />
                {activeDataset.filename}
                <span className="text-xs font-normal text-slate-400 bg-slate-800 px-2 py-0.5 rounded-md">
                  {activeDataset.record_count} rows parsed
                </span>
              </h2>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={handleRunValidation}
                disabled={validating}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-colors flex items-center space-x-2"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${validating ? 'animate-spin' : ''}`} />
                <span>{validating ? 'Validating...' : 'Re-Validate Mapping'}</span>
              </button>

              {validationReport?.ready_for_processing && (
                <button
                  onClick={handleStartReconciliation}
                  className="px-5 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-700/25 flex items-center space-x-2 transition-all"
                >
                  <span>Reconcile Dataset</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Mapping Grid */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              Column Semantic Alignment
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.keys(sampleRows[0] || {}).filter(k => !k.startsWith('_')).map((rawCol) => (
                <div key={rawCol} className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-indigo-300 font-medium truncate max-w-[140px]" title={rawCol}>
                      {rawCol}
                    </span>
                    <span className="text-[10px] text-slate-500">Raw Header</span>
                  </div>
                  <select
                    value={columnMapping[rawCol] || ''}
                    onChange={(e) => handleMappingChange(rawCol, e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  >
                    <option value="">-- Ignore / Unmapped --</option>
                    {CANONICAL_TARGETS.map(t => (
                      <option key={t.key} value={t.key}>{t.label}</option>
                    ))}
                  </select>
                  <p className="text-[11px] text-slate-500 truncate">
                    Sample: {String(sampleRows[0]?.[rawCol] ?? 'null')}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Validation Report Preview */}
          {validationReport && (
            <div className="p-5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-4">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Pre-Validation Hygiene Report
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
                  <div className="text-[10px] text-slate-400 uppercase">Valid Records</div>
                  <div className="text-xl font-bold text-emerald-400">{validationReport.valid_count}</div>
                </div>
                <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
                  <div className="text-[10px] text-slate-400 uppercase">Invalid Rows</div>
                  <div className="text-xl font-bold text-red-400">{validationReport.invalid_count}</div>
                </div>
                <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
                  <div className="text-[10px] text-slate-400 uppercase">Duplicates Detected</div>
                  <div className="text-xl font-bold text-amber-400">{validationReport.duplicates_detected}</div>
                </div>
                <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl">
                  <div className="text-[10px] text-slate-400 uppercase">Ready Status</div>
                  <div className="text-sm font-bold text-indigo-300 mt-1">
                    {validationReport.ready_for_processing ? 'VALIDATED' : 'ACTION REQUIRED'}
                  </div>
                </div>
              </div>

              {validationReport.validation_errors?.length > 0 && (
                <div className="mt-3 p-3 bg-red-950/30 border border-red-900/40 rounded-xl space-y-1">
                  <div className="text-xs font-semibold text-red-400">Row Hygiene Diagnostics:</div>
                  <ul className="text-xs text-red-300/90 list-disc list-inside space-y-0.5 max-h-32 overflow-y-auto">
                    {validationReport.validation_errors.slice(0, 10).map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Dataset History Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Database className="w-5 h-5 text-indigo-400" />
          Ingested Datasets Repository
        </h3>

        {datasets.length === 0 ? (
          <div className="text-center py-10 text-slate-500 text-xs">
            No dataset files uploaded yet. Upload a CSV or JSON file to begin.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] text-slate-400 uppercase bg-slate-950/60 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Records</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Uploaded</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {datasets.map((ds) => (
                  <tr key={ds.dataset_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-400" />
                      {ds.filename}
                    </td>
                    <td className="py-3 px-4 uppercase text-slate-400">{ds.source_type}</td>
                    <td className="py-3 px-4 font-mono">{ds.record_count}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        ds.processing_status === 'COMPLETED' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                        ds.processing_status === 'VALIDATED' ? 'bg-indigo-950 text-indigo-400 border border-indigo-800' :
                        ds.processing_status === 'FAILED' ? 'bg-red-950 text-red-400 border border-red-800' :
                        'bg-slate-800 text-slate-400'
                      }`}>
                        {ds.processing_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(ds.uploaded_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => navigate(`/reconciliation?dataset_id=${ds.dataset_id}`)}
                        className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1"
                      >
                        <span>Reconcile</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
