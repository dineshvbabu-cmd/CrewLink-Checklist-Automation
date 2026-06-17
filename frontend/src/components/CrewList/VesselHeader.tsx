import type { Vessel } from '../../types'
import { Ship, Flag, Hash } from 'lucide-react'

interface Props {
  vessel: Vessel
  activeTab: string
  onTabChange: (tab: string) => void
}

export default function VesselHeader({ vessel, activeTab, onTabChange }: Props) {
  const tabs = ['Crew List', 'Vessel Particular', 'Brazil Cabotage']

  return (
    <div style={{ backgroundColor: '#1a2a4a' }} className="text-white">
      <div className="flex items-center justify-between px-5 py-3">
        <div className="flex items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Ship size={18} className="text-blue-300" />
              <span className="font-bold text-lg tracking-wide">
                {vessel.name}
              </span>
              <span
                style={{ backgroundColor: '#2c3e6b', border: '1px solid #3d5491' }}
                className="text-xs px-2 py-0.5 rounded text-blue-200 ml-1"
              >
                {vessel.type}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-1 text-xs text-blue-300">
              <span className="flex items-center gap-1">
                <Hash size={11} />
                {vessel.imo}
              </span>
              <span className="flex items-center gap-1">
                <Flag size={11} />
                {vessel.flag}
              </span>
            </div>
          </div>
        </div>
        <div className="text-xs text-blue-300 text-right">
          <div className="font-semibold text-white text-sm">{vessel.totalCrew} Crew Members</div>
          <div>As of 17-Jun-2026</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ backgroundColor: '#162240' }} className="flex border-t border-blue-800">
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            style={
              activeTab === tab
                ? { borderBottom: '3px solid #2980b9', color: '#fff' }
                : { borderBottom: '3px solid transparent', color: '#93b4d9' }
            }
            className="px-5 py-2.5 text-xs font-medium hover:text-white transition-colors"
          >
            {tab}
          </button>
        ))}
      </div>
    </div>
  )
}
