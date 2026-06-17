import type { AuditEntry } from '../../types'

interface Props {
  entries: AuditEntry[]
}

export default function AuditLogPanel({ entries }: Props) {
  return (
    <div className="rounded border border-gray-200 bg-white">
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="m-0 text-sm font-semibold text-gray-800">Audit Trail</h3>
        <p className="m-0 mt-1 text-xs text-gray-500">Every AI run, manual remark, override, and seafarer action is captured here.</p>
      </div>
      <div className="max-h-56 overflow-auto">
        {entries.length === 0 ? (
          <div className="px-4 py-4 text-sm text-gray-400">No audit entries yet.</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {entries.map(entry => (
              <div key={entry.id} className="px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-medium text-gray-800">{entry.action.replace(/_/g, ' ')}</div>
                  <div className="text-[11px] text-gray-400">{entry.timestamp}</div>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {entry.actor} - {entry.target}
                </div>
                <div className="text-sm text-gray-700 mt-1">{entry.message}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
