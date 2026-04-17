import React, { useEffect, useRef, useState } from 'react'
import { Upload, Check, AlertCircle } from 'lucide-react'
import { uploadAPI } from '../services/api'

export default function FileUpload({ onUploadComplete }) {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [lastInvoiceUpload, setLastInvoiceUpload] = useState(null)
  const ignoreNextResultRef = useRef(false)

  const formatDateTime = (value) => {
    if (!value) return '-'
    const normalizedValue =
      typeof value === 'string' && !/[zZ]|[+\-]\d\d:\d\d$/.test(value)
        ? `${value}Z`
        : value
    const date = new Date(normalizedValue)
    if (Number.isNaN(date.getTime())) return '-'
    return date.toLocaleString('en-IN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    })
  }

  const loadLastInvoiceUpload = async () => {
    try {
      const response = await uploadAPI.getLastInvoiceUpload()
      setLastInvoiceUpload(response?.data?.last_upload || null)
    } catch {
      setLastInvoiceUpload(null)
    }
  }

  useEffect(() => {
    loadLastInvoiceUpload()
  }, [])

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setLoading(true)
      setMessage(null)
      ignoreNextResultRef.current = false

      let result
      result = await uploadAPI.uploadInvoices(file)

      const summary = result?.data?.import_summary
      const newRecords = Number(summary?.new_records || 0)
      const successText = newRecords > 0
        ? `${newRecords} new record${newRecords === 1 ? '' : 's'} added successfully.`
        : 'All things are up to date. Nothing to add.'

      if (ignoreNextResultRef.current) return

      setMessage({
        type: 'success',
        text: successText,
      })

      window.alert(successText)

      await loadLastInvoiceUpload()

      if (onUploadComplete) {
        onUploadComplete()
      }

      // Clear message after 5 seconds
      setTimeout(() => setMessage(null), 5000)
    } catch (err) {
      if (ignoreNextResultRef.current) return

      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Upload failed',
      })
    } finally {
      setLoading(false)
      // Reset file input
      e.target.value = ''
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Upload Files</h3>

      {/* File Upload Area */}
      <label className="block">
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition">
          <Upload className="mx-auto mb-2 text-gray-400" size={32} />
          <p className="text-gray-900 font-medium">Click to upload or drag and drop</p>
          <p className="text-gray-500 text-sm">Excel files (.xlsx, .xls) only</p>
          <input
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileSelect}
            disabled={loading}
            className="hidden"
          />
        </div>
      </label>

      {/* Status Messages */}
      {message && (
        <div
          className={`mt-4 p-4 rounded-lg flex items-start gap-3 ${
            message.type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
          }`}
        >
          {message.type === 'success' ? (
            <Check className="text-green-600 mt-0.5" size={20} />
          ) : (
            <AlertCircle className="text-red-600 mt-0.5" size={20} />
          )}
          <div>
            <p className={message.type === 'success' ? 'text-green-800' : 'text-red-800'}>
              {message.text}
            </p>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="mt-4 text-center">
          <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <p className="text-gray-600 mt-2">Uploading file...</p>
        </div>
      )}

      {lastInvoiceUpload && (
        <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-4">
          <p className="text-sm font-semibold text-blue-900">Last Invoice Upload</p>
          <p className="mt-1 text-sm text-blue-800">Time: {formatDateTime(lastInvoiceUpload.uploaded_at)}</p>
          <p className="text-sm text-blue-800">New records: {lastInvoiceUpload.new_records}</p>
          <p className="text-sm text-blue-800">Updated records: {lastInvoiceUpload.updated_records}</p>
          <p className="text-sm text-blue-800">Unchanged records: {lastInvoiceUpload.unchanged_records}</p>
        </div>
      )}
    </div>
  )
}
