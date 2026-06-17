import type { ConfirmationItem } from '../../types'

interface Props {
  items: ConfirmationItem[]
  canEdit: boolean
  onEdit: (item: ConfirmationItem) => void
}

export default function DepartureOpsTab({ items, canEdit, onEdit }: Props) {
  return (
    <div>
      <div className="px-4 py-2.5" style={{ backgroundColor: '#f7fafd', borderBottom: '1px solid #dde3ec' }}>
        <p className="text-xs text-gray-600 m-0">
          Ops verifies all departure items are complete before sign-on and keeps this record for audit review.
        </p>
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
              <th style={{ width: 90 }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.srNo}>
                <td className="text-center text-gray-500">{item.srNo}</td>
                <td>{item.description}</td>
                <td className="text-center">
                  {item.verifyOps ? <span className="tick-verified">OK</span> : <span className="text-gray-300 text-xs">Pending</span>}
                </td>
                <td>
                  {item.officeRemark ? (
                    <span className="text-xs text-gray-600">{item.officeRemark}</span>
                  ) : (
                    <span className="text-gray-300 text-xs italic">No remark</span>
                  )}
                </td>
                <td className="text-center">
                  {item.verifyCrew ? <span className="tick-verified">OK</span> : <span className="text-gray-300 text-xs">-</span>}
                </td>
                <td>
                  {item.seafarerRemark ? (
                    <span className="text-xs text-gray-600">{item.seafarerRemark}</span>
                  ) : (
                    <span className="text-gray-300 text-xs italic">-</span>
                  )}
                </td>
                <td className="text-center">
                  {canEdit ? (
                    <button className="link-blue text-xs" onClick={() => onEdit(item)}>
                      Update
                    </button>
                  ) : (
                    <span className="text-gray-300 text-xs">View</span>
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
