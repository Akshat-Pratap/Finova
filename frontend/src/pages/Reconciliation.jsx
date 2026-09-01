import { useState } from 'react'
import { Zap, BarChart3, Clock, CheckCircle, Brain, Users } from 'lucide-react'
import { startReconciliation } from '../api'
import { StatCard, Spinner, Alert } from '../components/ui'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'

export default function Reconciliation() {
  const [numRecords, setNumRecords] = useState(250)
  const [seed, setSeed] = useState(42)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleRun = async () => {
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      const res = await startReconciliation({ source: 'synthetic', num_records: numRecords, seed })
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  const chartData = result ? [
    { name: 'Matched', value: result.records_matched, fill: '#22c55e' },
    { name: 'AI Review', value: result.records_ai_reviewed, fill: '#6172f3' },
    { name: 'Manual', value: result.records_manual_review, fill: '#f59e0b' },
    { name: 'Duplicate', value: result.records_duplicate, fill: '#a855f7' },
  ] : []

  const gtData = result?.analytics
  const matchPct = result ? Math.round((result.match_rate || 0) * 100) : 0

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white">Reconciliation Engine</h1>
        <p className="text-gray-400 text-sm mt-1">
          Run deterministic matching, confidence scoring, and AI investigation
        </p>
      </div>

      {/* Configuration Panel */}
      <div className="card p-6">
        <h2 className="section-heading mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-brand-400" />
          Processing Configuration
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">Data Source</label>
            <div className="input flex items-center justify-between text-gray-300">
              <span>Synthetic Dataset</span>
              <span className="text-xs text-green-400 bg-green-900/30 border border-green-700/30 rounded px-2 py-0.5">DEMO</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">
              Records ({numRecords})
            </label>
            <input
              id="num-records-slider"
              type="range"
              min={50}
              max={1000}
              step={50}
              value={numRecords}
              onChange={(e) => setNumRecords(+e.target.value)}
              className="w-full accent-brand-500 mt-2"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>50</span><span>1000</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-2 uppercase tracking-wider">Random Seed</label>
            <input
              id="seed-input"
              type="number"
              value={seed}
              onChange={(e) => setSeed(+e.target.value)}
              className="input w-full"
              min={1}
              max={9999}
            />
          </div>
        </div>

        <div className="mt-6 flex items-center gap-4">
          <button
            id="start-reconciliation-btn"
            onClick={handleRun}
            disabled={running}
            className="btn-primary"
          >
            {running ? (
              <><Spinner size="sm" /> Processing {numRecords} records…</>
            ) : (
              <><Zap className="w-4 h-4" /> Start Reconciliation</>
            )}
          </button>
          {running && (
            <p className="text-xs text-gray-400">
              Running data engine → matching → AI investigation…
            </p>
          )}
        </div>
      </div>

      {/* Error */}
      {error && <Alert type="error" title="Reconciliation Failed" message={error} />}

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-slide-up">
          {/* Success banner */}
          <Alert
            type="success"
            title={`Run ${result.run_id} completed in ${result.processing_time_seconds?.toFixed(3)}s`}
            message={`${result.records_processed} records processed. Match rate: ${matchPct}%.`}
          />

          {/* Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Matched" value={result.records_matched} icon={CheckCircle} color="green"
              subtitle={`${matchPct}% auto-reconciled`} />
            <StatCard label="AI Investigated" value={result.records_ai_reviewed} icon={Brain} color="brand"
              subtitle="Ambiguous cases" />
            <StatCard label="Exceptions" value={result.exceptions_created} icon={BarChart3} color="amber"
              subtitle="Require attention" />
            <StatCard label="Processing Time" value={`${result.processing_time_seconds?.toFixed(3)}s`}
              icon={Clock} color="purple" subtitle={`${numRecords} records`} />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card p-5">
              <h3 className="section-heading mb-4">Status Breakdown</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(45,59,107,0.5)" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
                  <Tooltip
                    contentStyle={{ background: '#151d38', border: '1px solid #2d3b6b', borderRadius: 8, fontSize: 12 }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Classification metrics */}
            {result.analytics?.ground_truth_available && (
              <div className="card p-5">
                <h3 className="section-heading mb-4">Classification Metrics (Ground Truth)</h3>
                <div className="space-y-4">
                  {[
                    { label: 'Precision', value: result.analytics.precision, color: 'text-green-400' },
                    { label: 'Recall', value: result.analytics.recall, color: 'text-brand-400' },
                    { label: 'F1 Score', value: result.analytics.f1_score, color: 'text-purple-400' },
                  ].map(({ label, value, color }) => (
                    <div key={label}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-400">{label}</span>
                        <span className={`font-bold font-mono ${color}`}>{(value * 100).toFixed(1)}%</span>
                      </div>
                      <div className="h-1.5 bg-dark-600 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${color.replace('text-', 'bg-')}`}
                          style={{ width: `${(value * 100).toFixed(1)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                  <div className="mt-4 pt-4 border-t border-dark-600 grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-dark-700 rounded-lg p-3">
                      <p className="text-gray-400">True Positives</p>
                      <p className="text-green-400 font-bold text-base mt-0.5">{result.analytics.true_positives}</p>
                    </div>
                    <div className="bg-dark-700 rounded-lg p-3">
                      <p className="text-gray-400">False Positives</p>
                      <p className="text-red-400 font-bold text-base mt-0.5">{result.analytics.false_positives}</p>
                    </div>
                    <div className="bg-dark-700 rounded-lg p-3">
                      <p className="text-gray-400">True Negatives</p>
                      <p className="text-blue-400 font-bold text-base mt-0.5">{result.analytics.true_negatives ?? '—'}</p>
                    </div>
                    <div className="bg-dark-700 rounded-lg p-3">
                      <p className="text-gray-400">False Negatives</p>
                      <p className="text-amber-400 font-bold text-base mt-0.5">{result.analytics.false_negatives}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
