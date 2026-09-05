import { useState, useEffect } from 'react'
import {
  CreditCard, Search, ChevronLeft, ChevronRight, Filter,
  Download, ArrowUpDown, CheckCircle, AlertTriangle, RefreshCw
} from 'lucide-react'
import { listTransactions } from '../api'
import {
  PageContainer, PageHeader, GlassCard, StatCard,
  StatusBadge, ConfidenceBar, Button, Spinner, EmptyState, Currency
} from '../components/ui'

const STATUSES = ['', 'MATCHED', 'AI_REVIEW', 'MANUAL_REVIEW', 'DUPLICATE', 'MISMATCH']

export default function Transactions() {
  const [transactions, setTransactions] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const PAGE_SIZE = 20

  const fetchTransactions = async () => {
    setLoading(true)
    try {
      const data = await listTransactions({
        limit: PAGE_SIZE,
        skip: page * PAGE_SIZE,
        status: statusFilter || undefined,
      })
      setTransactions(data.transactions || [])
      setTotal(data.total || 0)
    } catch (err) {
      console.warn('Failed to load transactions:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTransactions()
  }, [page, statusFilter])

  // Filter in-memory for search query matching txn ID or customer ID
  const filteredTxns = transactions.filter(txn => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      (txn.transaction_id && txn.transaction_id.toLowerCase().includes(term)) ||
      (txn.customer_id && txn.customer_id.toLowerCase().includes(term)) ||
      (txn.invoice_id && txn.invoice_id.toLowerCase().includes(term))
    )
  })

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <PageContainer>
      <PageHeader
        title="Transaction Records & Signals"
        subtitle={`${total.toLocaleString()} ingested records across all batches with ML confidence breakdowns`}
        icon={CreditCard}
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchTransactions}
            icon={RefreshCw}
            loading={loading}
          >
            Refresh
          </Button>
        }
      />

      {/* Filter & Search Bar */}
      <GlassCard className="p-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Search by Txn ID, Customer, Invoice..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input pl-10 text-xs w-full"
            />
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs text-slate-400 font-medium">Status:</span>
            </div>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(0) }}
              className="select text-xs w-44"
            >
              {STATUSES.map(s => (
                <option key={s} value={s}>{s ? s.replace(/_/g, ' ') : 'All Statuses'}</option>
              ))}
            </select>
          </div>
        </div>
      </GlassCard>

      {/* Transactions Table Card */}
      <GlassCard className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-dark-700 bg-slate-50 dark:bg-dark-800/80">
                <th className="px-4 py-3.5 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px]">Transaction ID</th>
                <th className="px-4 py-3.5 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px]">Customer / Counterparty</th>
                <th className="px-4 py-3.5 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px] text-right">Expected</th>
                <th className="px-4 py-3.5 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px] text-right">Actual</th>
                <th className="px-4 py-3.5 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px] text-right">Variance</th>
                <th className="px-4 py-3.5 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px]">Reconciliation Status</th>
                <th className="px-4 py-3.5 text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider text-[11px] w-36">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-dark-800">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-20 text-center">
                    <Spinner size="lg" />
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">Loading transactions...</p>
                  </td>
                </tr>
              ) : filteredTxns.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12">
                    <EmptyState
                      icon={CreditCard}
                      title="No transactions found"
                      description={searchTerm ? "No records match your search criteria." : "Run a reconciliation batch to populate ledger records."}
                    />
                  </td>
                </tr>
              ) : filteredTxns.map((txn) => {
                const diff = parseFloat(txn.difference || 0)
                return (
                  <tr key={txn.transaction_id || txn.result_id} className="table-row">
                    <td className="px-4 py-3 font-mono font-medium text-indigo-600 dark:text-indigo-400">
                      {txn.transaction_id}
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                      {txn.customer_id || txn.counterparty || '—'}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-700 dark:text-slate-300">
                      <Currency amount={txn.expected_amount} />
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-700 dark:text-slate-300">
                      <Currency amount={txn.actual_amount} />
                    </td>
                    <td className="px-4 py-3 text-right font-mono">
                      {diff > 0 ? (
                        <span className="text-rose-500 dark:text-rose-400 font-semibold">
                          ₹{diff.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                          ₹0.00
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={txn.status} />
                    </td>
                    <td className="px-4 py-3">
                      <ConfidenceBar value={txn.confidence} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="px-4 py-3.5 border-t border-slate-200 dark:border-dark-700 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 bg-slate-50/50 dark:bg-dark-900/50">
            <div>
              Showing <span className="font-semibold text-slate-700 dark:text-slate-200">{page * PAGE_SIZE + 1}</span> to{' '}
              <span className="font-semibold text-slate-700 dark:text-slate-200">
                {Math.min((page + 1) * PAGE_SIZE, total)}
              </span>{' '}
              of <span className="font-semibold text-slate-700 dark:text-slate-200">{total.toLocaleString()}</span> records
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                icon={ChevronLeft}
              >
                Prev
              </Button>
              <span className="px-2 font-mono font-medium text-slate-700 dark:text-slate-300">
                {page + 1} / {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
              >
                Next
                <ChevronRight className="w-3.5 h-3.5 ml-1 inline" />
              </Button>
            </div>
          </div>
        )}
      </GlassCard>
    </PageContainer>
  )
}
