import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload, FileText, CheckCircle2, AlertTriangle, XCircle, ArrowRight,
  RefreshCw, Database, Layers, Sparkles, Filter, ChevronRight, Trash2, Check
} from 'lucide-react'
import { uploadDataset, listDatasets, validateDataset, generateDataset, deleteDataset } from '../api'
import {
  PageContainer, PageHeader, GlassCard, Button, StatusBadge,
  Alert, Spinner, EmptyState, ConfirmationDialog
} from '../components/ui'

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
  const [deletingDataset, setDeletingDataset] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [uploadSuccess, setUploadSuccess] = useState(null)
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

  const handleDeleteConfirm = async () => {
    if (!deletingDataset) return
    setDeleting(true)
    try {
      const res = await deleteDataset(deletingDataset.dataset_id)
      if (res.success) {
        if (activeDataset?.dataset_id === deletingDataset.dataset_id) {
          setActiveDataset(null)
          setColumnMapping({})
          setSampleRows([])
          setValidationReport(null)
        }
        setUploadSuccess(`Dataset '${deletingDataset.filename}' was deleted from MongoDB Atlas.`)
        await fetchDatasets()
      }
    } catch (err) {
      setUploadError(err.message || 'Failed to delete dataset')
    } finally {
      setDeleting(false)
      setDeletingDataset(null)
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setUploadError(null)
    setUploadSuccess(null)
    setValidationReport(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await uploadDataset(formData)
      if (res.success) {
        setActiveDataset(res)
        setColumnMapping(res.detected_mapping || {})
        setSampleRows(res.sample_rows || [])
        setUploadSuccess(`Successfully ingested '${res.filename}' with ${res.record_count?.toLocaleString()} records.`)
        fetchDatasets()
      }
    } catch (err) {
      setUploadError(err.message || 'File upload failed')
    } finally {
      setLoading(false)
    }
  }

  const handleMappingChange = (rawCol, canonicalTarget) => {
    setColumnMapping((prev) => ({
      ...prev,
      [rawCol]: canonicalTarget || undefined,
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
    <PageContainer>
      {/* Header */}
      <PageHeader
        title="Data Ingestion & Dataset Lifecycle"
        subtitle="Upload statement CSV/JSON files, inspect data hygiene, and map financial schemas."
        icon={Database}
        actions={
          <Button
            variant="outline"
            onClick={handleGenerateSynthetic}
            disabled={loading}
            icon={Sparkles}
          >
            Generate Sandbox Dataset (250 Rows)
          </Button>
        }
      />

      {/* Alerts */}
      {uploadError && <Alert type="error" message={uploadError} onDismiss={() => setUploadError(null)} />}
      {uploadSuccess && <Alert type="success" message={uploadSuccess} onDismiss={() => setUploadSuccess(null)} />}

      {/* Upload Dropzone */}
      <GlassCard className="p-8 text-center border-dashed border-2 border-slate-700/80 dark:border-slate-700/80 light:border-slate-300 hover:border-brand-500/80 transition-all">
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json"
          className="hidden"
          onChange={handleFileUpload}
        />
        <div className="w-14 h-14 bg-brand-500/10 dark:bg-brand-500/10 light:bg-brand-50 border border-brand-500/30 rounded-2xl flex items-center justify-center mx-auto mb-3 text-brand-400 shadow-md">
          <Upload className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-slate-100 dark:text-slate-100 light:text-slate-900">
          Upload Financial Statement or Transaction Dataset
        </h3>
        <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-500 mt-1 max-w-sm mx-auto">
          Supports Bank CSV feeds, Payment Provider statements, Gateway exports, and ERP ledgers up to 1GB.
        </p>

        <Button
          variant="primary"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          loading={loading}
          icon={FileText}
          className="mt-4"
        >
          Select CSV or JSON File
        </Button>
      </GlassCard>

      {/* Active Dataset Mapping & Validation Section */}
      {activeDataset && (
        <GlassCard className="p-6 space-y-6 animate-slide-up">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800/80 dark:border-slate-800/80 light:border-slate-200 gap-3">
            <div>
              <span className="text-[10px] font-bold text-brand-400 uppercase tracking-wider">Active Ingestion</span>
              <h2 className="text-base font-bold text-slate-100 dark:text-slate-100 light:text-slate-900 flex items-center gap-2 mt-0.5">
                <FileText className="w-4 h-4 text-slate-400" />
                {activeDataset.filename}
                <span className="text-xs font-mono px-2 py-0.2 rounded-md bg-slate-800 text-slate-300">
                  {activeDataset.record_count?.toLocaleString()} rows
                </span>
              </h2>
            </div>

            <div className="flex items-center gap-2.5 flex-wrap">
              <Button
                variant="danger"
                size="sm"
                onClick={() => setDeletingDataset(activeDataset)}
                icon={Trash2}
              >
                Delete
              </Button>

              <Button
                variant="secondary"
                size="sm"
                onClick={handleRunValidation}
                loading={validating}
                icon={RefreshCw}
              >
                Validate Mapping
              </Button>

              {validationReport?.ready_for_processing && (
                <Button
                  variant="success"
                  size="sm"
                  onClick={handleStartReconciliation}
                  icon={ArrowRight}
                >
                  Reconcile Dataset
                </Button>
              )}
            </div>
          </div>

          {/* Mapping Grid */}
          <div>
            <h3 className="text-xs font-bold text-slate-300 dark:text-slate-300 light:text-slate-700 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-brand-400" />
              Column Semantic Alignment
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.keys(sampleRows[0] || {}).filter((k) => !k.startsWith('_')).map((rawCol) => (
                <div key={rawCol} className="p-3.5 bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-100 border border-slate-800/80 dark:border-slate-800/80 light:border-slate-300 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-brand-300 dark:text-brand-300 light:text-brand-700 truncate max-w-[140px]" title={rawCol}>
                      {rawCol}
                    </span>
                    <span className="text-[10px] text-slate-400">Raw Header</span>
                  </div>
                  <select
                    value={columnMapping[rawCol] || ''}
                    onChange={(e) => handleMappingChange(rawCol, e.target.value)}
                    className="select py-1 text-xs"
                  >
                    <option value="">-- Ignore / Unmapped --</option>
                    {CANONICAL_TARGETS.map((t) => (
                      <option key={t.key} value={t.key}>{t.label}</option>
                    ))}
                  </select>
                  <p className="text-[11px] text-slate-400 truncate">
                    Sample: {String(sampleRows[0]?.[rawCol] ?? 'null')}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Validation Report */}
          {validationReport && (
            <div className="p-4 bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-100 border border-slate-800 rounded-xl space-y-3">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Data Hygiene & Validation Summary
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-2.5 bg-slate-900 dark:bg-slate-900 light:bg-white border border-slate-800 rounded-lg">
                  <span className="text-slate-400 text-[10px] block uppercase">Valid Records</span>
                  <span className="text-base font-bold font-mono text-emerald-400">{validationReport.valid_count?.toLocaleString()}</span>
                </div>
                <div className="p-2.5 bg-slate-900 dark:bg-slate-900 light:bg-white border border-slate-800 rounded-lg">
                  <span className="text-slate-400 text-[10px] block uppercase">Invalid Rows</span>
                  <span className="text-base font-bold font-mono text-red-400">{validationReport.invalid_count?.toLocaleString()}</span>
                </div>
                <div className="p-2.5 bg-slate-900 dark:bg-slate-900 light:bg-white border border-slate-800 rounded-lg">
                  <span className="text-slate-400 text-[10px] block uppercase">Duplicates</span>
                  <span className="text-base font-bold font-mono text-amber-400">{validationReport.duplicates_detected?.toLocaleString()}</span>
                </div>
                <div className="p-2.5 bg-slate-900 dark:bg-slate-900 light:bg-white border border-slate-800 rounded-lg">
                  <span className="text-slate-400 text-[10px] block uppercase">Status</span>
                  <span className="text-xs font-bold text-brand-400 mt-1 block">
                    {validationReport.ready_for_processing ? '✓ READY' : 'ACTION REQUIRED'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </GlassCard>
      )}

      {/* Dataset History Repository */}
      <GlassCard className="p-6 space-y-4">
        <h3 className="section-heading">
          <Database className="w-4 h-4 text-brand-400" />
          Ingested Datasets Repository
        </h3>

        {datasets.length === 0 ? (
          <EmptyState
            icon={Database}
            title="No Datasets Uploaded"
            description="Upload bank statements, invoices, or payment settlement CSV files to begin."
          />
        ) : (
          <div className="table-container">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-100 text-slate-400">
                  <th className="p-3 font-semibold">Filename</th>
                  <th className="p-3 font-semibold">Type</th>
                  <th className="p-3 font-semibold font-mono">Records</th>
                  <th className="p-3 font-semibold">Status</th>
                  <th className="p-3 font-semibold">Uploaded</th>
                  <th className="p-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((ds) => (
                  <tr key={ds.dataset_id} className="table-row">
                    <td className="p-3 font-medium text-slate-200 dark:text-slate-200 light:text-slate-800 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                      <span className="truncate max-w-[200px]" title={ds.filename}>{ds.filename}</span>
                    </td>
                    <td className="p-3 uppercase text-slate-400 font-mono text-[11px]">{ds.source_type}</td>
                    <td className="p-3 font-mono text-slate-300 dark:text-slate-300 light:text-slate-700">{ds.record_count?.toLocaleString()}</td>
                    <td className="p-3">
                      <StatusBadge status={ds.processing_status} />
                    </td>
                    <td className="p-3 text-slate-400">
                      {new Date(ds.uploaded_at).toLocaleDateString()}
                    </td>
                    <td className="p-3 text-right">
                      <div className="inline-flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/reconciliation?dataset_id=${ds.dataset_id}`)}
                          icon={ArrowRight}
                        >
                          Reconcile
                        </Button>
                        <button
                          onClick={() => setDeletingDataset(ds)}
                          className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-slate-800/40 transition-colors"
                          title="Delete Dataset"
                          aria-label="Delete Dataset"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>

      {/* Delete Confirmation Modal */}
      <ConfirmationDialog
        isOpen={Boolean(deletingDataset)}
        onClose={() => setDeletingDataset(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Dataset"
        message={`Are you sure you want to permanently delete '${deletingDataset?.filename}' from MongoDB Atlas?`}
        confirmLabel="Delete Dataset"
        loading={deleting}
      />
    </PageContainer>
  )
}
