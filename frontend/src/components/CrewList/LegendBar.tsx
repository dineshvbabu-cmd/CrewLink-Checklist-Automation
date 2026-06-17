import type { Vessel } from '../../types'

interface Props {
  vessel: Vessel
}

export default function LegendBar({ vessel }: Props) {
  const items = [
    { color: '#2c3e6b', label: 'Total crew on board', count: vessel.totalCrew },
    { color: '#e74c3c', label: 'Relief over due crew', count: vessel.reliefOverdue },
    { color: '#e67e22', label: 'Due in One month', count: vessel.dueOneMonth },
    { color: '#27ae60', label: 'Extra crew onboard', count: vessel.extraCrew },
    { color: '#3498db', label: 'Extended Contract', count: vessel.extendedContract },
    { color: '#9b59b6', label: 'Reduced Contract', count: vessel.reducedContract },
  ]

  return (
    <div className="bg-white border-b border-gray-200 px-5 py-2 flex flex-wrap items-center gap-x-6 gap-y-1.5">
      {items.map(item => (
        <div key={item.label} className="flex items-center gap-1.5">
          <span
            style={{ backgroundColor: item.color }}
            className="inline-block w-3.5 h-3.5 rounded-full flex-shrink-0"
          />
          <span className="text-gray-600 text-xs">
            {item.label}:
          </span>
          <span
            style={{ color: item.color }}
            className="font-bold text-xs"
          >
            ({item.count})
          </span>
        </div>
      ))}
    </div>
  )
}
