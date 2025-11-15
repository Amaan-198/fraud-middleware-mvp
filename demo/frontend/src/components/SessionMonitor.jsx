import { useState, useEffect } from 'react'
import api from '../services/api'
import { LoadingSpinner, ErrorAlert } from './common'
import SessionCard from './SessionCard'
import SessionDetail from './SessionDetail'

function SessionMonitor() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedSession, setSelectedSession] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [filter, setFilter] = useState('all') // all, active, terminated, suspicious

  useEffect(() => {
    fetchSessions()
    
    if (autoRefresh) {
      const interval = setInterval(fetchSessions, 2000) // Poll every 2 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const fetchSessions = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getActiveSessions(100)
      setSessions(data.sessions || [])
      setLastUpdate(new Date())
    } catch (err) {
      setError(err.message || 'Failed to fetch sessions')
    } finally {
      setLoading(false)
    }
  }

  const handleSessionClick = async (session) => {
    try {
      // Fetch full session details
      const fullDetails = await api.getSessionDetail(session.session_id)
      setSelectedSession(fullDetails)
    } catch (err) {
      setError(`Failed to load session details: ${err.message}`)
    }
  }

  const handleSessionUpdate = async () => {
    // Refresh sessions list after update
    await fetchSessions()
    // Refresh the selected session details
    if (selectedSession) {
      try {
        const updated = await api.getSessionDetail(selectedSession.session_id)
        setSelectedSession(updated)
      } catch (err) {
        console.error('Failed to refresh session details:', err)
      }
    }
  }

  // Filter sessions
  const filteredSessions = sessions.filter(session => {
    switch (filter) {
      case 'active':
        return !session.is_terminated
      case 'terminated':
        return session.is_terminated
      case 'suspicious':
        return session.risk_score >= 60 || session.is_terminated
      default:
        return true
    }
  })

  // Calculate statistics
  const stats = {
    total: sessions.length,
    active: sessions.filter(s => !s.is_terminated).length,
    terminated: sessions.filter(s => s.is_terminated).length,
    suspicious: sessions.filter(s => s.risk_score >= 60).length,
    avgRiskScore: sessions.length > 0
      ? (sessions.reduce((sum, s) => sum + s.risk_score, 0) / sessions.length).toFixed(1)
      : 0
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Session Monitor</h1>
          <p className="text-gray-600 mt-1">
            Live behavioral biometrics monitoring for active user sessions
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              autoRefresh
                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <span className="mr-2">{autoRefresh ? '⏸️' : '▶️'}</span>
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </button>
          <button
            onClick={fetchSessions}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 font-medium">Total Sessions</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            </div>
            <div className="text-3xl">📊</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 font-medium">Active</p>
              <p className="text-2xl font-bold text-green-600">{stats.active}</p>
            </div>
            <div className="text-3xl">✅</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 font-medium">Terminated</p>
              <p className="text-2xl font-bold text-red-600">{stats.terminated}</p>
            </div>
            <div className="text-3xl">🚫</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 font-medium">Suspicious</p>
              <p className="text-2xl font-bold text-orange-600">{stats.suspicious}</p>
            </div>
            <div className="text-3xl">⚠️</div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 font-medium">Avg Risk Score</p>
              <p className="text-2xl font-bold text-blue-600">{stats.avgRiskScore}</p>
            </div>
            <div className="text-3xl">📈</div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700">Filter:</span>
            {['all', 'active', 'terminated', 'suspicious'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
                  filter === f
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          {lastUpdate && (
            <div className="text-xs text-gray-500">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {error && <ErrorAlert message={error} />}

      {/* Loading State */}
      {loading && sessions.length === 0 ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
          <span className="ml-3 text-gray-600">Loading sessions...</span>
        </div>
      ) : filteredSessions.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <div className="text-6xl mb-4">🔍</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">No Sessions Found</h3>
          <p className="text-gray-600">
            {filter === 'all'
              ? 'No active sessions at the moment. Sessions will appear here as users interact with the system.'
              : `No ${filter} sessions found. Try a different filter.`}
          </p>
        </div>
      ) : (
        <>
          {/* Sessions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSessions.map(session => (
              <SessionCard
                key={session.session_id}
                session={session}
                onClick={() => handleSessionClick(session)}
              />
            ))}
          </div>

          {/* Result Count */}
          <div className="text-center text-sm text-gray-600">
            Showing {filteredSessions.length} of {sessions.length} sessions
          </div>
        </>
      )}

      {/* Session Detail Modal */}
      {selectedSession && (
        <SessionDetail
          session={selectedSession}
          onClose={() => setSelectedSession(null)}
          onUpdate={handleSessionUpdate}
        />
      )}
    </div>
  )
}

export default SessionMonitor
