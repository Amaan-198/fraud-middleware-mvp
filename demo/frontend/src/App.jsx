import { useState } from 'react'
import Dashboard from './components/Dashboard'
import FraudTester from './components/FraudTester'
import SecurityMonitor from './components/SecurityMonitor'
import SocWorkspace from './components/SocWorkspace'
import RateLimitingPlayground from './components/RateLimitingPlayground'
import SecurityTestPlayground from './components/SecurityTestPlayground'
import AuditTrail from './components/AuditTrail'
import SessionMonitor from './components/SessionMonitor'
import SessionDemoComparison from './components/SessionDemoComparison'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')

  const tabs = [
    { id: 'dashboard', name: 'Dashboard', icon: '📊' },
    { id: 'fraud', name: 'Fraud Tester', icon: '🔍' },
    { id: 'sessions', name: 'Session Monitor', icon: '👤' },
    { id: 'sessiondemo', name: 'Session Demo', icon: '🎬' },
    { id: 'security', name: 'Security Monitor', icon: '🛡️' },
    { id: 'soc', name: 'SOC Workspace', icon: '👮' },
    { id: 'ratelimit', name: 'Rate Limiting', icon: '⏱️' },
    { id: 'securitytest', name: 'Security Test', icon: '🔒' },
    { id: 'audit', name: 'Audit Trail', icon: '📋' },
  ]

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />
      case 'fraud':
        return <FraudTester />
      case 'sessions':
        return <SessionMonitor />
      case 'sessiondemo':
        return <SessionDemoComparison />
      case 'security':
        return <SecurityMonitor />
      case 'soc':
        return <SocWorkspace />
      case 'ratelimit':
        return <RateLimitingPlayground />
      case 'securitytest':
        return <SecurityTestPlayground />
      case 'audit':
        return <AuditTrail />
      default:
        return <Dashboard />
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-gray-50">
      {/* Header */}
      <header className="bg-white shadow-md border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="bg-gradient-to-br from-blue-600 to-blue-700 p-3 rounded-xl shadow-lg">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-blue-800 bg-clip-text text-transparent">
                  Security & Fraud Playground
                </h1>
                <p className="text-sm text-gray-600 mt-1">
                  Allianz Fraud Middleware MVP - Interactive Testing Lab
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-gradient-to-r from-green-400 to-green-500 text-white shadow-sm">
                <span className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></span>
                Live
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-2" aria-label="Tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  py-4 px-6 border-b-2 font-medium text-sm whitespace-nowrap transition-all duration-200 rounded-t-lg
                  ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 bg-blue-50'
                      : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50 hover:border-gray-300'
                  }
                `}
              >
                <span className="mr-2 text-lg">{tab.icon}</span>
                {tab.name}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderContent()}
      </main>

      {/* Footer */}
      <footer className="bg-gradient-to-r from-gray-800 to-gray-900 border-t border-gray-700 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-300">
            <span className="font-semibold text-blue-400">Allianz Fraud Middleware MVP v2.0</span> - Security & Fraud Detection System
          </p>
          <p className="text-center text-xs text-gray-500 mt-2">
            Real-time fraud detection with sub-100ms latency • Institute-level security monitoring • SOC analyst tools
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
