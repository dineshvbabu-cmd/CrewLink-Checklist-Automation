import { Link } from 'react-router-dom'
import { Bell, HelpCircle, LogOut, Settings, User } from 'lucide-react'

export default function Navbar() {
  return (
    <header style={{ backgroundColor: '#1a2a4a' }} className="text-white">
      <div className="flex items-center justify-between px-4 py-2 gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <Link to="/" className="flex items-center gap-2 no-underline">
            <div className="flex items-center gap-1">
              <div className="w-8 h-8 rounded-full bg-blue-400 flex items-center justify-center font-bold text-sm text-white">
                CL
              </div>
              <span className="text-white font-bold text-xl tracking-wide">crewlink</span>
            </div>
          </Link>
          <div className="h-5 w-px bg-blue-600 mx-2" />
          <nav className="flex gap-1 text-xs flex-wrap">
            {['Dashboard', 'Fleet', 'Crew', 'Voyage', 'Operations', 'Reports'].map(item => (
              <button key={item} className="px-3 py-1.5 rounded text-blue-200 hover:text-white hover:bg-blue-700 transition-colors">
                {item}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-blue-700 rounded px-2 py-1 text-xs text-blue-100 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
            AI-ACE Active
          </div>
          <button className="text-blue-200 hover:text-white p-1">
            <HelpCircle size={16} />
          </button>
          <button className="text-blue-200 hover:text-white p-1 relative">
            <Bell size={16} />
            <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-500 rounded-full text-white text-[9px] flex items-center justify-center font-bold">3</span>
          </button>
          <button className="text-blue-200 hover:text-white p-1">
            <Settings size={16} />
          </button>
          <div className="flex items-center gap-2 border-l border-blue-600 pl-3">
            <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center">
              <User size={14} />
            </div>
            <div className="text-xs">
              <div className="font-semibold">Shital Patil</div>
              <div className="text-blue-300 text-[10px]">Ops Manager</div>
            </div>
            <button className="text-blue-300 hover:text-white ml-1">
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: '#162240' }} className="px-4 py-1.5 flex items-center gap-2 text-xs text-blue-300">
        <span>Home</span>
        <span>&gt;</span>
        <span>Fleet Management</span>
        <span>&gt;</span>
        <span className="text-white">Crew List</span>
      </div>
    </header>
  )
}
