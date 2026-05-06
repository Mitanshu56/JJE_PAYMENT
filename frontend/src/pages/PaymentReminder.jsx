import React, { useEffect, useState } from 'react'
import { billsAPI } from '../services/api'
import api from '../services/api'

function PaymentReminder() {
  const [parties, setParties] = useState([])
  const [search, setSearch] = useState('')
  const [selectedParty, setSelectedParty] = useState(null)
  const [partyEmail, setPartyEmail] = useState('')
  const [bills, setBills] = useState([])
  const [selectedInvoices, setSelectedInvoices] = useState([])
  const [reminderDays, setReminderDays] = useState(30)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadParties()
    loadHistory()
  }, [])

  const loadParties = async () => {
    try {
      setLoading(true)
      const res = await api.get('/api/payment-reminders/parties')
      setParties(res.data.parties || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const loadHistory = async () => {
    try {
      const res = await api.get('/api/payment-reminders/history')
      setHistory(res.data.history || [])
    } catch (err) {
      console.error(err)
    }
  }

  const selectParty = async (party) => {
    setSelectedParty(party)
    try {
      const res = await api.get(`/api/payment-reminders/party/${encodeURIComponent(party.party_name)}`)
      setPartyEmail(res.data.email || '')
      setBills(res.data.bills || [])
      setSelectedInvoices([])
    } catch (err) {
      console.error(err)
    }
  }

  const saveEmail = async () => {
    if (!selectedParty) return
    try {
      await api.post('/api/payment-reminders/party-email', { party_name: selectedParty.party_name, email: partyEmail })
      alert('Saved')
      loadParties()
    } catch (err) {
      alert('Failed to save')
    }
  }

  const toggleInvoice = (inv) => {
    const exists = selectedInvoices.includes(inv.invoice_no)
    if (exists) setSelectedInvoices(selectedInvoices.filter(i => i !== inv.invoice_no))
    else setSelectedInvoices([...selectedInvoices, inv.invoice_no])
  }

  const sendSingle = async (inv) => {
    if (!selectedParty) return
    try {
      await api.post('/api/payment-reminders/send-single', { party_name: selectedParty.party_name, party_email: partyEmail, invoice_no: inv.invoice_no, reminder_days: reminderDays })
      alert('Sent')
      loadHistory()
    } catch (err) {
      alert('Failed to send')
    }
  }

  const sendMultiple = async () => {
    if (!selectedParty || selectedInvoices.length === 0) return
    try {
      await api.post('/api/payment-reminders/send-multiple', { party_name: selectedParty.party_name, party_email: partyEmail, invoice_numbers: selectedInvoices, reminder_days: reminderDays })
      alert('Sent')
      loadHistory()
    } catch (err) {
      alert('Failed to send')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Payment Reminder</h1>
        <div className="flex gap-6">
          <div className="w-1/3 bg-white p-4 rounded shadow">
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search party" className="w-full border p-2 mb-3" />
            <div className="space-y-2 max-h-96 overflow-auto">
              {loading && <div>Loading...</div>}
              {parties.filter(p => p.party_name.toLowerCase().includes(search.toLowerCase())).map(p => (
                <div key={p.party_name} className="p-2 border rounded hover:bg-gray-50 cursor-pointer" onClick={() => selectParty(p)}>
                  <div className="font-medium">{p.party_name}</div>
                  <div className="text-sm text-gray-500">Invoices: {p.invoice_count} — Pending: ₹{p.pending_amount}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="w-2/3 bg-white p-4 rounded shadow">
            {!selectedParty && <div>Select a party to view invoices</div>}
            {selectedParty && (
              <div>
                <h2 className="text-lg font-semibold">{selectedParty.party_name}</h2>
                <div className="mt-3">
                  <label className="block text-sm">Email</label>
                  <div className="flex gap-2 mt-1">
                    <input className="border p-2 flex-1" value={partyEmail} onChange={(e) => setPartyEmail(e.target.value)} />
                    <button onClick={saveEmail} className="bg-blue-600 text-white px-3 rounded">Save</button>
                  </div>
                </div>

                <div className="mt-4">
                  <label className="block text-sm">Reminder Days</label>
                  <select value={reminderDays} onChange={(e) => setReminderDays(Number(e.target.value))} className="border p-2 mt-1">
                    <option value={20}>20</option>
                    <option value={30}>30</option>
                    <option value={45}>45</option>
                    <option value={0}>Custom</option>
                  </select>
                </div>

                <div className="mt-4">
                  <table className="w-full text-sm border">
                    <thead className="bg-gray-100">
                      <tr>
                        <th></th>
                        <th>Invoice No</th>
                        <th>Date</th>
                        <th>Amount</th>
                        <th>Pending</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bills.map(inv => (
                        <tr key={inv._id} className="border-t">
                          <td className="p-2 text-center"><input type="checkbox" checked={selectedInvoices.includes(inv.invoice_no)} onChange={() => toggleInvoice(inv)} /></td>
                          <td className="p-2">{inv.invoice_no}</td>
                          <td className="p-2">{inv.invoice_date}</td>
                          <td className="p-2">₹{inv.grand_total}</td>
                          <td className="p-2">₹{(inv.grand_total - (inv.total_paid || 0)).toFixed(2)}</td>
                          <td className="p-2">{inv.status}</td>
                          <td className="p-2">
                            <button onClick={() => sendSingle(inv)} className="bg-green-600 text-white px-2 rounded text-xs">Send Single</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mt-3 flex gap-2">
                  <button onClick={sendMultiple} className="bg-blue-600 text-white px-3 py-2 rounded">Send Multiple</button>
                </div>

                <div className="mt-6">
                  <h3 className="font-semibold">Reminder History</h3>
                  <table className="w-full text-sm border mt-2">
                    <thead className="bg-gray-100">
                      <tr><th>When</th><th>Type</th><th>Invoices</th><th>Total Pending</th><th>Status</th></tr>
                    </thead>
                    <tbody>
                      {history.filter(h => h.party_name === selectedParty.party_name).map(h => (
                        <tr key={h._id} className="border-t">
                          <td className="p-2">{new Date(h.sent_at).toLocaleString()}</td>
                          <td className="p-2">{h.reminder_type}</td>
                          <td className="p-2">{(h.invoice_numbers || []).join(', ')}</td>
                          <td className="p-2">₹{h.total_pending_amount}</td>
                          <td className="p-2">{h.email_status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default PaymentReminder

*** End Patch