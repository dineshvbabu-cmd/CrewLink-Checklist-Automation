import { Fragment, useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, Paperclip } from 'lucide-react'
import type { DocumentsData, DocumentItem, PortalVerificationResult, PortalStatus, AttachmentStatus, MatrixStatus } from '../../types'
import TrafficLight from '../Common/TrafficLight'

const STATUS_LABELS: Record<'green' | 'yellow' | 'red', string> = {
  green: 'Good',
  yellow: 'Pending',
  red: 'Missing',
}

function attachmentPresentation(status?: AttachmentStatus, detail?: string) {
  switch (status) {
    case 'available':
      return { color: '#27ae60', label: 'Complete', detail: detail || 'Attachment and dates are valid' }
    case 'expired':
      return { color: '#e74c3c', label: 'Expired', detail: detail || 'Attached document has expired' }
    default:
      return { color: '#e74c3c', label: 'Missing', detail: detail || 'No usable attachment evidence found' }
  }
}

function matrixPresentation(status?: MatrixStatus, detail?: string) {
  switch (status) {
    case 'required':
      return { color: '#2563eb', label: 'Required', detail: detail || 'Required by vessel matrix' }
    default:
      return { color: '#64748b', label: 'Not required', detail: detail || 'Not required by vessel matrix' }
  }
}

function portalPresentation(status: PortalStatus | undefined, result?: PortalVerificationResult, detail?: string) {
  if (result?.verified) {
    return { color: '#27ae60', label: 'Verified', detail: result.message }
  }

  switch (status) {
    case 'verified':
      return { color: '#27ae60', label: 'Verified', detail: detail || 'Portal verification completed' }
    case 'pending':
      return { color: '#e67e22', label: 'Pending auto check', detail: detail || 'Ready for portal automation' }
    case 'manual_review':
      return { color: '#f39c12', label: 'Pending manual review', detail: detail || 'External portal review required' }
    case 'blocked':
      return { color: '#c2410c', label: 'Blocked', detail: detail || 'Finish checklist review first' }
    default:
      return { color: '#64748b', label: 'Not applicable', detail: detail || 'No supported public portal' }
  }
}

function confidenceLabel(score?: number) {
  if (typeof score !== 'number') {
    return '-'
  }
  return `${Math.round(score * 100)}%`
}

function statusLabel(status?: string) {
  if (status === 'green') return 'Good'
  if (status === 'yellow') return 'Pending'
  if (status === 'red') return 'Missing'
  return '-'
}

interface Props {
  data: DocumentsData
  approvedBy?: string
  verifyingDoc: string | null
  uploadingSrNo: number | null
  savingEditor: boolean
  verificationResults: Record<string, PortalVerificationResult>
  onVerifyDocument: (docName: string, docNo: string) => void
  inlineEditor: {
    srNo: number
    name: string
    rcRemark: string
    opsRemark: string
    rcOverrideStatus: 'green' | 'yellow' | 'red'
    rcOverrideReason: string
    opsOverrideStatus: 'green' | 'yellow' | 'red'
    opsOverrideReason: string
    manualVerified: boolean
    manualRemark: string
  } | null
  onOpenInlineEditor: (payload: { item: DocumentItem }) => void
  onCloseInlineEditor: () => void
  onInlineRemarkChange: (channel: 'rc' | 'ops', value: string) => void
  onInlineOverrideStatusChange: (channel: 'rc' | 'ops', status: 'green' | 'yellow' | 'red') => void
  onInlineOverrideReasonChange: (channel: 'rc' | 'ops', value: string) => void
  onInlineManualVerifiedChange: (value: boolean) => void
  onInlineManualRemarkChange: (value: string) => void
  onSaveRemark: (channel: 'rc' | 'ops') => void
  onSaveOverride: (channel: 'rc' | 'ops') => void
  onSaveManualVerification: () => void
  onUploadAttachment: (srNo: number, file: File) => void
  canEditRemark: boolean
  canRcOverride: boolean
  canOpsOverride: boolean
  canUpload: boolean
  canManualVerify: boolean
  userRole?: 'admin' | 'rc' | 'ops'
}

