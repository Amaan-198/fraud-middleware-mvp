import { useState } from 'react'
import { ENDPOINTS } from '../config'

function SecurityTestPlayground() {
  const [testSourceId, setTestSourceId] = useState('security_test_' + Math.random().toString(36).substr(2, 9))
  const [loading, setLoading] = useState(false)
  const [scenarioResults, setScenarioResults] = useState([])
  const [error, setError] = useState(null)

  // Clear previous results
  const clearResults = () => {
    setScenarioResults([])
    setError(null)
  }

  // Helper to add a result
  const addResult = (scenario, details) => {
    setScenarioResults(prev => [...prev, {
      scenario,
      timestamp: new Date().toISOString(),
      ...details
    }])
  }

  // Scenario 1: API Abuse (high request rate)
  const testApiAbuse = async () => {
    setLoading(true)
    setError(null)

    try {
      addResult('API Abuse', {
        status: 'running',
        description: 'Sending 60 rapid requests to trigger rate limit...'
      })

      let blockedCount = 0
      let successCount = 0
      let eventsGenerated = []

      // Send rapid-fire requests in smaller batches
      for (let i = 0; i < 60; i++) {
        try {
          const response = await fetch(ENDPOINTS.decision, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Source-ID': testSourceId,
            },
            body: JSON.stringify({
              user_id: testSourceId,
              device_id: 'test_device',
              amount: 10.0,
              timestamp: new Date().toISOString(),
              location: 'Test Location',
            }),
          })

          if (response.status === 429) {
            blockedCount++
          } else if (response.ok) {
            successCount++
          }
        } catch (err) {
          // Continue even if request fails
        }

        // Delay every 5 requests to avoid overwhelming
        if (i % 5 === 0 && i > 0) {
          await new Promise(resolve => setTimeout(resolve, 20))
        }
      }

      // Check for security events
      const eventsResponse = await fetch(`${ENDPOINTS.securityEvents}?source_id=${testSourceId}&limit=10`)
      if (eventsResponse.ok) {
        const events = await eventsResponse.json()
        eventsGenerated = events.filter(e => e.threat_type === 'api_abuse')
      }

      // Check if source is blocked
      const statusResponse = await fetch(ENDPOINTS.rateLimitStatus(testSourceId))
      const status = statusResponse.ok ? await statusResponse.json() : {}

      addResult('API Abuse', {
        status: 'completed',
        description: `Sent 60 rapid requests`,
        successfulRequests: successCount,
        blockedRequests: blockedCount,
        eventsGenerated: eventsGenerated.length,
        threatType: eventsGenerated.length > 0 ? eventsGenerated[0].threat_type : 'N/A',
        threatLevel: eventsGenerated.length > 0 ? eventsGenerated[0].threat_level : 'N/A',
        sourceBlocked: status.blocked || false,
        events: eventsGenerated
      })

    } catch (err) {
      setError(`API Abuse test failed: ${err.message}. Note: Dashboard and other views should still work.`)
      addResult('API Abuse', {
        status: 'error',
        description: `${err.message}. Other UI sections should continue working normally.`
      })
    } finally {
      setLoading(false)
    }
  }

  // Scenario 2: Brute Force Attack
  const testBruteForce = async () => {
    setLoading(true)
    setError(null)

    try {
      addResult('Brute Force', {
        status: 'running',
        description: 'Simulating 15 failed authentication attempts...'
      })

      let eventsGenerated = []

      // Simulate failed auth attempts
      for (let i = 0; i < 15; i++) {
        try {
          await fetch(ENDPOINTS.decision, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Source-ID': testSourceId,
              'X-Auth-Result': 'failed', // Custom header to simulate failed auth
            },
            body: JSON.stringify({
              user_id: testSourceId,
              device_id: 'test_device',
              amount: 0,
              timestamp: new Date().toISOString(),
              location: 'Test Location',
              metadata: {
                auth_attempt: true,
                auth_result: 'failed'
              }
            }),
          })
        } catch (err) {
          // Continue
        }

        await new Promise(resolve => setTimeout(resolve, 100))
      }

      // Check for security events
      const eventsResponse = await fetch(`${ENDPOINTS.securityEvents}?source_id=${testSourceId}&limit=10`)
      if (eventsResponse.ok) {
        const events = await eventsResponse.json()
        eventsGenerated = events.filter(e => e.threat_type === 'brute_force' || e.threat_type === 'api_abuse')
      }

      // Check if source is blocked
      const blockedResponse = await fetch(ENDPOINTS.blockedSources)
      const blockedSources = blockedResponse.ok ? await blockedResponse.json() : []
      const isBlocked = blockedSources.some(s => s.source_id === testSourceId)

      addResult('Brute Force', {
        status: 'completed',
        description: `Simulated 15 failed authentication attempts`,
        attemptsSent: 15,
        eventsGenerated: eventsGenerated.length,
        threatType: eventsGenerated.length > 0 ? eventsGenerated[0].threat_type : 'N/A',
        threatLevel: eventsGenerated.length > 0 ? eventsGenerated[0].threat_level : 'N/A',
        sourceBlocked: isBlocked,
        events: eventsGenerated
      })

    } catch (err) {
      setError(`Brute Force test failed: ${err.message}`)
      addResult('Brute Force', {
        status: 'error',
        description: err.message
      })
    } finally {
      setLoading(false)
    }
  }

  // Scenario 3: Data Exfiltration
  const testDataExfiltration = async () => {
    setLoading(true)
    setError(null)

    try {
      addResult('Data Exfiltration', {
        status: 'running',
        description: 'Simulating large data access (10x baseline)...'
      })

      let eventsGenerated = []

      // Simulate large data access
      for (let i = 0; i < 5; i++) {
        try {
          await fetch(ENDPOINTS.decision, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Source-ID': testSourceId,
              'X-Records-Accessed': '150', // 10x baseline of 15
            },
            body: JSON.stringify({
              user_id: testSourceId,
              device_id: 'test_device',
              amount: 0,
              timestamp: new Date().toISOString(),
              location: 'Test Location',
              metadata: {
                data_access: true,
                records_accessed: 150,
                data_type: 'customer_records'
              }
            }),
          })
        } catch (err) {
          // Continue
        }

        await new Promise(resolve => setTimeout(resolve, 200))
      }

      // Check for security events
      const eventsResponse = await fetch(`${ENDPOINTS.securityEvents}?source_id=${testSourceId}&limit=10`)
      if (eventsResponse.ok) {
        const events = await eventsResponse.json()
        eventsGenerated = events.filter(e =>
          e.threat_type === 'data_exfiltration' ||
          e.threat_type === 'unusual_data_access' ||
          e.threat_type === 'api_abuse'
        )
      }

      addResult('Data Exfiltration', {
        status: 'completed',
        description: `Simulated 5 large data access requests (150 records each, 10x baseline)`,
        requestsSent: 5,
        recordsPerRequest: 150,
        eventsGenerated: eventsGenerated.length,
        threatType: eventsGenerated.length > 0 ? eventsGenerated[0].threat_type : 'N/A',
        threatLevel: eventsGenerated.length > 0 ? eventsGenerated[0].threat_level : 'N/A',
        sourceBlocked: false,
        events: eventsGenerated
      })

    } catch (err) {
      setError(`Data Exfiltration test failed: ${err.message}`)
      addResult('Data Exfiltration', {
        status: 'error',
        description: err.message
      })
    } finally {
      setLoading(false)
    }
  }

  // Scenario 4: Insider Threat (off-hours + privileged access)
  const testInsiderThreat = async () => {
    setLoading(true)
    setError(null)

    try {
      addResult('Insider Threat', {
        status: 'running',
        description: 'Simulating off-hours access to sensitive endpoints...'
      })

      let eventsGenerated = []

      // Simulate off-hours access to sensitive endpoints
      for (let i = 0; i < 8; i++) {
        try {
          await fetch(ENDPOINTS.decision, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Source-ID': testSourceId,
              'X-Access-Time': 'off-hours', // Custom header
              'X-Endpoint-Type': 'privileged', // Accessing sensitive endpoint
            },
            body: JSON.stringify({
              user_id: testSourceId,
              device_id: 'test_device',
              amount: 0,
              timestamp: new Date().toISOString(),
              location: 'Test Location',
              metadata: {
                access_time: 'off-hours',
                endpoint_accessed: '/admin/sensitive-data',
                user_role: 'analyst'
              }
            }),
          })
        } catch (err) {
          // Continue
        }

        await new Promise(resolve => setTimeout(resolve, 150))
      }

      // Check for security events
      const eventsResponse = await fetch(`${ENDPOINTS.securityEvents}?source_id=${testSourceId}&limit=10`)
      if (eventsResponse.ok) {
        const events = await eventsResponse.json()
        eventsGenerated = events.filter(e =>
          e.threat_type === 'insider_threat' ||
          e.threat_type === 'unusual_access' ||
          e.threat_type === 'api_abuse'
        )
      }

      addResult('Insider Threat', {
        status: 'completed',
        description: `Simulated 8 off-hours accesses to privileged endpoints`,
        requestsSent: 8,
        accessPattern: 'Off-hours + Privileged endpoints',
        eventsGenerated: eventsGenerated.length,
        threatType: eventsGenerated.length > 0 ? eventsGenerated[0].threat_type : 'N/A',
        threatLevel: eventsGenerated.length > 0 ? eventsGenerated[0].threat_level : 'N/A',
        sourceBlocked: false,
        events: eventsGenerated
      })

    } catch (err) {
      setError(`Insider Threat test failed: ${err.message}`)
      addResult('Insider Threat', {
        status: 'error',
        description: err.message
      })
    } finally {
      setLoading(false)
    }
  }

  // Helper to render threat level badge
  const getThreatLevelBadge = (level) => {
    const badges = {
      0: { text: 'INFO', class: 'bg-blue-100 text-blue-800' },
      1: { text: 'LOW', class: 'bg-green-100 text-green-800' },
      2: { text: 'MEDIUM', class: 'bg-yellow-100 text-yellow-800' },
      3: { text: 'HIGH', class: 'bg-orange-100 text-orange-800' },
      4: { text: 'CRITICAL', class: 'bg-red-100 text-red-800' },
      'N/A': { text: 'N/A', class: 'bg-gray-100 text-gray-800' }
    }

    const badge = badges[level] || badges['N/A']
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${badge.class}`}>
        {badge.text}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">🔒 Security Test Playground</h2>
            <p className="text-sm text-gray-600 mt-1">
              Trigger security scenarios and observe system response
            </p>
          </div>
          <button
            onClick={clearResults}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Clear Results
          </button>
        </div>
      </div>

      {/* Test Source ID */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Test Source ID
        </label>
        <input
          type="text"
          value={testSourceId}
          onChange={(e) => setTestSourceId(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          placeholder="Enter source ID for testing"
        />
        <p className="text-xs text-gray-500 mt-2">
          All security tests will be performed using this source identifier
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm font-medium">⚠️ {error}</p>
        </div>
      )}

      {/* Security Scenario Buttons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* API Abuse */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <div className="flex items-start space-x-3">
            <div className="text-3xl">🚨</div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900">API Abuse</h3>
              <p className="text-sm text-gray-600 mt-1 mb-4">
                High request rate from single source (60 rapid requests)
              </p>
              <button
                onClick={testApiAbuse}
                disabled={loading}
                className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {loading ? 'Running...' : 'Trigger API Abuse'}
              </button>
            </div>
          </div>
        </div>

        {/* Brute Force */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <div className="flex items-start space-x-3">
            <div className="text-3xl">🔓</div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900">Brute Force</h3>
              <p className="text-sm text-gray-600 mt-1 mb-4">
                Multiple failed authentication attempts (15 attempts)
              </p>
              <button
                onClick={testBruteForce}
                disabled={loading}
                className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {loading ? 'Running...' : 'Trigger Brute Force'}
              </button>
            </div>
          </div>
        </div>

        {/* Data Exfiltration */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <div className="flex items-start space-x-3">
            <div className="text-3xl">📤</div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900">Data Exfiltration</h3>
              <p className="text-sm text-gray-600 mt-1 mb-4">
                Large/unusual data access (10x baseline records)
              </p>
              <button
                onClick={testDataExfiltration}
                disabled={loading}
                className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {loading ? 'Running...' : 'Trigger Data Exfiltration'}
              </button>
            </div>
          </div>
        </div>

        {/* Insider Threat */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <div className="flex items-start space-x-3">
            <div className="text-3xl">🕵️</div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900">Insider Threat</h3>
              <p className="text-sm text-gray-600 mt-1 mb-4">
                Off-hours privileged endpoint access (8 requests)
              </p>
              <button
                onClick={testInsiderThreat}
                disabled={loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {loading ? 'Running...' : 'Trigger Insider Threat'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Results Display */}
      {scenarioResults.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Test Results</h3>
          <div className="space-y-4">
            {scenarioResults.map((result, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="font-semibold text-gray-900">{result.scenario}</h4>
                    <p className="text-sm text-gray-500">
                      {new Date(result.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                  {result.status === 'running' && (
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold">
                      Running...
                    </span>
                  )}
                  {result.status === 'completed' && (
                    <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-semibold">
                      Completed
                    </span>
                  )}
                  {result.status === 'error' && (
                    <span className="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs font-semibold">
                      Error
                    </span>
                  )}
                </div>

                <p className="text-sm text-gray-700 mb-3">{result.description}</p>

                {result.status === 'completed' && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 bg-gray-50 rounded-lg">
                    {result.eventsGenerated !== undefined && (
                      <div>
                        <p className="text-xs text-gray-600">Events Generated</p>
                        <p className="text-lg font-semibold text-gray-900">{result.eventsGenerated}</p>
                      </div>
                    )}
                    {result.threatType && (
                      <div>
                        <p className="text-xs text-gray-600">Threat Type</p>
                        <p className="text-sm font-medium text-gray-900">{result.threatType}</p>
                      </div>
                    )}
                    {result.threatLevel !== undefined && (
                      <div>
                        <p className="text-xs text-gray-600">Threat Level</p>
                        <div className="mt-1">{getThreatLevelBadge(result.threatLevel)}</div>
                      </div>
                    )}
                    {result.sourceBlocked !== undefined && (
                      <div>
                        <p className="text-xs text-gray-600">Source Blocked</p>
                        <p className={`text-lg font-semibold ${result.sourceBlocked ? 'text-red-600' : 'text-green-600'}`}>
                          {result.sourceBlocked ? 'YES' : 'NO'}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Show event details if available */}
                {result.events && result.events.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <p className="text-xs font-semibold text-gray-700 mb-2">Security Events:</p>
                    <div className="space-y-2">
                      {result.events.slice(0, 3).map((event, eventIndex) => (
                        <div key={eventIndex} className="text-xs bg-gray-50 p-2 rounded">
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{event.threat_type}</span>
                            {getThreatLevelBadge(event.threat_level)}
                          </div>
                          <p className="text-gray-600 mt-1">{event.description}</p>
                        </div>
                      ))}
                      {result.events.length > 3 && (
                        <p className="text-xs text-gray-500">
                          + {result.events.length - 3} more events
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SecurityTestPlayground
