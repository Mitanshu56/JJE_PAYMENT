import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

// Bills API
export const billsAPI = {
  getAll: (skip = 0, limit = 100, status = null, party = null) => {
    const params = new URLSearchParams({ skip, limit })
    if (status) params.append('status', status)
    if (party) params.append('party', party)
    return api.get(`/api/bills/?${params}`)
  },
  getById: (invoiceNo) => api.get(`/api/bills/${invoiceNo}`),
  getByParty: (partyName) => api.get(`/api/bills/party/${partyName}`),
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
}

// Dashboard API
export const dashboardAPI = {
  getSummary: () => api.get('/api/dashboard/summary'),
  getPartySummary: () => api.get('/api/dashboard/party-summary'),
  getMonthlySummary: () => api.get('/api/dashboard/monthly-summary'),
  matchPayments: () => api.post('/api/match-payments'),
}

export default api
