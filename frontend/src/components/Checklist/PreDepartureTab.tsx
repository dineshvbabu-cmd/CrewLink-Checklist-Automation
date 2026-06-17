import { Fragment } from 'react'
import { Paperclip } from 'lucide-react'
import type { DocumentsData, PortalVerificationResult } from '../../types'
import TrafficLight from '../Common/TrafficLight'

const STATUS_LABELS: Record<'green' | 'yellow' | 'red', string> = {
  green: 'Good',
  yellow: 'Pending',
  red: 'Missing',
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
    remarkValue: string
    overrideStatus: 'green' | 'yellow' | 'red'
    overrideReason: string
  } | null
  onOpenInlineEditor: (item: {
    srNo: number
    name: string
    currentRemark: string
    currentStatus: 'green' | 'yellow' | 'red'
  }) => void
  onCloseInlineEditor: () => void
  onInlineRemarkChange: (value: string) => void
  onInlineOverrideStatusChange: (status: 'green' | 'yellow' | 'red') => void
  onInlineOverrideReasonChange: (value: string) => void
  onSaveRemark: () => void
  onSaveOverride: () => void
  onUploadAttachment: (srNo: number, file: File) => void
  canEditRemark: boolean
  canOverride: boolean
  canUpload: boolean
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
  onSaveRemark,
  onSaveOverride,
  onUploadAttachment,
  canEditRemark,
  canOverride,
  canUpload,
}: Props) {
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
              <th style={{ width: 75 }}>Verify (RC)</th>
              <th style={{ width: 110 }}>Verify (Ops)</th>
              <th style={{ width: 55 }}>AI</th>
              <th style={{ minWidth: 210 }}>Remarks / Action</th>
            </tr>
          </thead>
          <tbody>
            {data.sections.map(section => (
              <Fragment key={section.title}>
                <tr className="section-header-row">
                  <td colSpan={11}>{section.title}</td>
                </tr>
                {section.items.map(item => {
                  srCounter += 1
                  const isMissing = item.missing
                  const verifyResult = verificationResults[item.name]
                  const isEditorOpen = inlineEditor?.srNo === item.srNo
                  const canShowCombinedEditor =
                    canEditRemark || (canOverride && (item.aiStatus === 'red' || item.aiStatus === 'yellow'))
                  const displayStatus = item.overrideStatus || item.aiStatus
                  const showOverrideSection = canOverride && (item.aiStatus === 'red' || item.aiStatus === 'yellow' || !!item.overrideStatus)

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
                          {item.verifiedRC && !isMissing ? (
                            <span className="tick-verified" title="RC Verified">OK</span>
                          ) : (
                            <span className="text-gray-300 text-xs">-</span>
                          )}
                        </td>
                        <td>
                          {isMissing ? (
                            <span className="text-gray-400 text-xs">-</span>
                          ) : item.verifiedOps ? (
                            <span className="tick-verified" title="Ops Verified">OK</span>
                          ) : verifyResult ? (
                            <div>
                              <span
                                style={{ color: verifyResult.verified ? '#27ae60' : '#e74c3c' }}
                                className="text-xs"
                              >
                                {verifyResult.verified ? 'Verified' : 'Not found'}
                              </span>
                              <div className="text-xs text-gray-500 leading-tight" style={{ maxWidth: 120 }}>
                                {verifyResult.message}
                              </div>
                            </div>
                          ) : (
                            <button
                              onClick={() => onVerifyDocument(item.name, item.docNo)}
                              disabled={verifyingDoc === item.name}
                              className="link-blue text-xs hover:underline"
                            >
                              {verifyingDoc === item.name ? (
                                <span className="flex items-center gap-1">
                                  <span className="animate-spin inline-block w-2.5 h-2.5 border border-blue-500 border-t-transparent rounded-full" />
                                  Checking...
                                </span>
                              ) : (
                                'Verify'
                              )}
                            </button>
                          )}
                        </td>
                        <td className="text-center">
                          <div className="flex flex-col items-center gap-1">
                            <TrafficLight status={isMissing ? 'red' : item.aiStatus} size={11} />
                            <span className="text-[10px] font-medium text-slate-500">
                              {STATUS_LABELS[(displayStatus || 'red') as 'green' | 'yellow' | 'red']}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="flex flex-col gap-1">
                            {item.remark ? (
                              <span style={{ color: isMissing ? '#e67e22' : '#555' }} className="text-xs italic">
                                {item.remark}
                              </span>
                            ) : (
                              <span className="text-xs text-gray-400 italic">No remark</span>
                            )}
                            {item.overrideStatus && item.overrideReason && (
                              <div className="rounded border border-amber-200 bg-amber-50 px-2 py-1">
                                <div className="text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                                  AI Override: {STATUS_LABELS[item.overrideStatus as 'green' | 'yellow' | 'red']}
                                </div>
                                <div className="text-xs text-amber-900">{item.overrideReason}</div>
                              </div>
                            )}
                            <div className="flex gap-2 flex-wrap">
                              {canEditRemark && (
                                <button
                                  className="link-blue text-xs"
                                  onClick={() =>
                                    onOpenInlineEditor({
                                      srNo: item.srNo,
                                      name: item.name,
                                      currentRemark: item.remark,
                                      currentStatus: item.aiStatus,
                                    })
                                  }
                                >
                                  {isEditorOpen ? 'Hide Editor' : item.remark ? 'Edit Remark' : 'Add Remark'}
                                </button>
                              )}
                              {showOverrideSection && (
                                <button
                                  className="link-blue text-xs"
                                  onClick={() =>
                                    onOpenInlineEditor({
                                      srNo: item.srNo,
                                      name: item.name,
                                      currentRemark: item.remark,
                                      currentStatus: (item.overrideStatus || item.aiStatus) as 'green' | 'yellow' | 'red',
                                    })
                                  }
                                >
                                  {item.overrideStatus ? 'Edit Override AI' : 'Override AI'}
                                </button>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                      {isEditorOpen && inlineEditor && canShowCombinedEditor && (
                        <tr>
                          <td colSpan={11} className="bg-slate-50 px-4 py-4">
                            <div className={`grid gap-4 ${showOverrideSection ? 'lg:grid-cols-2' : 'grid-cols-1'}`}>
                              {canEditRemark && (
                                <div className="rounded border border-slate-200 bg-white p-4">
                                  <div className="text-sm font-semibold text-slate-900">Remark</div>
                                  <div className="mt-1 text-xs text-slate-500">{inlineEditor.name}</div>
                                  <textarea
                                    value={inlineEditor.remarkValue}
                                    onChange={event => onInlineRemarkChange(event.target.value)}
                                    rows={4}
                                    className="mt-3 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                                  />
                                  <div className="mt-3 flex justify-end gap-2">
                                    <button className="rounded border border-slate-300 px-3 py-2 text-sm" onClick={onCloseInlineEditor}>
                                      Close
                                    </button>
                                    <button
                                      className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
                                      disabled={savingEditor}
                                      onClick={onSaveRemark}
                                    >
                                      {savingEditor ? 'Saving...' : 'Save Remark'}
                                    </button>
                                  </div>
                                </div>
                              )}

                              {showOverrideSection && (
                                <div className="rounded border border-amber-200 bg-amber-50 p-4">
                                  <div className="text-sm font-semibold text-slate-900">AI Override</div>
                                  <div className="mt-1 text-xs text-slate-500">
                                    Set the AI outcome clearly as Good, Pending, or Missing and record the reason.
                                  </div>
                                  <select
                                    value={inlineEditor.overrideStatus}
                                    onChange={event => onInlineOverrideStatusChange(event.target.value as 'green' | 'yellow' | 'red')}
                                    className="mt-3 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                                  >
                                    <option value="green">Good</option>
                                    <option value="yellow">Pending</option>
                                    <option value="red">Missing</option>
                                  </select>
                                  <textarea
                                    value={inlineEditor.overrideReason}
                                    onChange={event => onInlineOverrideReasonChange(event.target.value)}
                                    rows={4}
                                    placeholder="Explain why the AI status is being overridden"
                                    className="mt-3 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                                  />
                                  <div className="mt-3 flex justify-end gap-2">
                                    <button className="rounded border border-slate-300 px-3 py-2 text-sm" onClick={onCloseInlineEditor}>
                                      Close
                                    </button>
                                    <button
                                      className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
                                      disabled={savingEditor || !inlineEditor.overrideReason.trim()}
                                      onClick={onSaveOverride}
                                    >
                                      {savingEditor ? 'Saving...' : 'Save Override'}
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
