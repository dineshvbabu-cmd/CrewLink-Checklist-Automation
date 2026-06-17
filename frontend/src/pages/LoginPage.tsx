import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth'

const DEMO_USERS = [
  { username: 'rc', password: 'CrewlinkRC!23', label: 'RC Officer' },
  { username: 'ops', password: 'CrewlinkOps!23', label: 'Ops Manager' },
  { username: 'admin', password: 'CrewlinkAdmin!23', label: 'Administrator' },
]

export default function LoginPage() {
  const { user, login } = useAuth()
  const [username, setUsername] = useState('rc')
  const [password, setPassword] = useState('CrewlinkRC!23')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (user) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await login(username, password)
    } catch {
      setError('Invalid login. Check the username and password and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen login-shell px-4 py-10">
      <div className="mx-auto max-w-5xl grid gap-6 lg:grid-cols-[1.05fr,0.95fr] items-stretch">
        <section className="rounded-2xl login-hero text-white p-8 border border-slate-700/30">
          <div className="text-xs uppercase tracking-[0.3em] text-sky-200">Crewlink AI-ACE</div>
          <h1 className="mt-3 mb-3 text-4xl font-bold leading-tight">Checklist automation built around the real Crewlink workflow.</h1>
          <p className="m-0 text-sm text-slate-200 leading-7 max-w-xl">
            RC reviews pre-departure documents, Ops clears exceptions, seafarers confirm handover, and every action
            lands in a persistent audit trail.
          </p>

          <div className="mt-8 grid gap-3 md:grid-cols-3">
            {DEMO_USERS.map(account => (
              <button
                key={account.username}
                type="button"
                onClick={() => {
                  setUsername(account.username)
                  setPassword(account.password)
                }}
                className="rounded-xl border border-sky-200/20 bg-white/10 px-4 py-3 text-left hover:bg-white/15"
              >
                <div className="text-xs text-sky-200">{account.label}</div>
                <div className="mt-1 font-semibold">{account.username}</div>
                <div className="mt-1 text-[11px] text-slate-300">{account.password}</div>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-2xl bg-white border border-slate-200 shadow-xl p-8">
          <div className="text-sm font-semibold text-slate-500 uppercase tracking-[0.18em]">Sign In</div>
          <h2 className="mt-2 mb-1 text-2xl font-bold text-slate-900">Access the checklist workspace</h2>
          <p className="m-0 text-sm text-slate-500">Use an RC, Ops, or Admin role to test the role-aware workflow.</p>

          <form className="mt-8 grid gap-4" onSubmit={handleSubmit}>
            <label className="grid gap-2 text-sm text-slate-600">
              Username
              <input
                value={username}
                onChange={event => setUsername(event.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900"
              />
            </label>
            <label className="grid gap-2 text-sm text-slate-600">
              Password
              <input
                type="password"
                value={password}
                onChange={event => setPassword(event.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900"
              />
            </label>

            {error && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:opacity-95 disabled:opacity-60"
            >
              {submitting ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </section>
      </div>
    </div>
  )
}
