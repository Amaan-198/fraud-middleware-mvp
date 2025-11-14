import { useState } from 'react'
import { ENDPOINTS } from '../config'

function RateLimitingPlayground() {
  const [testSourceId, setTestSourceId] = useState('test_user_' + Math.random().toString(36).substr(2, 9))
  const [tier, setTier] = useState('free')
  const [burstCount, setBurstCount] = useState(10)
  const [requestResults, setRequestResults] = useState([])
  const [sourceStatus, setSourceStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const tierConfigs = {
    free: { rpm: 20, burst: 10, description: 'Free tier - 20/min, burst 10' },
    basic: { rpm: 100, burst: 30, description: 'Basic tier - 100/min, burst 30' },
    premium: { rpm: 500, burst: 100, description: 'Premium tier - 500/min, burst 100' },
    internal: { rpm: 1000, burst: 200, description: 'Internal tier - 1000/min, burst 200' },
    unlimited: { rpm: 999999, burst: 999999, description: 'Unlimited - No limits' },
  }

  const setSourceTier = async () => {
    try {
      setError(null)
      const response = await fetch(
        `${ENDPOINTS.setRateLimitTier(testSourceId)}?tier=${tier}&analyst_id=playground_user`,
        {
          method: 'POST',
        }
      )

      if (!response.ok) throw new Error('Failed to set tier')

      const data = await response.json()
      alert(`Tier updated to ${tier} for ${testSourceId}`)
      await fetchSourceStatus()
    } catch (err) {
      setError(err.message)
    }
  }

  const fetchSourceStatus = async () => {
    try {
      setError(null)
      const response = await fetch(ENDPOINTS.rateLimitStatus(testSourceId))
      if (!response.ok) throw new Error('Failed to fetch status')

      const data = await response.json()
      setSourceStatus(data)
    } catch (err) {
      setError(err.message)
    }
  }

  const sendBurstRequests = async () => {
    setLoading(true)
    setError(null)
    setRequestResults([])

    const results = []

    try {
      // First set the tier
      await setSourceTier()

      // Send burst of requests
      for (let i = 0; i < burstCount; i++) {
        try {
          // Make a simple decision request to test rate limiting
          const txn = {
            user_id: testSourceId,
            device_id: 'test_device',
            amount: 10.0,
            timestamp: new Date().toISOString(),
            location: 'Test Location',
          }

          const startTime = Date.now()
          const response = await fetch(ENDPOINTS.decision, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Source-ID': testSourceId, // Custom header for rate limiting
            },
            body: JSON.stringify(txn),
          })

          const latency = Date.now() - startTime

          results.push({
            index: i + 1,
            status: response.status,
            allowed: response.ok,
            latency: latency,
            timestamp: new Date().toISOString(),
          })

          // Add small delay to see rate limiting in action
          await new Promise((resolve) => setTimeout(resolve, 50))
        } catch (err) {
          results.push({
            index: i + 1,
            status: 'error',
            allowed: false,
            latency: 0,
            error: err.message,
            timestamp: new Date().toISOString(),
          })
        }
      }

      setRequestResults(results)

      // Fetch updated status
      await fetchSourceStatus()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const calculateStats = () => {
    if (requestResults.length === 0) return null

    const allowed = requestResults.filter((r) => r.allowed).length
    const blocked = requestResults.filter((r) => !r.allowed).length
    const avgLatency =
      requestResults.reduce((sum, r) => sum + r.latency, 0) / requestResults.length

    return { allowed, blocked, avgLatency, total: requestResults.length }
  }

  const stats = calculateStats()

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Rate Limiting Playground</h2>
        <p className="text-sm text-gray-600 mb-6">
          Test rate limiting behavior by sending bursts of requests with different tier configurations.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Source ID</label>
            <input
              type="text"
              value={testSourceId}
              onChange={(e) => setTestSourceId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Rate Limit Tier</label>
            <select
              value={tier}
              onChange={(e) => setTier(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(tierConfigs).map(([key, config]) => (
                <option key={key} value={key}>
                  {config.description}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Burst Size</label>
            <input
              type="number"
              min="1"
              max="100"
              value={burstCount}
              onChange={(e) => setBurstCount(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex space-x-4">
          <button
            onClick={sendBurstRequests}
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Sending Requests...' : 'Send Burst Requests'}
          </button>

          <button
            onClick={fetchSourceStatus}
            disabled={loading}
            className="px-6 py-2 bg-gray-600 text-white font-medium rounded-md hover:bg-gray-700 disabled:opacity-50"
          >
            Check Status
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* Source Status */}
      {sourceStatus && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Status</h3>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-500 mb-1">Tier</p>
              <p className="text-xl font-bold text-gray-900 uppercase">{sourceStatus.tier}</p>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-500 mb-1">Tokens Available</p>
              <p className="text-xl font-bold text-blue-600">{sourceStatus.tokens_available}</p>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-500 mb-1">Violations</p>
              <p className="text-xl font-bold text-orange-600">{sourceStatus.violations}</p>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-500 mb-1">Blocked</p>
              <p className="text-xl font-bold text-red-600">
                {sourceStatus.blocked ? 'YES' : 'NO'}
              </p>
            </div>
          </div>

          {sourceStatus.blocked && sourceStatus.retry_after && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800 text-sm font-medium">
                Source is currently blocked. Retry after {sourceStatus.retry_after} seconds.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Request Results */}
      {stats && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Burst Results</h3>

          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-600 mb-1">Total Requests</p>
              <p className="text-2xl font-bold text-blue-900">{stats.total}</p>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm text-green-600 mb-1">Allowed</p>
              <p className="text-2xl font-bold text-green-900">{stats.allowed}</p>
            </div>

            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-red-600 mb-1">Blocked</p>
              <p className="text-2xl font-bold text-red-900">{stats.blocked}</p>
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-600 mb-1">Avg Latency</p>
              <p className="text-2xl font-bold text-gray-900">{stats.avgLatency.toFixed(0)}ms</p>
            </div>
          </div>

          {/* Request Timeline */}
          <div className="overflow-x-auto">
            <div className="flex space-x-1 mb-4">
              {requestResults.map((result, idx) => (
                <div
                  key={idx}
                  className={`w-4 h-8 rounded ${
                    result.allowed ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  title={`Request ${result.index}: ${result.allowed ? 'Allowed' : 'Blocked'} (${
                    result.latency
                  }ms)`}
                />
              ))}
            </div>
            <p className="text-xs text-gray-500">
              Green = Allowed | Red = Blocked (hover for details)
            </p>
          </div>

          {/* Detailed Table */}
          <div className="mt-6">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Detailed Results</h4>
            <div className="overflow-x-auto max-h-64 overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      #
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      HTTP Code
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Latency
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                      Time
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {requestResults.map((result, idx) => (
                    <tr key={idx} className={result.allowed ? '' : 'bg-red-50'}>
                      <td className="px-4 py-2 text-sm text-gray-900">{result.index}</td>
                      <td className="px-4 py-2">
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            result.allowed
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {result.allowed ? 'Allowed' : 'Blocked'}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-600">{result.status}</td>
                      <td className="px-4 py-2 text-sm text-gray-600">{result.latency}ms</td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {new Date(result.timestamp).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Information Panel */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">How Rate Limiting Works</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Each tier has different request limits per minute and burst capacity</li>
          <li>• Token bucket algorithm allows bursts up to the bucket size</li>
          <li>• Tokens refill at the rate limit (e.g., 20/min = 1 token every 3 seconds)</li>
          <li>• After 3 violations, sources are temporarily blocked</li>
          <li>• Blocked sources receive 429 status and must wait before retrying</li>
        </ul>
      </div>
    </div>
  )
}

export default RateLimitingPlayground
