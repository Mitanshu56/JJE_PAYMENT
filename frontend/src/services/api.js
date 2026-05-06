import axios from 'axios'
import { getSelectedFiscalYear } from '../utils/fiscal'

const API_BASE_URL = 'http://localhost:8000'
const AUTH_TOKEN_KEY = 'jje_auth_token'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

export const authStorage = {
  getToken: () => localStorage.getItem(AUTH_TOKEN_KEY) || '',
  setToken: (token) => {
    if (token) localStorage.setItem(AUTH_TOKEN_KEY, token)
  },
  clearToken: () => localStorage.removeItem(AUTH_TOKEN_KEY),
}

api.interceptors.request.use((config) => {
  const token = authStorage.getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  // Attach selected fiscal year if present
  const selectedFY = getSelectedFiscalYear()
  if (selectedFY) {
    config.headers = config.headers || {}
    config.headers['X-Fiscal-Year'] = selectedFY
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      authStorage.clearToken()
    }
    return Promise.reject(error)
  },
)

export const authAPI = {
  login: (username, password) => api.post('/api/auth/login', { username, password }),
  me: () => api.get('/api/auth/me'),
  forgotPassword: (username) => api.post('/api/auth/forgot-password', { username }),
  validateResetToken: (token) => api.get(`/api/auth/reset-password/validate?token=${encodeURIComponent(token)}`),
  resetPassword: (payload) => api.post('/api/auth/reset-password', payload),
}

export const fiscalAPI = {
  listYears: () => api.get('/api/fiscal/years'),
  createYear: (payload) => api.post('/api/fiscal/years', payload),
  deleteYear: (fiscalYear, password) => api.delete(`/api/fiscal/years/${encodeURIComponent(fiscalYear)}`, { data: { password } }),
}

// Bills API
export const billsAPI = {
  getAll: (
    skip = 0,
    limit = 100,
    status = null,
    party = null,
    month = null,
  ) => {
    const params = new URLSearchParams({ skip, limit })
    if (status) params.append('status', status)
    if (party) params.append('party', party)
    if (month) params.append('month', month)
    return api.get(`/api/bills/?${params}`)
  },
  getById: (invoiceNo) => api.get(`/api/bills/${invoiceNo}`),
  getByParty: (partyName) => api.get(`/api/bills/party/${partyName}`),
  deleteById: (billId) => api.delete(`/api/bills/by-id/${billId}`),
  delete: (invoiceNo) => api.delete(`/api/bills/${invoiceNo}`),
}

// Payments API
export const paymentsAPI = {
  getAll: (skip = 0, limit = 100, party = null) => {
    const params = new URLSearchParams({ skip, limit })
    if (party) params.append('party', party)
    return api.get(`/api/payments/?${params}`)
  },
  getById: (paymentId) => api.get(`/api/payments/${paymentId}`),
  getByParty: (partyName) => api.get(`/api/payments/party/${partyName}`),
  createManual: (payload) => api.post('/api/payments/manual', payload),
  updateManual: (paymentId, payload) => api.put(`/api/payments/manual/${paymentId}`, payload),
  delete: (paymentId) => api.delete(`/api/payments/${paymentId}`),
}

// Upload API
export const uploadAPI = {
  uploadInvoices: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/upload/invoices', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  uploadBankStatement: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/upload/bank-statements', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  uploadStatementPdf: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/upload/statements/pdf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  getLastInvoiceUpload: () => api.get('/api/upload/invoices/last'),
  getHistory: (limit = 50) => api.get(`/api/upload/history?limit=${limit}`),
}

export const statementsAPI = {
  getMonthly: (filters = {}) => {
    const params = new URLSearchParams()

    if (filters.fiscalYear) params.append('fiscal_year', filters.fiscalYear)
    if (filters.year) params.append('year', filters.year)
    if (filters.month) params.append('month', filters.month)
    if (filters.page) params.append('page', filters.page)
    if (filters.pageSize) params.append('page_size', filters.pageSize)

    const query = params.toString()
    return api.get(`/api/upload/statements/monthly${query ? `?${query}` : ''}`)
  },
  getMatch: (filters = {}) => {
    const params = new URLSearchParams()

    if (filters.fiscalYear) params.append('fiscal_year', filters.fiscalYear)
    if (filters.neftOnly !== undefined) params.append('neft_only', String(Boolean(filters.neftOnly)))
    if (filters.page) params.append('page', filters.page)
    if (filters.pageSize) params.append('page_size', filters.pageSize)

    const query = params.toString()
    return api.get(`/api/upload/statements/match${query ? `?${query}` : ''}`)
  },
  confirmNeft: (payload) => api.post('/api/upload/statements/neft-confirm', payload),
  deleteMonth: (monthKey) => api.delete(`/api/upload/statements/month/${monthKey}`),
}

// Dashboard API
export const dashboardAPI = {
  getSummary: () => api.get('/api/dashboard/summary'),
  getPartySummary: () => api.get('/api/dashboard/party-summary'),
  getMonthlySummary: () => api.get('/api/dashboard/monthly-summary'),
  matchPayments: () => api.post('/api/match-payments'),
}

export const paymentRemindersAPI = {
  listParties: () => api.get('/api/payment-reminders/parties'),
  getParty: (partyName) => api.get(`/api/payment-reminders/party/${encodeURIComponent(partyName)}`),
  savePartyEmail: (payload) => api.post('/api/payment-reminders/party-email', payload),
  sendSingle: (payload) => api.post('/api/payment-reminders/send-single', payload),
  sendMultiple: (payload) => api.post('/api/payment-reminders/send-multiple', payload),
  getHistory: (limit=100) => api.get(`/api/payment-reminders/history?limit=${limit}`),
  getHistoryByParty: (partyName, limit=100) => api.get(`/api/payment-reminders/history/${encodeURIComponent(partyName)}?limit=${limit}`),
}

export default api
