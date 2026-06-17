import { type ReactNode, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, ArrowLeft, ChevronDown, User } from 'lucide-react'
import type { CrewMember, DocumentsData, DocumentItem } from '../../types'
import TrafficLight from '../Common/TrafficLight'

interface Props {
  member: CrewMember
  docs: DocumentsData | null
}

const PROFILE_TABS = ['Personal Details', 'Documents', 'Sea Service', 'Correspondence', 'Compliance']

function buildProfileFacts(member: CrewMember) {
  return {
    nationalityCountry: member.nationality === 'Indian' ? 'India' : member.nationality,
    dateOfBirth: member.id === 'c001' ? '14-Feb-1986' : member.id === 'c002' ? '02-Aug-1994' : '11-Nov-1988',
    passportCountry: member.nationality === 'Indian' ? 'India' : 'Nigeria',
    crewStatus: member.status === 'planned' ? 'Planned sign-on' : 'On board',
    email: `${member.name.toLowerCase().replace(/\s+/g, '.')}@crewlink.demo`,
    phone: member.id === 'c001' ? '+91 98765 21001' : member.id === 'c002' ? '+234 803 112 9002' : '+91 99887 66554',
  }
}

function filterCourseItems(docs: DocumentsData | null, mode: 'stcw' | 'company') {
  if (!docs) {
    return []
  }

  return docs.sections
    .filter(section =>
      mode === 'stcw'
        ? section.title.toLowerCase().includes('stcw')
        : section.title.toLowerCase().includes('company'),
    )
    .flatMap(section => section.items)
}

