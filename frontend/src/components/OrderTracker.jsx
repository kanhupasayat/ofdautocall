import { useState } from 'react'
import ReadyToDispatch from './ReadyToDispatch'
import InTransit from './InTransit'
import OFDOrders from './OFDOrders'
import CallHistory from './CallHistory'
import './OrderTracker.css'

function OrderTracker() {
  const [activeTab, setActiveTab] = useState('ready')
  const [showRealDataForm, setShowRealDataForm] = useState(false)

  return (
    <div className="order-tracker">
      <div className="tracker-header">
        <h2>Last 20 Days Orders</h2>
        <p>Automatically showing all orders from last 20 days</p>
        <p className="date-info">
          {new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toLocaleDateString('en-IN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
          })} - {new Date().toLocaleDateString('en-IN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
          })}
        </p>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'ready' ? 'active' : ''}`}
          onClick={() => setActiveTab('ready')}
        >
          Manifested Orders
        </button>
        <button
          className={`tab ${activeTab === 'transit' ? 'active' : ''}`}
          onClick={() => setActiveTab('transit')}
        >
          In Transit
        </button>
        <button
          className={`tab ${activeTab === 'ofd' ? 'active' : ''}`}
          onClick={() => setActiveTab('ofd')}
        >
          OFD & Undelivered
        </button>
        <button
          className={`tab ${activeTab === 'calls' ? 'active' : ''}`}
          onClick={() => setActiveTab('calls')}
        >
          Call History
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'ready' && <ReadyToDispatch />}
        {activeTab === 'transit' && <InTransit />}
        {activeTab === 'ofd' && <OFDOrders />}
        {activeTab === 'calls' && <CallHistory />}
      </div>
    </div>
  )
}

export default OrderTracker
