import { Send } from 'lucide-react'
import type { ConfirmationItem, SelfServicePacket } from '../../types'

interface Props {
  items: ConfirmationItem[]
  sending: boolean
  latestLink: SelfServicePacket | null
  onSend: () => void
}

export default function SeafarerConfirmationTab({ items, sending, latestLink, onSend }: Props) {
  return (
    <div>
      <div className="px-4 py-3" style={{ backgroundColor: '#f7fafd', borderBottom: '1px solid #dde3ec' }}>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <p className="text-xs text-gray-600 m-0">
            This is the list of documents and items that must be handed over to the seafarer before departure.
          </p>
          <button
            onClick={onSend}
            style={{ backgroundColor: '#c0392b', color: 'white', border: 'none', borderRadius: 4, padding: '7px 16px', fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
          >
            <Send size={13} />
            {sending ? 'Sending...' : 'Send to seafarer for approval'}
          </button>
        </div>

        {latestLink && (
          <div className="mt-3 rounded border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-900 flex items-center justify-between gap-3 flex-wrap">
            <span>
              Latest self-service link:
              {' '}
              <a href={latestLink.url} target="_blank" rel="noreferrer" className="underline">
                {latestLink.url}
              </a>
            </span>
            <span className="text-blue-700">
              {latestLink.status.toUpperCase()} | sent {latestLink.sentAt}
            </span>
          </div>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="crewlink-table">
          <thead>
            <tr>
              <th style={{ width: 40 }}>Sr No</th>
              <th style={{ minWidth: 320 }}>Document / Item Description</th>
              <th style={{ width: 90 }}>Verify (Ops)</th>
              <th style={{ minWidth: 150 }}>Office Remarks</th>
              <th style={{ width: 90 }}>Verify (Crew)</th>
              <th style={{ minWidth: 150 }}>Seafarer Remarks</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.srNo}>
                <td className="text-center text-gray-500">{item.srNo}</td>
                <td>{item.description}</td>
                <td className="text-center">
                  {item.verifyOps ? <span className="tick-verified">✓</span> : <span className="text-gray-300 text-xs">Pending</span>}
                </td>
                <td>
                  {item.officeRemark ? (
                    <span className="text-xs text-gray-600">{item.officeRemark}</span>
                  ) : (
                    <span className="text-gray-300 text-xs italic">No remark</span>
                  )}
                </td>
                <td className="text-center">
                  {item.verifyCrew ? <span className="tick-verified">✓</span> : <span className="text-gray-300 text-xs">Awaiting</span>}
                </td>
                <td>
                  {item.seafarerRemark ? (
                    <span className="text-xs text-gray-600">{item.seafarerRemark}</span>
                  ) : (
                    <span className="text-gray-300 text-xs italic">Awaiting seafarer</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
