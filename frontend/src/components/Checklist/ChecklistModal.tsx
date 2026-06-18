import { useEffect, useState } from 'react'
import { Bot, X } from 'lucide-react'
import { useAuth } from '../../auth'
import type {
  AICheckResult,
  ConfirmationItem,
  CrewMember,
  CrewReport,
  DocumentsData,
  IntegrationStatus,
  PortalVerificationResult,
  SelfServicePacket,
} from '../../types'
import {
  getAuditLog,
  getConfirmation,
  getCrewReport,
  getDocuments,
  getExportChecklistUrl,
  getIntegrationStatus,
  getLatestSelfServiceLink,
  overrideDocumentStatus,
  runAICheck,
  sendSelfServiceLink,
  updateConfirmationItem,
  updateDocumentRemark,
  uploadDocumentAttachment,
  verifyPortal,
  verifyPortalBatch,
} from '../../api'
import TrafficLight from '../Common/TrafficLight'
import AIPanel from './AIPanel'
import AuditLogPanel from './AuditLogPanel'
import DepartureOpsTab from './DepartureOpsTab'
import EvidencePanel from './EvidencePanel'
import PreDepartureTab from './PreDepartureTab'
import SeafarerConfirmationTab from './SeafarerConfirmationTab'

interface Props {
  member: CrewMember
  onClose: () => void
}

const TABS = ['Pre Departure', 'Seafarer Confirmation', 'Departure (Ops)']

function applyVerificationResult(currentDocs: DocumentsData, result: PortalVerificationResult): DocumentsData {
  const nextSections = currentDocs.sections.map(section => ({
    ...section,
    items: section.items.map(item =>
      item.name === result.docName
        ? {
            ...item,
            verifiedOps: result.verified,
            portalVerified: result.verified,
            aiStatus: result.verified && item.aiStatus === 'yellow' ? 'green' : item.aiStatus,
          }
        : item,
    ),
  }))

  const allItems = nextSections.flatMap(section => section.items)

  return {
    ...currentDocs,
    sections: nextSections,
    summary: {
      ...currentDocs.summary,
      pendingVerification: allItems.filter(item => item.aiStatus === 'yellow' && !item.missing).length,
      valid: allItems.filter(item => item.aiStatus === 'green' && item.required !== false).length,
    },
  }
}

