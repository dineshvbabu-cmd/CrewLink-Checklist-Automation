import type { CrewReport } from '../../types'

interface Props {
  report: CrewReport | null
}

export default function EvidencePanel({ report }: Props) {
  if (!report) {
    return (
      <div className="rounded border border-gray-200 bg-white p-4 text-sm text-gray-400">
        Loading matrix and extraction evidence...
      </div>
    )
  }

  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="rounded border border-gray-200 bg-white">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="m-0 text-sm font-semibold text-gray-800">Vessel / Rank Matrix</h3>
          <p className="m-0 mt-1 text-xs text-gray-500">
            Required document set used by the AI check.
            {' '}
            Source:
            {' '}
            <span className="font-medium text-slate-700">{report.matrix.source || 'seed-fallback'}</span>
          </p>
        </div>
        <div className="p-4">
          <div className="flex flex-wrap gap-2">
            {report.matrix.requiredDocuments.map(document => (
              <span key={document} className="rounded-full bg-blue-50 text-blue-800 px-3 py-1 text-xs border border-blue-100">
                {document}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded border border-gray-200 bg-white">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="m-0 text-sm font-semibold text-gray-800">Extraction Snapshot</h3>
          <p className="m-0 mt-1 text-xs text-gray-500">Mock OCR extraction from attached documents.</p>
        </div>
        <div className="max-h-64 overflow-auto">
          <table className="crewlink-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>File</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {report.extraction.extractedDocuments.map(item => (
                <tr key={`${item.srNo}-${item.name}`}>
                  <td>{item.name}</td>
                  <td className="text-xs text-gray-500">{item.sourceFile}</td>
                  <td className="text-xs text-gray-600">{Math.round(item.confidence * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
