import { Fragment } from 'react'
import { Paperclip } from 'lucide-react'
import type { DocumentsData, PortalVerificationResult } from '../../types'
import TrafficLight from '../Common/TrafficLight'

interface Props {
  data: DocumentsData
  approvedBy?: string
  verifyingDoc: string | null
  verificationResults: Record<string, PortalVerificationResult>
  onVerifyDocument: (docName: string, docNo: string) => void
  onEditRemark: (srNo: number, currentRemark: string) => void
  onOverride: (srNo: number, currentStatus: 'green' | 'yellow' | 'red') => void
}

export default function PreDepartureTab({
  data,
  approvedBy,
  verifyingDoc,
  verificationResults,
  onVerifyDocument,
  onEditRemark,
  onOverride,
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
              <th style={{ width: 35 }}>Att.</th>
              <th style={{ width: 75 }}>Verify (RC)</th>
              <th style={{ width: 110 }}>Verify (Ops)</th>
              <th style={{ width: 55 }}>AI</th>
              <th style={{ minWidth: 180 }}>Remarks / Action</th>
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

                  return (
                    <tr key={`${section.title}-${item.srNo}`} className={isMissing ? 'missing-row' : ''}>
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
                        {!isMissing && item.attachmentUrl && (
                          <a href={item.attachmentUrl} target="_blank" rel="noreferrer" title="View attachment">
                            <Paperclip size={13} style={{ color: '#2980b9', cursor: 'pointer' }} />
                          </a>
                        )}
                      </td>
                      <td className="text-center">
                        {item.verifiedRC && !isMissing ? (
                          <span className="tick-verified" title="RC Verified">✓</span>
                        ) : (
                          <span className="text-gray-300 text-xs">-</span>
                        )}
                      </td>
                      <td>
                        {isMissing ? (
                          <span className="text-gray-400 text-xs">-</span>
                        ) : item.verifiedOps ? (
                          <span className="tick-verified" title="Ops Verified">✓</span>
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
                        <TrafficLight status={isMissing ? 'red' : item.aiStatus} size={11} />
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
                          <div className="flex gap-2 flex-wrap">
                            <button className="link-blue text-xs" onClick={() => onEditRemark(item.srNo, item.remark)}>
                              {item.remark ? 'Edit Remark' : 'Enter Remark'}
                            </button>
                            {(item.aiStatus === 'red' || item.aiStatus === 'yellow') && (
                              <button className="link-blue text-xs" onClick={() => onOverride(item.srNo, item.aiStatus)}>
                                Override AI
                              </button>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
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
