import { useState, useEffect, useRef } from 'react'
import api from '../services/api'
import { Card, LoadingSpinner, ErrorAlert } from './common'

function SessionDemoComparison() {
  const [demoRunning, setDemoRunning] = useState(false)
  const [normalSession, setNormalSession] = useState(null)
  const [attackSession, setAttackSession] = useState(null)
  const [error, setError] = useState(null)
  const [progress, setProgress] = useState('')
  const [normalHistory, setNormalHistory] = useState([])
  const [attackHistory, setAttackHistory] = useState([])
  const pollingIntervalRef = useRef(null)
  const demoStartedRef = useRef(false)

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
    }
  }, [])

  const runDemo = async () => {
    if (demoRunning) return

    try {
      setDemoRunning(true)
      setError(null)
      setProgress('Starting demo comparison... (this takes 15-20 seconds)')
      setNormalSession(null)
      setAttackSession(null)
      setNormalHistory([])
      setAttackHistory([])
      demoStartedRef.current = true

      // Trigger the demo (takes ~15-20 seconds to complete)
      console.log('Calling demo comparison API...')
      const result = await api.runDemoSessionComparison()
      console.log('Demo comparison result:', result)
      
      setProgress('Demo sessions initiated! Monitoring in real-time...')

      // Start polling both sessions
      const normalId = result.normal_session_id
      const attackId = result.attack_session_id

      if (!normalId || !attackId) {
        throw new Error('Demo API did not return session IDs')
      }

      const pollSessions = async () => {
        try {
          const [normalData, attackData] = await Promise.all([
            api.getSessionDetail(normalId),
            api.getSessionDetail(attackId)
          ])

          setNormalSession(normalData)
          setAttackSession(attackData)

          // Track history for charting
          setNormalHistory(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            risk: normalData.risk_score
          }].slice(-20))

          setAttackHistory(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            risk: attackData.risk_score
          }].slice(-20))

          // Check if demo is complete (attack session terminated)
          if (attackData.is_terminated) {
            setProgress('Demo complete! Attack session was terminated.')
            clearInterval(pollingIntervalRef.current)
            setTimeout(() => {
              setDemoRunning(false)
              demoStartedRef.current = false
            }, 5000) // Keep showing results for 5 seconds
          }
        } catch (err) {
          console.error('Polling error:', err)
          // Don't set error here - polling errors are often transient
        }
      }

      // Poll immediately and then every 2 seconds
      await pollSessions()
      pollingIntervalRef.current = setInterval(pollSessions, 2000)

    } catch (err) {
      console.error('Demo error:', err)
      setError(err.message || 'Failed to run demo. Make sure backend is running on port 8000.')
      setDemoRunning(false)
      demoStartedRef.current = false
    }
  }

  const getRiskColor = (score) => {
    if (score >= 80) return 'text-red-600'
    if (score >= 60) return 'text-orange-600'
    if (score >= 30) return 'text-yellow-600'
    return 'text-green-600'
  }

  const getRiskBg = (score) => {
    if (score >= 80) return 'bg-red-50 border-red-500'
    if (score >= 60) return 'bg-orange-50 border-orange-500'
    if (score >= 30) return 'bg-yellow-50 border-yellow-500'
    return 'bg-green-50 border-green-500'
  }

  const renderSessionPanel = (session, title, icon, isAttack = false) => {
    if (!session) {
      return (
        <Card className="h-full">
          <div className="text-center py-12">
            <div className="text-6xl mb-4">{icon}</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">{title}</h3>
            <p className="text-gray-500 text-sm">Waiting for demo to start...</p>
          </div>
        </Card>
      )
    }

    const riskColor = getRiskColor(session.risk_score)
    const riskBg = getRiskBg(session.risk_score)

    return (
      <Card className={`h-full border-l-4 ${riskBg} ${session.is_terminated ? 'ring-4 ring-red-300' : ''}`}>
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="text-3xl">{icon}</span>
              <div>
                <h3 className="text-lg font-bold text-gray-900">{title}</h3>
                <p className="text-xs text-gray-500 font-mono">{session.session_id}</p>
              </div>
            </div>
            {session.is_terminated ? (
              <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-bold bg-red-100 text-red-800">
                🚫 TERMINATED
              </span>
            ) : (
              <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-bold bg-green-100 text-green-800">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
                ACTIVE
              </span>
            )}
          </div>

          {/* Risk Score - Large Display */}
          <div className="text-center py-6 bg-white rounded-lg border-2 border-gray-100">
            <p className="text-sm text-gray-500 mb-2">Risk Score</p>
            <p className={`text-6xl font-bold ${riskColor}`}>
              {session.risk_score.toFixed(1)}
            </p>
            {session.is_terminated && (
              <p className="text-sm text-red-600 font-semibold mt-2">
                ⚠️ Auto-Terminated at 80+
              </p>
            )}
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all duration-500 ${
                  session.risk_score >= 80 ? 'bg-red-500' :
                  session.risk_score >= 60 ? 'bg-orange-500' :
                  session.risk_score >= 30 ? 'bg-yellow-500' :
                  'bg-green-500'
                }`}
                style={{ width: `${Math.min(session.risk_score, 100)}%` }}
              ></div>
            </div>
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-2 gap-3 pt-3 border-t border-gray-200">
            <div>
              <p className="text-xs text-gray-500">Transactions</p>
              <p className="text-2xl font-bold text-gray-900">{session.transaction_count}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Total Amount</p>
              <p className="text-2xl font-bold text-gray-900">
                ₹{session.total_amount?.toLocaleString() || '0'}
              </p>
            </div>
          </div>

          {/* Anomalies */}
          {session.anomalies && session.anomalies.length > 0 && (
            <div className="pt-3 border-t border-gray-200">
              <p className="text-xs text-gray-500 font-semibold mb-2">
                Anomalies Detected ({session.anomalies.length})
              </p>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {session.anomalies.map((anomaly, idx) => (
                  <div key={idx} className="text-xs bg-red-50 text-red-700 px-2 py-1 rounded">
                    ⚠️ {anomaly.split(':')[0].replace(/_/g, ' ')}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          Behavioral Session Demo
        </h1>
        <p className="text-lg text-gray-600 max-w-3xl mx-auto">
          Watch in real-time as our behavioral biometrics system detects and terminates an account takeover attack while allowing legitimate user activity.
        </p>
      </div>

      {/* Run Demo Button */}
      <div className="text-center">
        <button
          onClick={runDemo}
          disabled={demoRunning}
          className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-lg font-bold rounded-xl hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105"
        >
          {demoRunning ? (
            <>
              <LoadingSpinner size="small" />
              <span className="ml-3">Demo Running...</span>
            </>
          ) : (
            <>
              <span className="mr-3">🎬</span>
              <span>Run Demo Comparison</span>
            </>
          )}
        </button>
        {progress && (
          <p className="mt-3 text-sm text-gray-600 font-medium">{progress}</p>
        )}
      </div>

      {/* Error Alert */}
      {error && <ErrorAlert message={error} />}

      {/* Side-by-side Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {renderSessionPanel(normalSession, 'Legitimate User', '✅', false)}
        {renderSessionPanel(attackSession, 'Account Takeover', '🚨', true)}
      </div>

      {/* Risk Timeline Chart */}
      {(normalHistory.length > 0 || attackHistory.length > 0) && (
        <Card>
          <h3 className="text-xl font-bold text-gray-900 mb-4">Risk Score Timeline</h3>
          <div className="relative h-64 bg-gray-50 rounded-lg p-4">
            <svg className="w-full h-full" viewBox="0 0 800 200">
              {/* Grid lines */}
              {[0, 25, 50, 75, 100].map(y => (
                <g key={y}>
                  <line
                    x1="0"
                    y1={200 - (y * 2)}
                    x2="800"
                    y2={200 - (y * 2)}
                    stroke="#e5e7eb"
                    strokeWidth="1"
                  />
                  <text x="5" y={205 - (y * 2)} fontSize="10" fill="#9ca3af">
                    {y}
                  </text>
                </g>
              ))}

              {/* Normal session line (green) */}
              {normalHistory.length > 1 && (
                <polyline
                  points={normalHistory.map((point, idx) => 
                    `${(idx / (normalHistory.length - 1)) * 780 + 40},${200 - (point.risk * 2)}`
                  ).join(' ')}
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="3"
                />
              )}

              {/* Attack session line (red) */}
              {attackHistory.length > 1 && (
                <polyline
                  points={attackHistory.map((point, idx) => 
                    `${(idx / (attackHistory.length - 1)) * 780 + 40},${200 - (point.risk * 2)}`
                  ).join(' ')}
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="3"
                />
              )}
            </svg>
          </div>
          <div className="flex items-center justify-center space-x-6 mt-4">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-1 bg-green-500 rounded"></div>
              <span className="text-sm text-gray-600">Legitimate User</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-1 bg-red-500 rounded"></div>
              <span className="text-sm text-gray-600">Account Takeover</span>
            </div>
          </div>
        </Card>
      )}

      {/* Explanation */}
      {!demoRunning && !demoStartedRef.current && (
        <Card className="bg-blue-50 border-blue-200">
          <h3 className="text-lg font-bold text-blue-900 mb-3">How This Demo Works</h3>
          <div className="space-y-2 text-sm text-blue-800">
            <p>
              <strong>Left Panel (✅ Legitimate User):</strong> Simulates normal user behavior with typical transaction patterns, amounts, and timing. Risk score stays low.
            </p>
            <p>
              <strong>Right Panel (🚨 Account Takeover):</strong> Simulates an attacker who has stolen account credentials. Shows suspicious patterns like:
            </p>
            <ul className="list-disc list-inside ml-4 space-y-1">
              <li>Large unusual amounts (70,000+ INR vs baseline 2,500 INR)</li>
              <li>Rapid beneficiary changes (5+ new beneficiaries)</li>
              <li>Odd-hour transactions (3 AM)</li>
              <li>Velocity spikes (too many transactions too quickly)</li>
            </ul>
            <p className="pt-2">
              <strong>Result:</strong> The system automatically terminates the attack session when risk score reaches 80+, while the legitimate session continues unaffected.
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}

export default SessionDemoComparison
