import { useState, useEffect } from 'react'
import { CreditCard, Search, ChevronLeft, ChevronRight } from 'lucide-react'
import { listTransactions } from '../api'
import { StatusBadge, ConfidenceBar, Spinner, EmptyState, Currency } from '../components/ui'

const STATUSES = ['', 'MATCHED', 'AI_REVIEW', 'MANUAL_REVIEW', 'DUPLICATE', 'MISMATCH']

export default function Transactions() {
  const [transactions, setTransactions] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const PAGE_SIZE = 20

  const fetch = async () => {
    setLoading(true)
    try {
      const data = await listTransactions({
        limit: PAGE_SIZE,
        skip: page * PAGE_SIZE,
        status: statusFilter || undefined,
      })
      setTransactions(data.transactions || [])
      setTotal(data.total || 0)
    } catch {}
    finally { setLoading(false) }
  }

  useEffect(() => { fetch() }, [page, statusFilter])

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Transactions</h1>
          <p className="text-gray-400 text-sm mt-1">
            {total.toLocaleString()} records across all reconciliation runs
          </p>
        </div>
        {/* Filter */}
        <select
          id="status-filter"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0) }}
          className="input text-sm w-44"
        >
          {STATUSES.map(s => (
            <option key={s} value={s}>{s || 'All Statuses'}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-600 bg-dark-700/50">
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider font-medium">Transaction ID</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider font-medium">Customer</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider font-medium">Expected</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider font-medium">Actual</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider font-medium">Difference</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider font-medium">Status</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 uppercase tracking-wider font-medium w-36">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-16 text-center">
                    <Spinner size="md" />
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <EmptyState
                      icon={CreditCard}
                      title="No transactions found"
                      description="Run a reconciliation to populate transaction records."
                    />
                  </td>
                </tr>
              ) : transactions.map((txn) => (
                <tr key={txn.transaction_id || txn.result_id} className="table-row">
                  <td className="px-4 py-3 font-mono text-xs text-gray-300">{txn.transaction_id}</td>
                  <td className="px-4 py-3 text-gray-300 text-xs">{txn.customer_id}</td>
                  <td className="px-4 py-3 text-gray-300">
                    <Currency amount={txn.expected_amount} />
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    <Currency amount={txn.actual_amount} />
                  </td>
                  <td className="px-4 py-3">
                    {parseFloat(txn.difference) > 0 ? (
                      <span className="text-red-400 font-mono text-sm">
                        ₹{parseFloat(txn.difference).toFixed(2)}
                      </span>
                    ) : (
                      <span className="text-green-400 font-mono text-sm">₹0.00</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={txn.status} />
                  </td>
                  <td className="px-4 py-3">
                    <ConfidenceBar value={txn.confidence} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-dark-600 flex items-center justify-between text-xs text-gray-400">
            <span>Page {page + 1} of {totalPages} — {total} records</span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn-secondary py-1 px-2"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="btn-secondary py-1 px-2"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
