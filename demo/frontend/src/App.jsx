import { useState } from 'react'
import Dashboard from './components/Dashboard'
import FraudTester from './components/FraudTester'
import SecurityMonitor from './components/SecurityMonitor'
import SocWorkspace from './components/SocWorkspace'
import RateLimitingPlayground from './components/RateLimitingPlayground'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')

  const tabs = [
    { id: 'dashboard', name: 'Dashboard', icon: '📊' },
    { id: 'fraud', name: 'Fraud Tester', icon: '🔍' },
    { id: 'security', name: 'Security Monitor', icon: '🛡️' },
    { id: 'soc', name: 'SOC Workspace', icon: '👮' },
    { id: 'ratelimit', name: 'Rate Limiting', icon: '⏱️' },
  ]

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />
      case 'fraud':
        return <FraudTester />
      case 'security':
        return <SecurityMonitor />
      case 'soc':
        return <SocWorkspace />
      case 'ratelimit':
        return <RateLimitingPlayground />
      default:
        return <Dashboard />
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Security & Fraud Playground
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Allianz Fraud Middleware MVP - Interactive Testing Lab
              </p>
            </div>
            <div className="text-sm text-gray-500">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Live
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8" aria-label="Tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap
                  ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <span className="mr-2">{tab.icon}</span>
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
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-500">
            Allianz Fraud Middleware MVP v2.0 - Security & Fraud Detection System
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
