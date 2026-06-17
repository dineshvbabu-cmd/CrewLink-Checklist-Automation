import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getSelfServicePacket, submitSelfServicePacket } from '../api'
import type { SelfServicePacket } from '../types'

export default function SelfServiceApprovalPage() {
  const { token } = useParams<{ token: string }>()
  const [packet, setPacket] = useState<SelfServicePacket | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [seafarerName, setSeafarerName] = useState('')
  const [items, setItems] = useState<Array<{ srNo: number; verifyCrew: boolean; seafarerRemark: string }>>([])
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!token) {
      return
    }

    getSelfServicePacket(token)
      .then(response => {
        setPacket(response)
        setSeafarerName(response.crewName)
        setItems(
          response.items.map(item => ({
            srNo: item.srNo,
            verifyCrew: item.verifyCrew,
            seafarerRemark: item.seafarerRemark,
          })),
        )
      })
      .finally(() => setLoading(false))
  }, [token])

  const updateItem = (srNo: number, next: Partial<{ verifyCrew: boolean; seafarerRemark: string }>) => {
    setItems(previous =>
      previous.map(item => (item.srNo === srNo ? { ...item, ...next } : item)),
    )
  }

  const handleSubmit = async () => {
    if (!token) {
      return
    }

    setSubmitting(true)
    try {
      const response = await submitSelfServicePacket(token, { seafarerName, items })
      setPacket(response)
      setMessage('Confirmation submitted successfully. Crewlink Ops has been notified.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Loading seafarer approval link...
      </div>
    )
  }

  if (!packet) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Approval link not found.
      </div>
    )
  }

  return (
    <div className="min-h-screen px-4 py-8 approval-shell">
      <div className="max-w-4xl mx-auto rounded-xl bg-white shadow-lg overflow-hidden border border-blue-100">
        <div className="approval-header px-6 py-5 text-white">
          <div className="text-sm opacity-80">Crewlink Self-Service Confirmation</div>
          <h1 className="m-0 mt-1 text-2xl font-bold">{packet.crewName}</h1>
          <div className="text-sm opacity-90 mt-1">
            {packet.rank} | Sent by {packet.sentBy} on {packet.sentAt}
          </div>
        </div>

        <div className="p-6">
          <div className="grid md:grid-cols-[1.2fr,0.8fr] gap-4 mb-5">
            <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-blue-700 font-semibold">Approval Link Status</div>
              <div className="text-sm text-blue-900 mt-1">{packet.status === 'submitted' ? 'Submitted' : 'Awaiting Seafarer Confirmation'}</div>
            </div>
            <div className="rounded-lg border border-gray-200 px-4 py-3">
              <label className="text-xs uppercase tracking-wide text-gray-500 font-semibold block mb-2">Seafarer Name</label>
              <input
                value={seafarerName}
                onChange={event => setSeafarerName(event.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              />
            </div>
          </div>

          {message && (
            <div className="mb-4 rounded border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
              {message}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="crewlink-table">
              <thead>
                <tr>
                  <th style={{ width: 40 }}>Sr No</th>
                  <th>Document / Item Description</th>
                  <th style={{ width: 110 }}>Received</th>
                  <th style={{ minWidth: 240 }}>Seafarer Remarks</th>
                </tr>
              </thead>
              <tbody>
                {packet.items.map(item => {
                  const local = items.find(entry => entry.srNo === item.srNo) ?? {
                    srNo: item.srNo,
                    verifyCrew: false,
                    seafarerRemark: '',
                  }

                  return (
                    <tr key={item.srNo}>
                      <td className="text-center text-gray-500">{item.srNo}</td>
                      <td>{item.description}</td>
                      <td className="text-center">
                        <input
                          type="checkbox"
                          checked={local.verifyCrew}
                          onChange={event => updateItem(item.srNo, { verifyCrew: event.target.checked })}
                        />
                      </td>
                      <td>
                        <input
                          value={local.seafarerRemark}
                          onChange={event => updateItem(item.srNo, { seafarerRemark: event.target.value })}
                          placeholder="Add confirmation or issue details"
                          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                        />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-5 flex justify-end gap-2">
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="rounded bg-blue-900 text-white px-4 py-2 text-sm hover:opacity-90 disabled:opacity-60"
            >
              {submitting ? 'Submitting...' : 'Submit Confirmation'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