export default function PreDepartureTab({
  data,
  approvedBy,
  verifyingDoc,
  uploadingSrNo,
  savingEditor,
  verificationResults,
  onVerifyDocument,
  inlineEditor,
  onOpenInlineEditor,
  onCloseInlineEditor,
  onInlineRemarkChange,
  onInlineOverrideStatusChange,
  onInlineOverrideReasonChange,
  onInlineManualVerifiedChange,
  onInlineManualRemarkChange,
  onSaveRemark,
  onSaveOverride,
  onSaveManualVerification,
  onUploadAttachment,
  canEditRemark,
  canRcOverride,
  canOpsOverride,
  canUpload,
  canManualVerify,
  userRole,
}: Props) {
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({})

  useEffect(() => {
    setCollapsedSections(current => {
      const next = { ...current }
      data.sections.forEach(section => {
        if (!(section.title in next)) {
          next[section.title] = false
        }
      })
      return next
    })
  }, [data.sections])

  const setAllSectionsCollapsed = (collapsed: boolean) => {
    const next: Record<string, boolean> = {}
    data.sections.forEach(section => {
      next[section.title] = collapsed
    })
    setCollapsedSections(next)
  }

  let srCounter = 0

  return (
    <div>
      {approvedBy && (
        <div className="px-4 py-2" style={{ backgroundColor: '#f0faf4', borderBottom: '1px solid #c3e6cb' }}>
          <span style={{ color: '#27ae60' }} className="text-xs font-semibold">
            RC checklist approved by: {approvedBy}
          </span>
        </div>
      )}

      <div className="grid gap-3 px-4 py-3 md:grid-cols-2" style={{ backgroundColor: '#f8fbff', borderBottom: '1px solid #dbe7f3' }}>
        <div className="rounded border border-blue-100 bg-white px-3 py-2">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Checklist Check</div>
          <div className="mt-1 text-xs text-slate-700">
            Step 1: confirm attachment exists and expiry is valid.
          </div>
        </div>
        <div className="rounded border border-indigo-100 bg-white px-3 py-2">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Matrix Requirement</div>
          <div className="mt-1 text-xs text-slate-700">
            Step 2: confirm whether the document is actually required for this rank and vessel.
          </div>
        </div>
        <div className="rounded border border-amber-100 bg-white px-3 py-2 md:col-span-2">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Portal Verification</div>
          <div className="mt-1 text-xs text-slate-700">
            Step 3: confirm portal verification or existing verification attachment in licenses / courses / documents.
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Checklist sections
        </div>
        <div className="flex items-center gap-2">
          <button
            className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50"
            onClick={() => setAllSectionsCollapsed(false)}
            type="button"
          >
            Expand all
          </button>
          <button
            className="rounded border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50"
            onClick={() => setAllSectionsCollapsed(true)}
            type="button"
          >
            Collapse all
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="crewlink-table">
          <thead>
            <tr>
              <th style={{ width: 40 }}>Sr No</th>
              <th style={{ minWidth: 220 }}>Documents</th>
              <th style={{ width: 130 }}>Document No</th>
              <th style={{ width: 80 }}>Type</th>
              <th style={{ width: 95 }}>Issue Date</th>
              <th style={{ width: 95 }}>Expiry Date</th>
              <th style={{ width: 80 }}>Att.</th>
              <th style={{ width: 150 }}>Attachment & Validity</th>
              <th style={{ width: 150 }}>Matrix Requirement</th>
              <th style={{ width: 170 }}>Portal Verification</th>
              <th style={{ width: 85 }}>Confidence</th>
              <th style={{ width: 70 }}>AI</th>
              <th style={{ minWidth: 230 }}>Remarks / Action</th>
            </tr>
          </thead>
          <tbody>
            {data.sections.map(section => (
              <Fragment key={section.title}>
                <tr className="section-header-row">
                  <td colSpan={13} className="!p-0">
                    <button
                      type="button"
                      className="flex w-full items-center justify-between px-4 py-3 text-left"
                      onClick={() =>
                        setCollapsedSections(current => ({
                          ...current,
                          [section.title]: !current[section.title],
                        }))
                      }
                    >
                      <span className="flex items-center gap-3">
                        <span>{section.title}</span>
                        <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                          {section.items.length} items
                        </span>
                      </span>
                      {collapsedSections[section.title] ? (
                        <span className="flex items-center gap-1 text-xs text-slate-600">
                          Expand <ChevronDown size={14} />
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs text-slate-600">
                          Collapse <ChevronUp size={14} />
                        </span>
                      )}
                    </button>
                  </td>
                </tr>
                {!collapsedSections[section.title] && section.items.map(item => {
                  srCounter += 1
                  const isMissing = item.missing
                  const verifyResult = verificationResults[item.name]
                  const isEditorOpen = inlineEditor?.srNo === item.srNo
                  const canShowCombinedEditor =
                    canEditRemark
                    || (canRcOverride && (item.aiStatus === 'red' || item.aiStatus === 'yellow' || !!item.rcOverrideStatus))
                    || (canOpsOverride && (item.aiStatus === 'red' || item.aiStatus === 'yellow' || !!item.opsOverrideStatus))
                    || canManualVerify
                  const displayStatus = item.overrideStatus || item.aiStatus
                  const showRcOverride = canRcOverride && (item.aiStatus === 'red' || item.aiStatus === 'yellow' || !!item.rcOverrideStatus)
                  const showOpsOverride = canOpsOverride && (item.aiStatus === 'red' || item.aiStatus === 'yellow' || !!item.opsOverrideStatus)
                  const attachmentView = attachmentPresentation(item.attachmentStatus, item.attachmentReason)
                  const matrixView = matrixPresentation(item.matrixStatus, item.matrixReason)
                  const portalView = portalPresentation(item.portalStatus, verifyResult, item.portalReason)
                  const portalRoute = item.portalRoute
                  const routeNeedsManualReview = portalRoute?.eligible && !portalRoute?.autoCapable
                  const routeIsUnsupported = portalRoute && portalRoute.eligible === false
                  const canAutoVerify = portalRoute?.autoCapable && item.portalStatus === 'pending'
                  const canMarkManual = canManualVerify && item.portalStatus !== 'verified' && item.required

                  return (
                    <Fragment key={`${section.title}-${item.srNo}`}>
                      <tr className={isMissing ? 'missing-row' : ''}>
                        <td className="text-center text-gray-500">{srCounter}</td>
                        <td>
                          <div className="flex flex-col">
                            <span className={isMissing ? 'font-medium' : ''}>{item.name}</span>
                            {item.required && <span className="text-[10px] text-gray-400">Required by matrix</span>}
                          </div>
                        </td>
                        <td className={`font-mono text-xs ${isMissing ? 'text-orange-400' : 'text-gray-600'}`}>
                          {item.docNo || '-'}
                        </td>
                        <td className="text-gray-500 text-xs">{item.type}</td>
                        <td className={`text-xs ${isMissing ? 'text-orange-400' : 'text-gray-600'}`}>
                          {item.issueDate || '-'}
                        </td>
                        <td className={`text-xs ${isMissing ? 'text-orange-400' : 'text-gray-600'}`}>
                          {item.expiryDate || '-'}
                        </td>
                        <td className="text-center">
                          <div className="flex items-center justify-center gap-2">
                            {!isMissing && item.attachmentUrl && (
                              <a href={item.attachmentUrl} target="_blank" rel="noreferrer" title={item.attachmentName || 'View attachment'}>
                                <Paperclip size={13} style={{ color: '#2980b9', cursor: 'pointer' }} />
                              </a>
                            )}
                            {!isMissing && canUpload && (
                              <label className="link-blue text-[10px] cursor-pointer">
                            {uploadingSrNo === item.srNo ? 'Uploading...' : 'Upload'}
                                <input
                                  type="file"
                                  className="hidden"
                                  disabled={uploadingSrNo === item.srNo}
                                  onChange={event => {
                                    const file = event.target.files?.[0]
                                    if (file) {
                                      onUploadAttachment(item.srNo, file)
                                    }
                                    event.target.value = ''
                                  }}
                                />
                              </label>
                            )}
                          </div>
                        </td>
                        <td className="text-center">
                          <div>
                            <div style={{ color: attachmentView.color }} className="text-xs font-semibold">
                              {attachmentView.label}
                            </div>
                            <div className="text-[10px] text-gray-500 leading-tight" style={{ maxWidth: 140 }}>
                              {attachmentView.detail}
                            </div>
                          </div>
                        </td>
                        <td className="text-center">
                          <div>
                            <div style={{ color: matrixView.color }} className="text-xs font-semibold">
                              {matrixView.label}
                            </div>
                            <div className="text-[10px] text-gray-500 leading-tight" style={{ maxWidth: 140 }}>
                              {matrixView.detail}
                            </div>
                          </div>
                        </td>
                        <td>
                          {item.portalEvidenceUrl ? (
                            <div>
                              <span style={{ color: portalView.color }} className="text-xs font-semibold">
                                {portalView.label}
                              </span>
                              <div className="text-xs text-gray-500 leading-tight" style={{ maxWidth: 150 }}>
                                Existing Crewlink verification evidence found.
                              </div>
                              <a
                                href={item.portalEvidenceUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="link-blue text-[10px]"
                              >
                                Open verification attachment
                              </a>
                            </div>
                          ) : verifyResult?.portalUrl ? (
                            <div>
                              <span style={{ color: portalView.color }} className="text-xs font-semibold">
                                {portalView.label}
                              </span>
                              <div className="text-xs text-gray-500 leading-tight" style={{ maxWidth: 150 }}>
                                {portalView.detail}
                              </div>
                              <a
                                href={verifyResult.portalUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="link-blue text-[10px]"
                              >
                                Open {verifyResult.portalLabel || verifyResult.portal}
                              </a>
                            </div>
                          ) : item.portalStatus === 'verified' ? (
                            <div>
                              <span style={{ color: portalView.color }} className="text-xs font-semibold">
                                {portalView.label}
                              </span>
                              <div className="text-xs text-gray-500 leading-tight" style={{ maxWidth: 150 }}>
                                {portalView.detail}
                              </div>
                            </div>
                          ) : item.portalStatus === 'manual_review' || routeNeedsManualReview ? (
                            <div>
                              <span style={{ color: portalView.color }} className="text-xs font-semibold">
                                {portalView.label}
                              </span>
                              <div className="text-xs text-gray-500 leading-tight" style={{ maxWidth: 150 }}>
                                {portalRoute?.portalLabel || portalView.detail}
                              </div>
                              {portalRoute?.portalUrl && (
                                <a href={portalRoute.portalUrl} target="_blank" rel="noreferrer" className="link-blue text-[10px]">
                                  Open portal
                                </a>
                              )}
                            </div>
                          ) : item.portalStatus === 'not_applicable' || routeIsUnsupported ? (
                            <div>
                              <span style={{ color: portalView.color }} className="text-xs font-semibold">
                                {portalView.label}
                              </span>
                              <div className="text-xs text-gray-500 leading-tight" style={{ maxWidth: 150 }}>
                                {portalView.detail}
                              </div>
                            </div>
                          ) : item.portalStatus === 'blocked' ? (
                            <div>
                              <span style={{ color: portalView.color }} className="text-xs font-semibold">
                                {portalView.label}
                              </span>
                              <div className="text-xs text-gray-500 leading-tight" style={{ maxWidth: 150 }}>
                                {portalView.detail}
                              </div>
                            </div>
                          ) : canAutoVerify ? (
                            <div className="flex flex-col gap-1">
                              <button
                                onClick={() => onVerifyDocument(item.name, item.docNo)}
                                disabled={verifyingDoc === item.name}
                                className="link-blue text-xs hover:underline text-left"
                              >
                                {verifyingDoc === item.name ? (
                                  <span className="flex items-center gap-1">
                                    <span className="animate-spin inline-block w-2.5 h-2.5 border border-blue-500 border-t-transparent rounded-full" />
                                    Checking...
                                  </span>
                                ) : (
                                  'Run portal check'
                                )}
                              </button>
                              {canMarkManual && (
                                <button
                                  className="link-blue text-[10px] text-left"
                                  onClick={() => onOpenInlineEditor({ item })}
                                >
                                  Manual verify
                                </button>
                              )}
                            </div>
                          ) : verifyResult ? (
                            <div>
                              <span style={{ color: portalView.color }} className="text-xs font-semibold">
                                {portalView.label}
                              </span>
                              <div className="text-xs text-gray-500 leading-tight" style={{ maxWidth: 150 }}>
                                {portalView.detail}
                              </div>
                            </div>
                          ) : (
                            <div className="flex flex-col gap-1">
                              <span className="text-gray-300 text-xs">-</span>
                              {canMarkManual && (
                                <button
                                  className="link-blue text-[10px] text-left"
                                  onClick={() => onOpenInlineEditor({ item })}
                                >
                                  Manual verify
                                </button>
                              )}
                            </div>
                          )}
                        </td>
                        <td className="text-center">
                          <div className="text-xs font-semibold text-slate-700">{confidenceLabel(item.extractionConfidence)}</div>
                          <div className="text-[10px] text-slate-500">AI extraction</div>
                        </td>
                        <td className="text-center">
                          <div className="flex flex-col items-center gap-1">
                            <TrafficLight status={isMissing ? 'red' : (displayStatus as 'green' | 'yellow' | 'red')} size={11} />
                            <span className="text-[10px] font-medium text-slate-500">
                              {STATUS_LABELS[(displayStatus || 'red') as 'green' | 'yellow' | 'red']}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="flex flex-col gap-1">
                            {item.rcRemark ? <span className="text-[11px] text-slate-700">RC: {item.rcRemark}</span> : null}
                            {item.opsRemark ? <span className="text-[11px] text-slate-700">OPS: {item.opsRemark}</span> : null}
                            {!item.rcRemark && !item.opsRemark && (
                              <span className="text-xs text-gray-400 italic">No RC / OPS remark</span>
                            )}
                            {item.systemNote && item.systemNote !== item.statusReason ? (
                              <span className="text-[10px] text-slate-500">System: {item.systemNote}</span>
                            ) : null}
                            {item.statusReason && item.aiStatus === 'yellow' ? (
                              <div className="rounded border border-slate-200 bg-slate-50 px-2 py-1">
                                <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-600">
                                  Pending because
                                </div>
                                <div className="text-xs text-slate-800">{item.statusReason}</div>
                              </div>
                            ) : null}
                            {item.overrideStatus && item.overrideReason && (
                              <div className="rounded border border-amber-200 bg-amber-50 px-2 py-1">
                                <div className="text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                                  AI Override: {STATUS_LABELS[item.overrideStatus as 'green' | 'yellow' | 'red']}
                                </div>
                                <div className="text-xs text-amber-900">{item.overrideReason}</div>
                              </div>
                            )}
                            {item.manualVerificationRemark ? (
                              <div className="rounded border border-emerald-200 bg-emerald-50 px-2 py-1">
                                <div className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
                                  Manual verification
                                </div>
                                <div className="text-xs text-emerald-900">
                                  {item.manualVerificationRemark}
                                  {item.manualVerificationBy ? ` (${item.manualVerificationBy})` : ''}
                                </div>
                              </div>
                            ) : null}
                            <div className="flex gap-2 flex-wrap">
                              {canEditRemark && (
                                <button
                                  className="link-blue text-xs"
                                  onClick={() => onOpenInlineEditor({ item })}
                                >
                                  {isEditorOpen ? 'Hide Editor' : 'Remarks / AI'}
                                </button>
                              )}
                              {showRcOverride && (
                                <button
                                  className="link-blue text-xs"
                                  onClick={() => onOpenInlineEditor({ item })}
                                >
                                  {item.rcOverrideStatus ? 'Edit RC Override' : 'RC Override AI'}
                                </button>
                              )}
                              {showOpsOverride && (
                                <button
                                  className="link-blue text-xs"
                                  onClick={() => onOpenInlineEditor({ item })}
                                >
                                  {item.opsOverrideStatus ? 'Edit OPS Override' : 'OPS Override AI'}
                                </button>
                              )}
                              {canMarkManual && (
                                <button
                                  className="link-blue text-xs"
                                  onClick={() => onOpenInlineEditor({ item })}
                                >
                                  Manual verify
                                </button>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                      {isEditorOpen && inlineEditor && canShowCombinedEditor && (
                        <tr>
                          <td colSpan={13} className="bg-slate-50 px-4 py-4">
                            <div className="grid gap-4 lg:grid-cols-2">
                              {canEditRemark && (
                                <div className="rounded border border-slate-200 bg-white p-4">
                                  <div className="text-sm font-semibold text-slate-900">RC / OPS Remarks</div>
                                  <div className="mt-1 text-xs text-slate-500">{inlineEditor.name}</div>
                                  <div className="mt-3 space-y-4">
                                    <div>
                                      <div className="text-xs font-semibold text-slate-600">RC remark</div>
                                      <textarea
                                        value={inlineEditor.rcRemark}
                                        onChange={event => onInlineRemarkChange('rc', event.target.value)}
                                        rows={3}
                                        className="mt-2 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                                      />
                                      <div className="mt-2 flex justify-end">
                                        <button
                                          className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
                                          disabled={savingEditor || userRole === 'ops'}
                                          onClick={() => onSaveRemark('rc')}
                                        >
                                          {savingEditor ? 'Saving...' : 'Save RC Remark'}
                                        </button>
                                      </div>
                                    </div>
                                    <div>
                                      <div className="text-xs font-semibold text-slate-600">OPS remark</div>
                                      <textarea
                                        value={inlineEditor.opsRemark}
                                        onChange={event => onInlineRemarkChange('ops', event.target.value)}
                                        rows={3}
                                        className="mt-2 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                                      />
                                      <div className="mt-2 flex justify-end">
                                        <button
                                          className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
                                          disabled={savingEditor || userRole === 'rc'}
                                          onClick={() => onSaveRemark('ops')}
                                        >
                                          {savingEditor ? 'Saving...' : 'Save OPS Remark'}
                                        </button>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="mt-3 flex justify-end gap-2">
                                    <button className="rounded border border-slate-300 px-3 py-2 text-sm" onClick={onCloseInlineEditor}>
                                      Close
                                    </button>
                                  </div>
                                </div>
                              )}

                              {(showRcOverride || showOpsOverride || canMarkManual) && (
                                <div className="rounded border border-amber-200 bg-amber-50 p-4">
                                  <div className="text-sm font-semibold text-slate-900">Override / Manual Verification</div>
                                  <div className="mt-1 text-xs text-slate-500">
                                    RC and OPS can keep separate override decisions here. Manual verification is a separate portal activity.
                                  </div>
                                  <div className="mt-3 space-y-4">
                                    {showRcOverride && (
                                      <div className="rounded border border-amber-200 bg-white p-3">
                                        <div className="text-xs font-semibold text-slate-600">RC override AI</div>
                                        <select
                                          value={inlineEditor.rcOverrideStatus}
                                          onChange={event => onInlineOverrideStatusChange('rc', event.target.value as 'green' | 'yellow' | 'red')}
                                          className="mt-2 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                                        >
                                          <option value="green">Good</option>
                                          <option value="yellow">Pending</option>
                                          <option value="red">Missing</option>
                                        </select>
                                        <textarea
                                          value={inlineEditor.rcOverrideReason}
                                          onChange={event => onInlineOverrideReasonChange('rc', event.target.value)}
                                          rows={3}
                                          placeholder="Explain the RC override"
                                          className="mt-2 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                                        />
                                        <div className="mt-2 flex justify-end">
                                          <button
                                            className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
                                            disabled={savingEditor || !inlineEditor.rcOverrideReason.trim()}
                                            onClick={() => onSaveOverride('rc')}
                                          >
                                            {savingEditor ? 'Saving...' : `Save RC Override (${statusLabel(inlineEditor.rcOverrideStatus)})`}
                                          </button>
                                        </div>
                                      </div>
                                    )}
                                    {showOpsOverride && (
                                      <div className="rounded border border-amber-200 bg-white p-3">
                                        <div className="text-xs font-semibold text-slate-600">OPS override AI</div>
                                        <select
                                          value={inlineEditor.opsOverrideStatus}
                                          onChange={event => onInlineOverrideStatusChange('ops', event.target.value as 'green' | 'yellow' | 'red')}
                                          className="mt-2 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                                        >
                                          <option value="green">Good</option>
                                          <option value="yellow">Pending</option>
                                          <option value="red">Missing</option>
                                        </select>
                                        <textarea
                                          value={inlineEditor.opsOverrideReason}
                                          onChange={event => onInlineOverrideReasonChange('ops', event.target.value)}
                                          rows={3}
                                          placeholder="Explain the OPS override"
                                          className="mt-2 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                                        />
                                        <div className="mt-2 flex justify-end">
                                          <button
                                            className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
                                            disabled={savingEditor || !inlineEditor.opsOverrideReason.trim()}
                                            onClick={() => onSaveOverride('ops')}
                                          >
                                            {savingEditor ? 'Saving...' : `Save OPS Override (${statusLabel(inlineEditor.opsOverrideStatus)})`}
                                          </button>
                                        </div>
                                      </div>
                                    )}
                                    {canMarkManual && (
                                      <div className="rounded border border-emerald-200 bg-white p-3">
                                        <div className="text-xs font-semibold text-slate-600">Manual portal verification</div>
                                        <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
                                          <input
                                            type="checkbox"
                                            checked={inlineEditor.manualVerified}
                                            onChange={event => onInlineManualVerifiedChange(event.target.checked)}
                                          />
                                          Mark portal verification as completed manually
                                        </label>
                                        <textarea
                                          value={inlineEditor.manualRemark}
                                          onChange={event => onInlineManualRemarkChange(event.target.value)}
                                          rows={3}
                                          placeholder="Add the manual verification remark or why manual review is recommended"
                                          className="mt-2 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                                        />
                                        <div className="mt-2 flex justify-end">
                                          <button
                                            className="rounded bg-emerald-700 px-3 py-2 text-sm text-white"
                                            disabled={savingEditor}
                                            onClick={onSaveManualVerification}
                                          >
                                            {savingEditor ? 'Saving...' : inlineEditor.manualVerified ? 'Save Manual Verification' : 'Recommend Manual Review'}
                                          </button>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                  <div className="mt-3 flex justify-end gap-2">
                                    <button className="rounded border border-slate-300 px-3 py-2 text-sm" onClick={onCloseInlineEditor}>
                                      Close
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
