import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for JWT authorization token & tenant ID
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('finova_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const orgId = localStorage.getItem('finova_org_id')
  if (orgId && orgId !== 'undefined' && orgId !== 'null') {
    config.headers['X-Organization-ID'] = orgId
  }
  return config
})

// Response interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail?.message ||
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred'
    return Promise.reject(new Error(message))
  }
)

// --- Auth & Tenant Operations ---
export const registerUser = (data) => api.post('/api/v1/auth/register', data)
export const loginUser = (data) => api.post('/api/v1/auth/login', data)
export const getMe = () => api.get('/api/v1/auth/me')
export const getOrganizations = () => api.get('/api/v1/organizations')
export const getOrgDetails = (orgId) => api.get(`/api/v1/organizations/${orgId}`)
export const updateOrgSettings = (orgId, data) => api.patch(`/api/v1/organizations/${orgId}/settings`, data)
export const listOrgMembers = (orgId) => api.get(`/api/v1/organizations/${orgId}/members`)
export const inviteOrgMember = (orgId, data) => api.post(`/api/v1/organizations/${orgId}/members`, data)

// --- Health ---
export const getHealth = () => api.get('/api/v1/health')

// --- Datasets & Column Mapping ---
export const uploadDataset = (formData) => api.post('/api/v1/datasets/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 600000, // 10 minutes for large file transfers
})
export const listDatasets = (params) => api.get('/api/v1/datasets', { params })
export const getDataset = (id) => api.get(`/api/v1/datasets/${id}`)
export const deleteDataset = (id) => api.delete(`/api/v1/datasets/${id}`)
export const validateDataset = (id, mapping) => api.post(`/api/v1/datasets/${id}/validate`, { column_mapping: mapping }, { timeout: 300000 })
export const generateDataset = (params) => api.post('/api/v1/datasets/generate', null, { params })

// --- Reconciliation ---
export const startReconciliation = (data) => api.post('/api/v1/reconciliation/run', data, { timeout: 600000 })
export const getJobStatus = (jobId) => api.get(`/api/v1/reconciliation/job/${jobId}`)
export const getRunDetails = (runId) => api.get(`/api/v1/reconciliation/${runId}`)
export const getRunStatus = (runId) => api.get(`/api/v1/reconciliation/runs/${runId}`)
export const listRuns = (params) => api.get('/api/v1/reconciliation', { params })

// --- Transactions Explorer ---
export const listTransactions = (params) => api.get('/api/v1/transactions', { params })
export const getTransaction = (id) => api.get(`/api/v1/transactions/${id}`)

// --- Exceptions Management & HITL ---
export const listExceptions = (params) => api.get('/api/v1/exceptions', { params })
export const getException = (id) => api.get(`/api/v1/exceptions/${id}`)
export const resolveException = (id, data) => api.post(`/api/v1/exceptions/${id}/resolve`, data)
export const rejectException = (id, data) => api.post(`/api/v1/exceptions/${id}/reject`, data)
export const ignoreException = (id, data) => api.post(`/api/v1/exceptions/${id}/ignore`, data)
export const assignException = (id, email) => api.post(`/api/v1/exceptions/${id}/assign`, { assignee_email: email })
export const addExceptionNote = (id, content) => api.post(`/api/v1/exceptions/${id}/notes`, { content })
export const recordAdjustment = (id, data) => api.post(`/api/v1/exceptions/${id}/adjust`, data)

// --- AI Investigations ---
export const triggerInvestigation = (exceptionId) => api.post(`/api/v1/investigations/${exceptionId}`)
export const getInvestigation = (exceptionId) => api.get(`/api/v1/investigations/results/${exceptionId}`)

// --- Integrations Hub ---
export const listIntegrations = () => api.get('/api/v1/integrations')
export const connectIntegration = (data) => api.post('/api/v1/integrations/connect', data)
export const testIntegration = (id) => api.post(`/api/v1/integrations/${id}/test`)
export const syncIntegration = (id, count = 50) => api.post(`/api/v1/integrations/${id}/sync`, null, { params: { count } })
export const disconnectIntegration = (id) => api.delete(`/api/v1/integrations/${id}`)

// --- Reports & Exports ---
export const exportReport = (data) => api.post('/api/v1/reports/export', data, { responseType: 'blob' })

// --- Analytics & Forecasting ---
export const getAnalyticsSummary = () => api.get('/api/v1/analytics/summary')
export const getRunMetrics = (runId) => api.get('/api/v1/analytics/metrics', { params: { run_id: runId } })
export const getForecast = (params) => api.get('/api/v1/forecast', { params })

// --- Audit Trail & Hash-Chain Verification ---
export const getAuditLogs = (params) => api.get('/api/v1/audit-logs', { params })
export const verifyAuditIntegrity = () => api.get('/api/v1/audit-logs/verify')

export default api