export default function ChecklistModal({ member, onClose }: Props) {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState(0)
  const [docs, setDocs] = useState<DocumentsData | null>(null)
  const [confirmation, setConfirmation] = useState<ConfirmationItem[] | null>(null)
  const [aiResult, setAiResult] = useState<AICheckResult | null>(null)
  const [report, setReport] = useState<CrewReport | null>(null)
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null)
  const [auditEntries, setAuditEntries] = useState<CrewReport['auditLog']>([])
  const [latestLink, setLatestLink] = useState<SelfServicePacket | null>(null)
  const [verificationResults, setVerificationResults] = useState<Record<string, PortalVerificationResult>>({})
  const [verifyingDoc, setVerifyingDoc] = useState<string | null>(null)
  const [uploadingSrNo, setUploadingSrNo] = useState<number | null>(null)
  const [portalSummary, setPortalSummary] = useState<string | null>(null)
  const [infoMessage, setInfoMessage] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [portalRunning, setPortalRunning] = useState(false)
  const [sendingLink, setSendingLink] = useState(false)
  const [savingEditor, setSavingEditor] = useState(false)
  const [loading, setLoading] = useState(true)
  const [inlineEditor, setInlineEditor] = useState<{
    srNo: number
    name: string
    remarkValue: string
    overrideStatus: 'green' | 'yellow' | 'red'
    overrideReason: string
  } | null>(null)
  const [confirmationEditor, setConfirmationEditor] = useState<{
    srNo: number
    description: string
    verifyOps: boolean
    officeRemark: string
  } | null>(null)

  const activeStatus = aiResult?.overallStatus ?? member.aiStatus
  const canEditRemark = !!user && ['rc', 'ops', 'admin'].includes(user.role)
  const canOverride = !!user && ['ops', 'admin'].includes(user.role)
  const canSendSelfService = !!user && ['rc', 'admin'].includes(user.role)
  const canUpload = !!user && ['rc', 'ops', 'admin'].includes(user.role)
  const canUpdateOps = !!user && ['ops', 'admin'].includes(user.role)

  const refreshSideData = async () => {
    const [reportResponse, auditResponse, linkResponse, integrationResponse] = await Promise.all([
      getCrewReport(member.id),
      getAuditLog(member.id),
      getLatestSelfServiceLink(member.id),
      getIntegrationStatus(),
    ])
    setReport(reportResponse)
    setAuditEntries(auditResponse)
    setLatestLink(linkResponse)
    setIntegrationStatus(integrationResponse)
  }

  const refreshCoreData = async () => {
    const [documentsData, confirmationData] = await Promise.all([
      getDocuments(member.id),
      getConfirmation(member.id),
    ])
    setDocs(documentsData)
    setConfirmation(confirmationData)
  }

  useEffect(() => {
    setLoading(true)
    Promise.all([refreshCoreData(), refreshSideData()]).finally(() => setLoading(false))
  }, [member.id])

  useEffect(() => {
    if (!loading) {
      void handleAICheck()
    }
  }, [loading])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  const handleAICheck = async () => {
    setAiLoading(true)
    try {
      const result = await runAICheck(member.id)
      setAiResult(result)
      await Promise.all([refreshCoreData(), refreshSideData()])
    } finally {
      setAiLoading(false)
    }
  }

  const handleVerifyDocument = async (docName: string, docNo: string) => {
    setVerifyingDoc(docName)
    try {
      const result = await verifyPortal(member.id, docName, docNo)
      setVerificationResults(previous => ({ ...previous, [docName]: result }))
      setPortalSummary(result.message)
      setDocs(previous => (previous ? applyVerificationResult(previous, result) : previous))
      await handleAICheck()
    } finally {
      setVerifyingDoc(null)
    }
  }

  const handleRunPortalVerification = async () => {
    setPortalRunning(true)
    setPortalSummary(null)
    try {
      const batch = await verifyPortalBatch(member.id)
      setVerificationResults(previous => {
        const next = { ...previous }
        batch.results.forEach(result => {
          next[result.docName] = result
        })
        return next
      })
      setPortalSummary(
        `Portal verification complete: ${batch.verifiedCount} verified, ${batch.manualCount} routed to official portals, ${batch.failedCount} failed.`,
      )
      await handleAICheck()
    } finally {
      setPortalRunning(false)
    }
  }

  const handleSaveRemark = async () => {
    if (!inlineEditor) {
      return
    }
    setSavingEditor(true)
    try {
      await updateDocumentRemark(member.id, inlineEditor.srNo, inlineEditor.remarkValue, user?.fullName ?? 'RC Team')
      await Promise.all([refreshCoreData(), refreshSideData()])
      setInfoMessage('Remark saved and added to the audit trail.')
    } finally {
      setSavingEditor(false)
    }
  }

  const handleSaveOverride = async () => {
    if (!inlineEditor) {
      return
    }
    setSavingEditor(true)
    try {
      await overrideDocumentStatus(
        member.id,
        inlineEditor.srNo,
        inlineEditor.overrideStatus,
        inlineEditor.overrideReason,
        user?.fullName ?? 'Ops Team',
      )
      await handleAICheck()
      setInfoMessage('AI override recorded for learning feedback and audit.')
    } finally {
      setSavingEditor(false)
    }
  }

  const handleSaveConfirmation = async () => {
    if (!confirmationEditor) {
      return
    }
    setSavingEditor(true)
    try {
      await updateConfirmationItem(
        member.id,
        confirmationEditor.srNo,
        confirmationEditor.verifyOps,
        confirmationEditor.officeRemark,
      )
      setConfirmationEditor(null)
      await Promise.all([refreshCoreData(), refreshSideData()])
      setInfoMessage('Departure Ops item updated successfully.')
    } finally {
      setSavingEditor(false)
    }
  }

  const handleSendToSeafarer = async () => {
    setSendingLink(true)
    try {
      const packet = await sendSelfServiceLink(member.id, user?.fullName ?? 'RC Team')
      setLatestLink(packet)
      await refreshSideData()
      setInfoMessage('Self-service approval link generated and ready to share.')
    } finally {
      setSendingLink(false)
    }
  }

  const handleUploadAttachment = async (srNo: number, file: File) => {
    setUploadingSrNo(srNo)
    try {
      await uploadDocumentAttachment(member.id, srNo, file)
      await Promise.all([refreshCoreData(), refreshSideData()])
      await handleAICheck()
      setInfoMessage(`${file.name} uploaded successfully and re-checked against the vessel matrix.`)
    } finally {
      setUploadingSrNo(null)
    }
  }

  const handleExportPdf = () => {
    window.open(getExportChecklistUrl(member.id), '_blank', 'noopener,noreferrer')
  }

  const closeEditors = () => {
    setInlineEditor(null)
    setConfirmationEditor(null)
  }

  return (
    <div className="modal-overlay" onClick={event => { if (event.target === event.currentTarget) onClose() }}>
      <div
        style={{
          background: 'white',
          borderRadius: 6,
          boxShadow: '0 8px 40px rgba(0,0,0,0.25)',
          width: '95vw',
          maxWidth: 1280,
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div style={{ backgroundColor: '#1a2a4a' }} className="flex items-center justify-between px-5 py-3 flex-shrink-0">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-white font-bold text-base">{member.name}</span>
              <span style={{ backgroundColor: '#2c3e6b', border: '1px solid #3d5491' }} className="text-blue-200 text-xs px-2 py-0.5 rounded">
                {member.rank}
              </span>
              <span className="text-blue-300 text-xs">|</span>
              <span className="text-blue-300 text-xs">{member.empNo}</span>
              <TrafficLight status={activeStatus} size={11} />
            </div>
            <div className="mt-1">
              <span
                style={{ backgroundColor: '#2c3e6b', border: '1px solid #3d5491', borderRadius: 20 }}
                className="text-xs text-blue-200 px-3 py-1 inline-flex items-center gap-2"
              >
                <span>Vessel Proposed: <strong className="text-white">ALKEBULAN</strong></span>
                <span>|</span>
                <span>Travel Readiness date: <strong className="text-white">{member.travelDate}</strong></span>
              </span>
            </div>
          </div>
          <button onClick={onClose} className="text-blue-300 hover:text-white p-1">
            <X size={20} />
          </button>
        </div>

        <div style={{ backgroundColor: '#162240', borderBottom: '1px solid #0d1a33' }} className="flex flex-shrink-0">
          {TABS.map((tab, index) => (
            <button
              key={tab}
              onClick={() => setActiveTab(index)}
              style={
                activeTab === index
                  ? { borderBottom: '3px solid #2980b9', color: '#fff' }
                  : { borderBottom: '3px solid transparent', color: '#93b4d9' }
              }
              className="px-5 py-2.5 text-xs font-medium hover:text-white transition-colors"
            >
              {tab}
              {index === 0 && docs && docs.summary.missing > 0 && (
                <span style={{ backgroundColor: '#e74c3c', color: 'white', borderRadius: 10, fontSize: 10, padding: '1px 5px', marginLeft: 6 }}>
                  {docs.summary.missing}
                </span>
              )}
            </button>
          ))}
          <div className="flex-1" />
          <button
            onClick={() => void handleAICheck()}
            disabled={aiLoading}
            style={{ backgroundColor: '#1e4d8c', color: 'white', border: 'none', margin: '4px 12px', borderRadius: 4, padding: '0 12px', fontSize: 11, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5 }}
          >
            <Bot size={13} />
            {aiLoading ? 'Running...' : 'AI Check'}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center p-12 text-gray-400">
              <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mr-3" />
              Loading checklist...
            </div>
          ) : (
            <div className="p-4 space-y-4">
              {infoMessage && (
                <div className="rounded border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
                  {infoMessage}
                </div>
              )}

              {confirmationEditor && (
                <div className="rounded border border-slate-200 bg-slate-50 p-4">
                  <div className="grid gap-3">
                    <div className="text-sm font-semibold text-slate-900">Update Departure Ops Item</div>
                    <div className="text-xs text-slate-500">{confirmationEditor.description}</div>
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={confirmationEditor.verifyOps}
                        onChange={event => setConfirmationEditor({ ...confirmationEditor, verifyOps: event.target.checked })}
                      />
                      Mark as verified by Ops
                    </label>
                    <textarea
                      value={confirmationEditor.officeRemark}
                      onChange={event => setConfirmationEditor({ ...confirmationEditor, officeRemark: event.target.value })}
                      rows={4}
                      placeholder="Add Ops remarks"
                      className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                    />
                    <div className="flex justify-end gap-2">
                      <button className="rounded border border-slate-300 px-3 py-2 text-sm" onClick={closeEditors}>Cancel</button>
                      <button className="rounded bg-slate-900 px-3 py-2 text-sm text-white" disabled={savingEditor} onClick={() => void handleSaveConfirmation()}>
                        {savingEditor ? 'Saving...' : 'Save Ops Update'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 0 && (
                <>
                  <AIPanel
                    result={aiResult}
                    loading={aiLoading}
                    portalRunning={portalRunning}
                    portalSummary={portalSummary}
                    integrationStatus={integrationStatus}
                    crewName={member.name}
                    rank={member.rank}
                    onRunCheck={() => void handleAICheck()}
                    onRunPortalVerification={() => void handleRunPortalVerification()}
                    onExportPdf={handleExportPdf}
                  />
                  <EvidencePanel report={report} />
                </>
              )}

              {activeTab === 0 && docs && (
                <PreDepartureTab
                  data={docs}
                  approvedBy={activeStatus === 'green' ? 'S. Patil on 17-Jun-2026 10:30' : undefined}
                  verifyingDoc={verifyingDoc}
                  uploadingSrNo={uploadingSrNo}
                  savingEditor={savingEditor}
                  verificationResults={verificationResults}
                  onVerifyDocument={handleVerifyDocument}
                  inlineEditor={inlineEditor}
                  onOpenInlineEditor={({ srNo, name, currentRemark, currentStatus }) => {
                    setConfirmationEditor(null)
                    setInlineEditor(current =>
                      current?.srNo === srNo
                        ? null
                        : {
                            srNo,
                            name,
                            remarkValue: currentRemark,
                            overrideStatus: currentStatus,
                            overrideReason: '',
                          },
                    )
                  }}
                  onCloseInlineEditor={() => setInlineEditor(null)}
                  onInlineRemarkChange={value =>
                    setInlineEditor(current => (current ? { ...current, remarkValue: value } : current))
                  }
                  onInlineOverrideStatusChange={status =>
                    setInlineEditor(current => (current ? { ...current, overrideStatus: status } : current))
                  }
                  onInlineOverrideReasonChange={value =>
                    setInlineEditor(current => (current ? { ...current, overrideReason: value } : current))
                  }
                  onSaveRemark={() => void handleSaveRemark()}
                  onSaveOverride={() => void handleSaveOverride()}
                  onUploadAttachment={(srNo, file) => void handleUploadAttachment(srNo, file)}
                  canEditRemark={canEditRemark}
                  canOverride={canOverride}
                  canUpload={canUpload}
                />
              )}

              {activeTab === 1 && confirmation && (
                <SeafarerConfirmationTab
                  items={confirmation}
                  sending={sendingLink}
                  latestLink={latestLink}
                  onSend={() => void handleSendToSeafarer()}
                  canSend={canSendSelfService}
                />
              )}

              {activeTab === 2 && confirmation && (
                <DepartureOpsTab
                  items={confirmation}
                  canEdit={canUpdateOps}
                  onEdit={item => {
                    closeEditors()
                    setConfirmationEditor({
                      srNo: item.srNo,
                      description: item.description,
                      verifyOps: item.verifyOps,
                      officeRemark: item.officeRemark,
                    })
                  }}
                />
              )}

              <AuditLogPanel entries={auditEntries} />
            </div>
          )}
        </div>

        <div style={{ backgroundColor: '#f7fafd', borderTop: '1px solid #dde3ec' }} className="px-5 py-2.5 flex items-center justify-between flex-shrink-0">
          <span className="text-xs text-gray-500">
            Pre-Joining Checklist - {member.name} ({member.rank}) | ALKEBULAN
          </span>
          <div className="flex gap-2">
            <button
              style={{ border: '1px solid #dde3ec', borderRadius: 4, padding: '5px 14px', fontSize: 12, cursor: 'pointer', backgroundColor: 'white', color: '#555' }}
              onClick={onClose}
            >
              Close
            </button>
            <button
              onClick={handleExportPdf}
              style={{ backgroundColor: '#2c3e6b', color: 'white', border: 'none', borderRadius: 4, padding: '5px 14px', fontSize: 12, cursor: 'pointer' }}
            >
              Export PDF
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
