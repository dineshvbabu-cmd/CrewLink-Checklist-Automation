import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, CheckCircle2, MoreVertical } from 'lucide-react'
import type { CrewMember } from '../../types'
import TrafficLight from '../Common/TrafficLight'

interface Props {
  crew: CrewMember[]
  selectedIds: Set<string>
  onToggleSelect: (id: string) => void
  onToggleSelectAll: (checked: boolean) => void
  onOpenChecklist: (member: CrewMember) => void
  aiLoadingId: string | null
  onRunAICheck: (id: string) => void
}

const MENU_ITEMS = [
  'Deplan',
  'Experience',
  'Pre-Joining Checklist',
  'Medical Request',
  'Flag Docs',
  'Contract',
  'Sign On',
  'Crew Info',
  'Accommodation',
  'Add to planner',
]

function ThreeDotMenu({ member, onSelect }: { member: CrewMember; onSelect: (item: string) => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen(current => !current)}
        aria-label="More actions"
        title="More actions"
        className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
      >
        <MoreVertical size={15} />
      </button>
      {open && (
        <div
          className="absolute right-0 top-6 bg-white border border-gray-200 rounded shadow-lg z-50 min-w-[190px]"
          style={{ fontSize: '12px' }}
        >
          {MENU_ITEMS.map(item => (
            <button
              key={item}
              onClick={() => {
                onSelect(item)
                setOpen(false)
              }}
              className={`w-full text-left px-4 py-2 hover:bg-blue-50 ${
                item === 'Pre-Joining Checklist'
                  ? 'text-blue-700 font-semibold border-t border-b border-blue-100 bg-blue-50'
                  : 'text-gray-700'
              }`}
            >
              {item === 'Pre-Joining Checklist' && <span className="mr-1.5">AI</span>}
              {item}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function CrewTable({
  crew,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onOpenChecklist,
  aiLoadingId,
  onRunAICheck,
}: Props) {
  const navigate = useNavigate()
  const selectableIds = crew.map(member => member.id)
  const allSelected = selectableIds.length > 0 && selectableIds.every(id => selectedIds.has(id))
  const selectedCount = selectableIds.filter(id => selectedIds.has(id)).length

  const handleMenuSelect = (item: string, member: CrewMember) => {
    if (item === 'Pre-Joining Checklist') {
      onOpenChecklist(member)
    }
  }

  const isReliefDueSoon = (dateStr: string) => {
    try {
      const parsed = new Date(dateStr.replace(/-/g, ' '))
      const now = new Date()
      const diffDays = (parsed.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
      return diffDays < 45
    } catch {
      return false
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="crewlink-table">
        <thead>
          <tr>
            <th style={{ width: 38 }}>
              <input
                aria-label="Select all crew"
                type="checkbox"
                checked={allSelected}
                onChange={event => onToggleSelectAll(event.target.checked)}
              />
            </th>
            <th style={{ width: 40 }}>Sr.No.</th>
            <th style={{ width: 55 }}>Rank</th>
            <th style={{ minWidth: 180 }}>Name</th>
            <th style={{ width: 70 }}>Emp. No.</th>
            <th style={{ width: 90 }}>Nationality</th>
            <th style={{ width: 100 }}>E/F Travel Date</th>
            <th style={{ width: 95 }}>Sign On Date</th>
            <th style={{ width: 95 }}>Relief Due</th>
            <th style={{ minWidth: 170 }}>Reliever - Rank : Name</th>
            <th style={{ width: 110, backgroundColor: '#1e3a8a' }}>AI Compliance</th>
            <th style={{ width: 130 }}>Checklist</th>
          </tr>
        </thead>
        <tbody>
          {crew.map(member => (
            <tr key={member.id}>
              <td className="text-center">
                <input
                  aria-label={`Select ${member.name}`}
                  type="checkbox"
                  checked={selectedIds.has(member.id)}
                  onChange={() => onToggleSelect(member.id)}
                />
              </td>
              <td className="text-center text-gray-500">{member.srNo}</td>
              <td>
                <span
                  style={{ backgroundColor: '#e8eef5', color: '#2c3e6b', border: '1px solid #c5d3e8' }}
                  className="px-2 py-0.5 rounded text-xs font-semibold"
                >
                  {member.rank}
                </span>
              </td>
              <td>
                <div className="flex items-center gap-1.5">
                  {member.complianceIssue && (
                    <span title="Compliance issue" style={{ color: '#e74c3c' }}>
                      <AlertCircle size={13} />
                    </span>
                  )}
                  <button
                    onClick={() => navigate(`/seafarer/${member.id}`)}
                    title="Open seafarer profile"
                    className="text-blue-600 hover:underline font-medium text-left"
                    style={{ color: '#2980b9' }}
                  >
                    {member.name}
                  </button>
                </div>
              </td>
              <td className="text-gray-600">{member.empNo}</td>
              <td className="text-gray-600">{member.nationality}</td>
              <td className="text-gray-600">{member.travelDate}</td>
              <td className="text-gray-600">{member.signOnDate}</td>
              <td>
                <span style={{ color: isReliefDueSoon(member.reliefDue) ? '#e67e22' : '#444' }}>
                  {member.reliefDue}
                </span>
              </td>
              <td>
                <div className="flex items-center gap-1.5">
                  {member.relieverApproved ? (
                    <CheckCircle2 size={13} style={{ color: '#27ae60' }} />
                  ) : (
                    <span style={{ width: 13 }} />
                  )}
                  <span className="text-gray-600 text-xs">
                    {member.relieverRank} : {member.relieverName}
                  </span>
                </div>
              </td>
              <td className="text-center">
                {aiLoadingId === member.id ? (
                  <div className="flex items-center justify-center gap-1.5">
                    <div className="animate-spin w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full" />
                    <span className="text-xs text-blue-500">Checking...</span>
                  </div>
                ) : (
                  <button
                    onClick={() => onRunAICheck(member.id)}
                    className="flex items-center justify-center gap-1.5 w-full"
                    title="Run AI check"
                  >
                    <TrafficLight status={member.aiStatus} size={12} />
                    <span
                      className="text-xs font-medium"
                      style={{
                        color:
                          member.aiStatus === 'green'
                            ? '#27ae60'
                            : member.aiStatus === 'red'
                              ? '#e74c3c'
                              : '#f39c12',
                      }}
                    >
                      {member.aiStatus === 'green'
                        ? 'Clear'
                        : member.aiStatus === 'red'
                          ? 'Action Req.'
                          : 'Pending'}
                    </span>
                  </button>
                )}
              </td>
              <td className="text-center">
                <div className="flex items-center justify-center gap-1.5">
                  <button
                    onClick={() => onOpenChecklist(member)}
                    className="rounded border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-700 hover:bg-blue-100"
                  >
                    Checklist
                  </button>
                  <ThreeDotMenu member={member} onSelect={item => handleMenuSelect(item, member)} />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-500">
        {selectedCount} crew selected for AI check scope
      </div>
    </div>
  )
}
