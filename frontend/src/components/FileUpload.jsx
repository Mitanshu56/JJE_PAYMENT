import React, { useState } from 'react'
import { Upload, Check, AlertCircle } from 'lucide-react'
import { uploadAPI } from '../services/api'

export default function FileUpload({ onUploadComplete }) {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [uploadType, setUploadType] = useState('invoices')

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setLoading(true)
      setMessage(null)

      let result
      if (uploadType === 'invoices') {
        result = await uploadAPI.uploadInvoices(file)
      } else {
        result = await uploadAPI.uploadBankStatement(file)
      }

      setMessage({
        type: 'success',
        text: result.data.message,
      })

      if (onUploadComplete) {
        onUploadComplete()
      }

      // Clear message after 5 seconds
      setTimeout(() => setMessage(null), 5000)
    } catch (err) {
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

      {/* Upload Type Selector */}
      <div className="flex gap-4 mb-6">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            value="invoices"
            checked={uploadType === 'invoices'}
            onChange={(e) => setUploadType(e.target.value)}
            className="w-4 h-4 text-blue-600"
          />
          <span className="text-gray-700 font-medium">Invoice Excel</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            value="bank_statement"
            checked={uploadType === 'bank_statement'}
            onChange={(e) => setUploadType(e.target.value)}
            className="w-4 h-4 text-blue-600"
          />
          <span className="text-gray-700 font-medium">Bank Statement</span>
        </label>
      </div>

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
    </div>
  )
}