export default function SeafarerProfile({ member, docs }: Props) {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('Compliance')
  const [docSubTab, setDocSubTab] = useState<'License' | 'Courses'>('License')
  const [courseSubTab, setCourseSubTab] = useState<'stcw' | 'company'>('stcw')
  const facts = buildProfileFacts(member)
  const complianceIssueCount = docs ? docs.summary.missing + docs.summary.expired : 0

  return (
    <div>
      <div style={{ backgroundColor: '#f7fafd', borderBottom: '1px solid #dde3ec' }} className="px-5 py-2">
        <button onClick={() => navigate('/')} className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline">
          <ArrowLeft size={13} />
          Back to Crew List - ALKEBULAN
        </button>
      </div>

      <div style={{ backgroundColor: '#1a2a4a' }} className="px-5 py-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div
              style={{ width: 64, height: 64, backgroundColor: '#2c3e6b', border: '2px solid #3d5491', borderRadius: '50%' }}
              className="flex items-center justify-center flex-shrink-0"
            >
              <User size={28} className="text-blue-300" />
            </div>

            <div>
              <div className="flex items-center gap-3 mb-1 flex-wrap">
                <h1 className="text-white font-bold text-xl m-0">{member.name}</h1>
                <span style={{ backgroundColor: '#27ae60', borderRadius: 12, padding: '2px 10px' }} className="text-white text-xs font-semibold">
                  Approved
                </span>
                <TrafficLight status={member.aiStatus} size={13} />
              </div>
              <div className="flex items-center gap-3 text-blue-300 text-sm flex-wrap">
                <span>{member.rank}</span>
                <span>|</span>
                <span>{member.empNo}</span>
                <span>|</span>
                <span>ALKEBULAN</span>
                <span>|</span>
                <span>{member.nationality}</span>
              </div>
            </div>
          </div>

          <div style={{ backgroundColor: '#162240', border: '1px solid #2c3e6b', borderRadius: 6 }} className="px-4 py-2 text-xs text-blue-200">
            <div className="font-semibold text-white text-xs mb-1">Experience</div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <div className="text-[10px] text-blue-400">Operator</div>
                <div className="font-bold text-white">8y 3m 12d</div>
              </div>
              <div>
                <div className="text-[10px] text-blue-400">Rank</div>
                <div className="font-bold text-white">2y 6m</div>
              </div>
              <div>
                <div className="text-[10px] text-blue-400">Total</div>
                <div className="font-bold text-white">12y 1m</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: '#162240' }} className="flex border-b border-blue-900 flex-wrap">
        {PROFILE_TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={
              activeTab === tab
                ? { borderBottom: '3px solid #2980b9', color: '#fff' }
                : { borderBottom: '3px solid transparent', color: '#93b4d9' }
            }
            className="px-5 py-2.5 text-xs font-medium hover:text-white transition-colors flex items-center gap-1.5"
          >
            {tab}
            {(tab === 'Personal Details' || tab === 'Documents' || tab === 'Correspondence') && <ChevronDown size={11} />}
            {tab === 'Compliance' && complianceIssueCount > 0 && (
              <span style={{ backgroundColor: '#e74c3c', color: 'white', borderRadius: 10, fontSize: 10, padding: '1px 5px' }}>
                {complianceIssueCount}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="p-5">
        {activeTab === 'Personal Details' && (
          <div className="grid md:grid-cols-2 gap-4">
            <InfoCard title="Identity">
              <InfoRow label="Nationality" value={facts.nationalityCountry} />
              <InfoRow label="Date of Birth" value={facts.dateOfBirth} />
              <InfoRow label="Crew Status" value={facts.crewStatus} />
              <InfoRow label="Expected Sign-On" value={member.signOnDate} />
            </InfoCard>
            <InfoCard title="Contact">
              <InfoRow label="Email" value={facts.email} />
              <InfoRow label="Phone" value={facts.phone} />
              <InfoRow label="Travel Readiness" value={member.travelDate} />
              <InfoRow label="Relief Due" value={member.reliefDue} />
            </InfoCard>
          </div>
        )}

        {activeTab === 'Documents' && docs && (
          <div>
            <div className="flex gap-1 mb-4 border-b border-gray-200">
              {(['License', 'Courses'] as const).map(sub => (
                <button
                  key={sub}
                  onClick={() => setDocSubTab(sub)}
                  style={docSubTab === sub ? { borderBottom: '2px solid #2980b9', color: '#2980b9' } : { borderBottom: '2px solid transparent', color: '#555' }}
                  className="px-4 py-2 text-xs font-medium"
                >
                  {sub}
                </button>
              ))}
            </div>

            {docSubTab === 'License' && (
              <table className="crewlink-table">
                <thead>
                  <tr>
                    <th>License</th>
                    <th>Certificate No</th>
                    <th>Place Of Issue</th>
                    <th>Country</th>
                    <th>Issue Date</th>
                    <th>Expiry Date</th>
                    <th>Authority</th>
                    <th>Verified</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.sections
                    .filter(section => section.title.toLowerCase().includes('license'))
                    .flatMap(section => section.items)
                    .map((item, index) => (
                      <tr key={index} className={item.missing ? 'missing-row' : ''}>
                        <td>{item.name}</td>
                        <td className="font-mono text-xs">{item.docNo || '-'}</td>
                        <td className="text-gray-500 text-xs">Mumbai</td>
                        <td className="text-gray-500 text-xs">{facts.passportCountry}</td>
                        <td className="text-xs">{item.issueDate || '-'}</td>
                        <td className="text-xs">{item.expiryDate}</td>
                        <td className="text-xs text-gray-500">DG Shipping</td>
                        <td className="text-center">
                          {item.verifiedOps ? <span className="tick-verified">✓</span> : <span className="text-gray-400 text-xs">Pending</span>}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}

            {docSubTab === 'Courses' && (
              <div>
                <div className="flex gap-1 mb-3">
                  <button
                    onClick={() => setCourseSubTab('stcw')}
                    className={`px-3 py-1 text-xs rounded ${courseSubTab === 'stcw' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-blue-50'}`}
                  >
                    STCW Course
                  </button>
                  <button
                    onClick={() => setCourseSubTab('company')}
                    className={`px-3 py-1 text-xs rounded ${courseSubTab === 'company' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-blue-50'}`}
                  >
                    Company Courses
                  </button>
                </div>
                <table className="crewlink-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Course</th>
                      <th>Certificate No</th>
                      <th>Place Of Issue</th>
                      <th>Issue Date</th>
                      <th>Expiry Date</th>
                      <th>Authority</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filterCourseItems(docs, courseSubTab).map((item, index) => (
                      <tr key={index} className={item.missing ? 'missing-row' : ''}>
                        <td className="text-xs text-gray-500">{item.type}</td>
                        <td>{item.name}</td>
                        <td className="font-mono text-xs">{item.docNo || '-'}</td>
                        <td className="text-xs text-gray-500">Mumbai</td>
                        <td className="text-xs">{item.issueDate || '-'}</td>
                        <td className="text-xs">{item.expiryDate}</td>
                        <td className="text-xs text-gray-500">{courseSubTab === 'stcw' ? 'IMO / DGS' : 'Operator LMS'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'Sea Service' && (
          <div className="rounded border border-gray-200 bg-white overflow-hidden">
            <table className="crewlink-table">
              <thead>
                <tr>
                  <th>Vessel</th>
                  <th>Rank</th>
                  <th>From</th>
                  <th>To</th>
                  <th>Duration</th>
                  <th>Operator</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>ALKEBULAN</td>
                  <td>{member.rank}</td>
                  <td>13-Jan-2026</td>
                  <td>{member.signOnDate}</td>
                  <td>6.0 months</td>
                  <td>CrewLink ASM</td>
                </tr>
                <tr>
                  <td>SEA FALCON</td>
                  <td>{member.rank}</td>
                  <td>01-Jul-2025</td>
                  <td>31-Dec-2025</td>
                  <td>6.0 months</td>
                  <td>CrewLink ASM</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'Correspondence' && (
          <div className="grid gap-3">
            <InfoCard title="Recent Correspondence">
              <InfoRow label="17-Jun-2026" value="RC shared pre-departure checklist with Ops for review." />
              <InfoRow label="15-Jun-2026" value="Seafarer confirmed passport and CDC originals are with office." />
              <InfoRow label="12-Jun-2026" value="Travel readiness target aligned for planned sign-on." />
            </InfoCard>
          </div>
        )}

        {activeTab === 'Compliance' && <ComplianceView member={member} docs={docs} />}
      </div>
    </div>
  )
}

function ComplianceView({ member, docs }: { member: CrewMember; docs: DocumentsData | null }) {
  const [signOnDate, setSignOnDate] = useState(member.signOnDate)
  const missingItems = docs?.sections.flatMap(section => section.items).filter(item => item.missing) ?? []

  return (
    <div>
      <div style={{ backgroundColor: '#f7fafd', border: '1px solid #dde3ec', borderRadius: 6 }} className="p-3 mb-4">
        <div className="flex flex-wrap gap-3 items-end">
          <SelectField label="Select Vessel" value="Alkebulan" />
          <SelectField label="Select Rank" value={member.rank} />
          <SelectField label="Select Duration" value="6.0 months" />
          <div className="flex flex-col gap-0.5">
            <label className="text-xs text-gray-500">Expected Sign-On-Date</label>
            <input
              type="date"
              value={toInputDate(signOnDate)}
              onChange={event => setSignOnDate(fromInputDate(event.target.value))}
              style={{ border: '1px solid #c5d3e8', borderRadius: 4, padding: '4px 8px', fontSize: 12, color: '#2c3e50', backgroundColor: 'white', minWidth: 150 }}
            />
          </div>
          <SelectField label="Select Validity Period" value="3 months" />
          <button style={{ backgroundColor: '#2c3e6b', color: 'white', border: 'none', borderRadius: 4, padding: '6px 20px', fontSize: 12, cursor: 'pointer', alignSelf: 'flex-end' }}>
            Search
          </button>
        </div>
      </div>

      {docs && (
        <div className="grid md:grid-cols-4 gap-3 mb-4">
          {[
            { label: 'Valid & Verified', count: docs.summary.valid, color: '#27ae60' },
            { label: 'Pending Verification', count: docs.summary.pendingVerification, color: '#f39c12' },
            { label: 'Missing Documents', count: docs.summary.missing, color: '#e74c3c' },
            { label: 'Expired', count: docs.summary.expired, color: '#e74c3c' },
          ].map(card => (
            <div key={card.label} style={{ border: `2px solid ${card.color}20`, borderRadius: 6, backgroundColor: 'white' }} className="p-3 text-center">
              <div style={{ fontSize: 28, fontWeight: 'bold', color: card.color }}>{card.count}</div>
              <div className="text-xs text-gray-500 mt-0.5">{card.label}</div>
            </div>
          ))}
        </div>
      )}

      {missingItems.length > 0 && (
        <div style={{ backgroundColor: '#fff5f5', border: '1px solid #fcc', borderRadius: 6 }} className="p-3 mb-4 flex items-start gap-2">
          <AlertCircle size={15} style={{ color: '#e74c3c', flexShrink: 0, marginTop: 1 }} />
          <div className="text-xs">
            <span className="font-semibold text-red-700">Action Required: </span>
            <span className="text-gray-700">{missingItems.map(item => item.name).join(' | ')}</span>
          </div>
        </div>
      )}

      {docs && (
        <div className="overflow-x-auto">
          <table className="crewlink-table">
            <thead>
              <tr>
                <th style={{ minWidth: 220 }}>Document Name</th>
                <th style={{ width: 130 }}>Document No</th>
                <th style={{ width: 80 }}>Type</th>
                <th style={{ width: 95 }}>Issue Date</th>
                <th style={{ width: 95 }}>Expiry Date</th>
                <th style={{ width: 35 }}>Att.</th>
                <th style={{ width: 60 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {docs.sections.map(section => (
                <SectionRows key={section.title} title={section.title} items={section.items} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function SectionRows({ title, items }: { title: string; items: DocumentItem[] }) {
  return (
    <>
      <tr className="section-header-row">
        <td colSpan={7}>{title}</td>
      </tr>
      {items.map((item, index) => (
        <tr key={`${title}-${index}`} className={item.missing ? 'missing-row' : ''}>
          <td>{item.name}</td>
          <td className="font-mono text-xs text-gray-600">{item.docNo || '-'}</td>
          <td className="text-xs text-gray-500">{item.type}</td>
          <td className="text-xs text-gray-600">{item.issueDate || '-'}</td>
          <td className="text-xs text-gray-600">{item.expiryDate}</td>
          <td className="text-center">{!item.missing && <span style={{ color: '#2980b9', cursor: 'pointer' }}>Att.</span>}</td>
          <td className="text-center">
            <TrafficLight status={item.missing ? 'red' : item.aiStatus} size={11} />
          </td>
        </tr>
      ))}
    </>
  )
}

function InfoCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded border border-gray-200 bg-white p-4">
      <h3 className="m-0 mb-3 text-sm font-semibold text-gray-800">{title}</h3>
      <div className="grid gap-2">{children}</div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-800 font-medium text-right">{value}</span>
    </div>
  )
}

function SelectField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <label className="text-xs text-gray-500">{label}</label>
      <select
        defaultValue={value}
        style={{ border: '1px solid #c5d3e8', borderRadius: 4, padding: '4px 8px', fontSize: 12, color: '#2c3e50', backgroundColor: 'white', minWidth: 130 }}
      >
        <option>{value}</option>
      </select>
    </div>
  )
}

function toInputDate(value: string) {
  const [day, month, year] = value.split('-')
  const monthIndex = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].indexOf(month)
  if (monthIndex === -1) {
    return ''
  }
  return `${year}-${String(monthIndex + 1).padStart(2, '0')}-${day}`
}

function fromInputDate(value: string) {
  if (!value) {
    return ''
  }
  const [year, month, day] = value.split('-')
  const monthName = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][Number(month) - 1]
  return `${day}-${monthName}-${year}`
}
