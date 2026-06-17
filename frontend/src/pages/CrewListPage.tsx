import { useEffect, useMemo, useState } from 'react'
import { Bot, Download, Filter, RefreshCw } from 'lucide-react'
import type { AICheckResult, CrewMember, Vessel } from '../types'
import { getCrew, getVessel, runAICheck } from '../api'
import ChecklistModal from '../components/Checklist/ChecklistModal'
import CrewTable from '../components/CrewList/CrewTable'
import LegendBar from '../components/CrewList/LegendBar'
import VesselHeader from '../components/CrewList/VesselHeader'

const PLACEHOLDER_TAB_COPY: Record<string, string> = {
  'Vessel Particular': 'Vessel particulars panel can be expanded next, but the crew workflow remains the primary demo surface.',
  'Brazil Cabotage': 'Brazil cabotage rules and supporting fields can be layered in later without changing the current AI compliance flow.',
}

const FILTER_SEQUENCE = ['all', 'red', 'yellow', 'green'] as const
type StatusFilter = (typeof FILTER_SEQUENCE)[number]

const FILTER_LABELS: Record<StatusFilter, string> = {
  all: 'All',
  red: 'Action Req.',
  yellow: 'Pending',
  green: 'Clear',
}

export default function CrewListPage() {
  const [vessel, setVessel] = useState<Vessel | null>(null)
  const [crew, setCrew] = useState<CrewMember[]>([])
  const [activeTab, setActiveTab] = useState('Crew List')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [selectedMember, setSelectedMember] = useState<CrewMember | null>(null)
  const [aiLoadingId, setAiLoadingId] = useState<string | null>(null)
  const [aiResults, setAiResults] = useState<Record<string, AICheckResult>>({})
  const [loading, setLoading] = useState(true)
  const [runningAll, setRunningAll] = useState(false)
  const [runningSelected, setRunningSelected] = useState(false)
  const [lastRunTime, setLastRunTime] = useState<string | null>(null)

  const loadData = async () => {
    const [vesselData, crewData] = await Promise.all([getVessel(), getCrew()])
    setVessel(vesselData)
    setCrew(crewData)
    setSelectedIds(previous => {
      if (previous.size === 0) {
        return new Set(crewData.filter(member => member.status === 'planned').map(member => member.id))
      }
      return new Set(crewData.filter(member => previous.has(member.id)).map(member => member.id))
    })
  }

  useEffect(() => {
    loadData()
      .finally(() => setLoading(false))
  }, [])

  const visibleCrew = useMemo(
    () => (statusFilter === 'all' ? crew : crew.filter(member => member.aiStatus === statusFilter)),
    [crew, statusFilter],
  )

  const selectedCrew = useMemo(
    () => crew.filter(member => selectedIds.has(member.id)),
    [crew, selectedIds],
  )

  const runCheckForMember = async (member: CrewMember) => {
    setAiLoadingId(member.id)
    const result = await runAICheck(member.id)
    setAiResults(previous => ({ ...previous, [member.id]: result }))
    setCrew(previous =>
      previous.map(item => (item.id === member.id ? { ...item, aiStatus: result.overallStatus } : item)),
    )
  }

  const handleRunAICheck = async (id: string) => {
    const member = crew.find(item => item.id === id)
    if (!member) {
      return
    }

    try {
      await runCheckForMember(member)
      setLastRunTime(new Date().toLocaleTimeString())
    } finally {
      setAiLoadingId(null)
    }
  }

  const handleRunMany = async (members: CrewMember[], setBusy: (value: boolean) => void) => {
    if (members.length === 0) {
      return
    }

    setBusy(true)
    try {
      for (const member of members) {
        try {
          await runCheckForMember(member)
        } catch {
          // Keep progressing through the selected crew list.
        } finally {
          setAiLoadingId(null)
        }
      }
      setLastRunTime(new Date().toLocaleTimeString())
    } finally {
      setBusy(false)
    }
  }

  const handleRunSelectedAI = async () => {
    await handleRunMany(selectedCrew, setRunningSelected)
  }

  const handleRunAllAI = async () => {
    await handleRunMany(crew.filter(member => member.status === 'planned'), setRunningAll)
  }

  const handleToggleSelect = (id: string) => {
    setSelectedIds(previous => {
      const next = new Set(previous)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleToggleSelectAll = (checked: boolean) => {
    setSelectedIds(checked ? new Set(visibleCrew.map(member => member.id)) : new Set())
  }

  const handleCycleFilter = () => {
    setStatusFilter(previous => FILTER_SEQUENCE[(FILTER_SEQUENCE.indexOf(previous) + 1) % FILTER_SEQUENCE.length])
  }

  const handleRefresh = async () => {
    setLoading(true)
    try {
      await loadData()
    } finally {
      setLoading(false)
    }
  }

  const handleExport = () => {
    const rows = [
      ['Sr No', 'Rank', 'Name', 'Emp No', 'Nationality', 'Travel Date', 'Sign On Date', 'Relief Due', 'AI Status'],
      ...visibleCrew.map(member => [
        String(member.srNo),
        member.rank,
        member.name,
        member.empNo,
        member.nationality,
        member.travelDate,
        member.signOnDate,
        member.reliefDue,
        member.aiStatus,
      ]),
    ]

    const csv = rows
      .map(row => row.map(value => `"${value.replace(/"/g, '""')}"`).join(','))
      .join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `crewlink-checklist-${statusFilter}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  if (loading || !vessel) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mr-3" />
        Loading vessel data...
      </div>
    )
  }

  return (
    <div>
      <VesselHeader vessel={vessel} activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === 'Crew List' ? (
        <>
          <LegendBar vessel={vessel} />

          <div className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={handleRunSelectedAI}
                disabled={runningSelected || selectedCrew.length === 0}
                style={{ backgroundColor: '#1a2a4a' }}
                className="flex items-center gap-1.5 text-white text-xs px-3 py-1.5 rounded hover:opacity-90 disabled:opacity-60"
              >
                <Bot size={13} />
                {runningSelected ? 'Running selected...' : `AI Check Selected (${selectedCrew.length})`}
              </button>
              <button
                onClick={handleRunAllAI}
                disabled={runningAll}
                style={{ backgroundColor: '#2c3e6b' }}
                className="flex items-center gap-1.5 text-white text-xs px-3 py-1.5 rounded hover:opacity-90 disabled:opacity-60"
              >
                <Bot size={13} />
                {runningAll ? 'Running all planned...' : 'Run AI Check (All Planned)'}
              </button>
              {lastRunTime && <span className="text-xs text-gray-400">Last run: {lastRunTime}</span>}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCycleFilter}
                className="flex items-center gap-1 text-xs text-gray-500 border border-gray-300 px-3 py-1.5 rounded hover:bg-gray-50"
              >
                <Filter size={12} />
                Filter: {FILTER_LABELS[statusFilter]}
              </button>
              <button
                onClick={() => void handleRefresh()}
                className="flex items-center gap-1 text-xs text-gray-500 border border-gray-300 px-3 py-1.5 rounded hover:bg-gray-50"
              >
                <RefreshCw size={12} />
                Refresh
              </button>
              <button
                onClick={handleExport}
                className="flex items-center gap-1 text-xs text-gray-500 border border-gray-300 px-3 py-1.5 rounded hover:bg-gray-50"
              >
                <Download size={12} />
                Export
              </button>
            </div>
          </div>

          <div className="bg-white m-3 rounded shadow-sm overflow-hidden border border-gray-200">
            <CrewTable
              crew={visibleCrew}
              selectedIds={selectedIds}
              onToggleSelect={handleToggleSelect}
              onToggleSelectAll={handleToggleSelectAll}
              onOpenChecklist={setSelectedMember}
              aiLoadingId={aiLoadingId}
              onRunAICheck={handleRunAICheck}
            />
          </div>

          {selectedMember && (
            <ChecklistModal
              member={selectedMember}
              onClose={() => setSelectedMember(null)}
            />
          )}
        </>
      ) : (
        <div className="m-4 rounded border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-800 mb-2">{activeTab}</h2>
          <p className="text-sm text-gray-500 m-0">{PLACEHOLDER_TAB_COPY[activeTab]}</p>
        </div>
      )}

      {Object.keys(aiResults).length > 0 && (
        <div className="mx-3 mb-4 rounded border border-blue-100 bg-blue-50 px-4 py-3 text-xs text-blue-900">
          Latest AI statuses:
          {' '}
          {Object.values(aiResults)
            .slice(-3)
            .map(result => `${result.name}: ${result.overallStatus.toUpperCase()}`)
            .join(' | ')}
        </div>
      )}
    </div>
  )
}
