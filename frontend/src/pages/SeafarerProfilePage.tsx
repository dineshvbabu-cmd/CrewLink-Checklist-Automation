import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import type { CrewMember, DocumentsData } from '../types'
import { getCrewMember, getDocuments } from '../api'
import SeafarerProfile from '../components/Profile/SeafarerProfile'

export default function SeafarerProfilePage() {
  const { id } = useParams<{ id: string }>()
  const [member, setMember] = useState<CrewMember | null>(null)
  const [docs, setDocs] = useState<DocumentsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    Promise.all([getCrewMember(id), getDocuments(id)])
      .then(([m, d]) => { setMember(m); setDocs(d) })
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mr-3" />
        Loading seafarer profile...
      </div>
    )
  }

  if (!member) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Seafarer not found.
      </div>
    )
  }

  return <SeafarerProfile member={member} docs={docs} />
}
