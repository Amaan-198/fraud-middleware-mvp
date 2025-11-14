import { useState, useEffect } from 'react'
import { ENDPOINTS } from '../config'

function SocWorkspace() {
  const [activeView, setActiveView] = useState('review_queue')
  const [reviewQueue, setReviewQueue] = useState([])
  const [blockedSources, setBlockedSources] = useState([])
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [sourceRisk, setSourceRisk] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [analystId, setAnalystId] = useState('analyst_' + Math.random().toString(36).substr(2, 9))

  useEffect(() => {
    if (activeView === 'review_queue') {
      fetchReviewQueue()
    } else if (activeView === 'blocked_sources') {
      fetchBlockedSources()
    }
  }, [activeView])

  const fetchReviewQueue = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch(ENDPOINTS.reviewQueue)
      if (!response.ok) throw new Error('Failed to fetch review queue')
      const data = await response.json()
      setReviewQueue(data.events || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchBlockedSources = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch(ENDPOINTS.blockedSources)
      if (!response.ok) throw new Error('Failed to fetch blocked sources')
      const data = await response.json()
      setBlockedSources(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchSourceRisk = async (sourceId) => {
    try {
      const response = await fetch(ENDPOINTS.sourceRisk(sourceId))
      if (!response.ok) throw new Error('Failed to fetch source risk')
      const data = await response.json()
      setSourceRisk(data)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleReviewEvent = async (eventId, action, notes) => {
    try {
      setError(null)
      const response = await fetch(ENDPOINTS.reviewEvent(eventId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: eventId,
          analyst_id: analystId,
          action: action,
          notes: notes,
        }),
      })

      if (!response.ok) throw new Error('Failed to review event')

      // Refresh the queue
      await fetchReviewQueue()
      setSelectedEvent(null)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleUnblockSource = async (sourceId, reason) => {
    try {
      setError(null)
      const response = await fetch(ENDPOINTS.unblockSource(sourceId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_id: sourceId,
          analyst_id: analystId,
          reason: reason,
        }),
      })

      if (!response.ok) throw new Error('Failed to unblock source')

      // Refresh blocked sources
      await fetchBlockedSources()
    } catch (err) {
      setError(err.message)
    }
  }

  const getThreatLevelBadge = (level) => {
    const badges = {
      0: 'bg-gray-100 text-gray-800',
      1: 'bg-blue-100 text-blue-800',
      2: 'bg-yellow-100 text-yellow-800',
      3: 'bg-orange-100 text-orange-800',
      4: 'bg-red-100 text-red-800',
    }
    return badges[level] || 'bg-gray-100 text-gray-800'
  }

  const getThreatLevelName = (level) => {
    const names = ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    return names[level] || 'UNKNOWN'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">SOC Analyst Workspace</h2>
          <div className="text-sm text-gray-600">
            Analyst: <span className="font-mono font-medium">{analystId}</span>
          </div>
        </div>

        {/* View Selector */}
        <div className="flex space-x-4">
          <button
            onClick={() => setActiveView('review_queue')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              activeView === 'review_queue'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Review Queue ({reviewQueue.length})
          </button>
          <button
            onClick={() => setActiveView('blocked_sources')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              activeView === 'blocked_sources'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Blocked Sources ({blockedSources.length})
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* Review Queue View */}
      {activeView === 'review_queue' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Event List */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Events Requiring Review</h3>
              <button
                onClick={fetchReviewQueue}
                disabled={loading}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Refresh
              </button>
            </div>

            {loading ? (
              <p className="text-gray-500 text-sm">Loading...</p>
            ) : reviewQueue.length === 0 ? (
              <p className="text-gray-500 text-sm">No events requiring review</p>
            ) : (
              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {reviewQueue.map((event, idx) => (
                  <div
                    key={idx}
                    onClick={() => {
                      setSelectedEvent(event)
                      fetchSourceRisk(event.source_identifier)
                    }}
                    className={`p-4 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                      selectedEvent?.event_id === event.event_id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getThreatLevelBadge(
                          event.threat_level
                        )}`}
                      >
                        {getThreatLevelName(event.threat_level)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 mb-1">{event.threat_type}</p>
                    <p className="text-sm text-gray-600 mb-2">{event.description}</p>
                    <p className="text-xs text-gray-500 font-mono">
                      Source: {event.source_identifier}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Event Details & Actions */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Event Details</h3>

            {selectedEvent ? (
              <div className="space-y-6">
                {/* Event Info */}
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-500 uppercase mb-1">Event ID</p>
                    <p className="text-sm font-mono">{selectedEvent.event_id}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase mb-1">Timestamp</p>
                    <p className="text-sm">{new Date(selectedEvent.timestamp).toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase mb-1">Threat Type</p>
                    <p className="text-sm">{selectedEvent.threat_type}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase mb-1">Source</p>
                    <p className="text-sm font-mono">{selectedEvent.source_identifier}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase mb-1">Description</p>
                    <p className="text-sm">{selectedEvent.description}</p>
                  </div>
                  {selectedEvent.metadata && Object.keys(selectedEvent.metadata).length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 uppercase mb-1">Metadata</p>
                      <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                        {JSON.stringify(selectedEvent.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>

                {/* Source Risk Profile */}
                {sourceRisk && (
                  <div className="border-t pt-4">
                    <p className="text-sm font-medium text-gray-900 mb-3">Source Risk Profile</p>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-gray-50 p-3 rounded">
                        <p className="text-xs text-gray-500 mb-1">Risk Score</p>
                        <p className="text-xl font-bold text-red-600">{sourceRisk.risk_score}/100</p>
                      </div>
                      <div className="bg-gray-50 p-3 rounded">
                        <p className="text-xs text-gray-500 mb-1">Recent Events</p>
                        <p className="text-xl font-bold text-gray-900">{sourceRisk.recent_events}</p>
                      </div>
                    </div>
                    {sourceRisk.is_blocked && (
                      <div className="mt-2 bg-red-50 border border-red-200 rounded p-2">
                        <p className="text-xs text-red-800 font-medium">Source is currently blocked</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Review Actions */}
                <div className="border-t pt-4">
                  <p className="text-sm font-medium text-gray-900 mb-3">Review Actions</p>
                  <div className="space-y-2">
                    <button
                      onClick={() => handleReviewEvent(selectedEvent.event_id, 'dismiss', 'False positive')}
                      className="w-full px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700"
                    >
                      Dismiss (False Positive)
                    </button>
                    <button
                      onClick={() =>
                        handleReviewEvent(selectedEvent.event_id, 'investigate', 'Flagged for investigation')
                      }
                      className="w-full px-4 py-2 bg-yellow-600 text-white text-sm font-medium rounded-md hover:bg-yellow-700"
                    >
                      Investigate Further
                    </button>
                    <button
                      onClick={() =>
                        handleReviewEvent(selectedEvent.event_id, 'escalate', 'Escalated to senior analyst')
                      }
                      className="w-full px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700"
                    >
                      Escalate
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">Select an event to view details and take action</p>
            )}
          </div>
        </div>
      )}

      {/* Blocked Sources View */}
      {activeView === 'blocked_sources' && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Blocked Sources</h3>
            <button
              onClick={fetchBlockedSources}
              disabled={loading}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Refresh
            </button>
          </div>

          {loading ? (
            <p className="text-gray-500 text-sm">Loading...</p>
          ) : blockedSources.length === 0 ? (
            <p className="text-gray-500 text-sm">No blocked sources</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Blocked At</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Threat Level</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Auto Blocked</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {blockedSources.map((source, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-mono text-gray-900">{source.source_id}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {new Date(source.blocked_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{source.reason}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getThreatLevelBadge(
                            source.threat_level
                          )}`}
                        >
                          Level {source.threat_level}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {source.auto_blocked ? 'Yes' : 'No'}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => {
                            if (
                              window.confirm(
                                `Are you sure you want to unblock ${source.source_id}?`
                              )
                            ) {
                              handleUnblockSource(
                                source.source_id,
                                'Unblocked by analyst after review'
                              )
                            }
                          }}
                          className="px-3 py-1 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700"
                        >
                          Unblock
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default SocWorkspace
