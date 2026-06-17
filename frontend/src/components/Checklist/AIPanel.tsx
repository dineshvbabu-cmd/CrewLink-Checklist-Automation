import { useState } from 'react'
import { Bot, ChevronDown, ChevronUp, Download, RefreshCw } from 'lucide-react'
import type { AICheckResult, IntegrationStatus } from '../../types'
import TrafficLight from '../Common/TrafficLight'

interface Props {
  result: AICheckResult | null
  loading: boolean
  portalRunning: boolean
  portalSummary: string | null
  integrationStatus: IntegrationStatus | null
  crewName: string
  rank: string
  onRunCheck: () => void
  onRunPortalVerification: () => void
  onExportPdf: () => void
}

function downloadTextReport(result: AICheckResult) {
  const report = [
    `AI Compliance Summary - ${result.name}`,
    `${result.rank} | ${result.vessel} | ${result.flag}`,
    '',
    `Valid and verified: ${result.summary.valid}`,
    `Pending portal verification: ${result.summary.pendingVerification}`,
    `Missing: ${result.summary.missing}`,
    `Expired: ${result.summary.expired}`,
    '',
    `Missing items: ${result.missingItems.join(', ') || 'None'}`,
    `Pending items: ${result.pendingItems.join(', ') || 'None'}`,
    `Expired items: ${result.expiredItems.join(', ') || 'None'}`,
    '',
    result.aiNarrative,
  ].join('\n')

  const blob = new Blob([report], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${result.name.replace(/\s+/g, '-').toLowerCase()}-ai-report.txt`
  link.click()
  URL.revokeObjectURL(url)
}

export default function AIPanel({
  result,
  loading,
  portalRunning,
  portalSummary,
  integrationStatus,
  crewName,
  rank,
  onRunCheck,
  onRunPortalVerification,
  onExportPdf,
}: Props) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div style={{ border: '1px solid #c5d3e8', borderRadius: 6, marginBottom: 12 }} className="overflow-hidden">
      <div
        style={{ backgroundColor: '#1a2a4a' }}
        className="flex items-center justify-between px-4 py-2.5 cursor-pointer"
        onClick={() => setCollapsed(current => !current)}
      >
        <div className="flex items-center gap-2 text-white">
          <Bot size={16} className="text-blue-300" />
          <span className="font-semibold text-sm">AI Compliance Summary</span>
          <span className="text-blue-300 text-xs">- {crewName} ({rank})</span>
        </div>
        <div className="flex items-center gap-3">
          {result && <TrafficLight status={result.overallStatus} size={12} />}
          <button
            onClick={event => {
              event.stopPropagation()
              onRunCheck()
            }}
            className="flex items-center gap-1 text-xs text-blue-300 hover:text-white border border-blue-500 px-2 py-1 rounded"
          >
            <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Analysing...' : 'Run AI Analysis'}
          </button>
          {collapsed ? <ChevronDown size={14} className="text-blue-300" /> : <ChevronUp size={14} className="text-blue-300" />}
        </div>
      </div>

      {!collapsed && (
        <div style={{ backgroundColor: '#f7fafd', padding: '14px 16px' }}>
          {loading ? (
            <div className="flex items-center gap-3 text-gray-500 py-3">
              <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full" />
              <span className="text-sm">Analysing documents against vessel and rank matrix...</span>
            </div>
          ) : result ? (
            <div>
              <div className="flex gap-6 mb-3 flex-wrap">
                <Metric status="green" count={result.summary.valid} label="documents - Valid and verified" />
                <Metric status="yellow" count={result.summary.pendingVerification} label="documents - Portal verification pending" />
                <Metric status="red" count={result.summary.missing} label="items - Missing or expired" />
              </div>

              {result.missingItems.length > 0 && (
                <div className="mb-2">
                  <span style={{ color: '#e74c3c' }} className="font-semibold text-xs">Missing: </span>
                  <span className="text-xs text-gray-700">{result.missingItems.join(' | ')}</span>
                </div>
              )}
              {result.pendingItems.length > 0 && (
                <div className="mb-2">
                  <span style={{ color: '#f39c12' }} className="font-semibold text-xs">Pending: </span>
                  <span className="text-xs text-gray-600">{result.pendingItems.join(' | ')}</span>
                </div>
              )}

              <div style={{ backgroundColor: '#eef4fb', border: '1px solid #c5d8ee', borderRadius: 4 }} className="p-3 mt-2">
                <div className="text-xs text-gray-500 mb-1 font-semibold">AI Assessment</div>
                <p className="text-xs text-gray-700 leading-relaxed m-0">{result.aiNarrative}</p>
              </div>

              <div className="grid md:grid-cols-2 gap-3 mt-3">
                <div className="rounded border border-blue-100 bg-white p-3">
                  <div className="text-xs font-semibold text-gray-500 mb-2">Matrix Coverage</div>
                  <div className="text-sm text-gray-700">
                    {result.matrixDocuments.length}
                    {' '}
                    required documents matched to this rank and vessel.
                  </div>
                </div>
                <div className="rounded border border-blue-100 bg-white p-3">
                  <div className="text-xs font-semibold text-gray-500 mb-2">Extraction Snapshot</div>
                  <div className="text-sm text-gray-700">
                    {result.extractedDocuments.length}
                    {' '}
                    extracted records processed for AI review.
                  </div>
                </div>
              </div>

              {integrationStatus && (
                <div className="mt-3 rounded border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 flex flex-wrap gap-3">
                  <span>
                    Portal mode: <strong>{integrationStatus.portal.mode}</strong>
                  </span>
                  <span>
                    Provider: <strong>{integrationStatus.portal.provider}</strong>
                  </span>
                  <span>
                    Storage: <strong>{integrationStatus.storage.databasePath}</strong>
                  </span>
                </div>
              )}

              {portalSummary && (
                <div className="mt-3 rounded border border-green-200 bg-green-50 px-3 py-2 text-xs text-green-800">
                  {portalSummary}
                </div>
              )}

              <div className="flex gap-2 mt-3 flex-wrap">
                <button
                  onClick={() => downloadTextReport(result)}
                  style={{ backgroundColor: '#2980b9', color: 'white', border: 'none', borderRadius: 4, padding: '5px 12px', fontSize: 12, cursor: 'pointer' }}
                  className="flex items-center gap-1 hover:opacity-90"
                >
                  <Download size={11} />
                  Download AI Notes
                </button>
                <button
                  onClick={onExportPdf}
                  style={{ backgroundColor: '#445d8f', color: 'white', border: 'none', borderRadius: 4, padding: '5px 12px', fontSize: 12, cursor: 'pointer' }}
                  className="hover:opacity-90"
                >
                  Export Checklist PDF
                </button>
                <button
                  onClick={onRunPortalVerification}
                  disabled={portalRunning || result.summary.pendingVerification === 0}
                  style={{ backgroundColor: result.summary.pendingVerification > 0 ? '#e67e22' : '#27ae60', color: 'white', border: 'none', borderRadius: 4, padding: '5px 12px', fontSize: 12, cursor: 'pointer' }}
                  className="hover:opacity-90 disabled:opacity-60"
                >
                  {portalRunning ? 'Running portal verification...' : 'Run Portal Verification'}
                </button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-500 py-2">
              Click <strong>Run AI Analysis</strong> to check all documents against the vessel and rank matrix.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Metric({ status, count, label }: { status: 'green' | 'yellow' | 'red'; count: number; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <TrafficLight status={status} size={11} />
      <span className="text-sm">
        <span className="font-bold text-gray-800">{count}</span>
        <span className="text-gray-500"> {label}</span>
      </span>
    </div>
  )
}
