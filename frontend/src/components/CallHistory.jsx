import { useState, useEffect } from 'react'
import axios from 'axios'
import './CallHistory.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://ofdautocall.onrender.com/api'

// Configure axios to skip ngrok browser warning
axios.defaults.headers.common['ngrok-skip-browser-warning'] = 'true'

function CallHistory() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [calls, setCalls] = useState([])
  const [count, setCount] = useState(0)

  useEffect(() => {
    // Check if cache is from today, if not clear it (daily refresh)
    const lastRefreshDate = localStorage.getItem('call_history_last_refresh')
    const today = new Date().toDateString()

    if (lastRefreshDate !== today) {
      // New day detected, clear cache to force fresh data
      localStorage.removeItem('call_history_cache')
      localStorage.setItem('call_history_last_refresh', today)
    }

    // Load from localStorage first (instant load)
    const cachedData = localStorage.getItem('call_history_cache')
    if (cachedData) {
      try {
        const parsed = JSON.parse(cachedData)
        setCalls(parsed.calls || [])
        setCount(parsed.count || 0)
        setLoading(false)
      } catch (e) {
        console.error('Failed to parse cached data')
      }
    }

    // Then fetch fresh data
    fetchCallHistory()

    // Auto-refresh every 10 seconds
    const interval = setInterval(() => {
      fetchCallHistory()
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  const fetchCallHistory = async () => {
    setError(null)

    try {
      const response = await axios.get(`${API_BASE_URL}/orders/call-history/`)
      const data = response.data

      console.log('[CallHistory] Fetched data:', data)
      console.log('[CallHistory] Number of calls:', data.count)

      // Debug each call
      if (data.calls && data.calls.length > 0) {
        data.calls.forEach((call, index) => {
          console.log(`[CallHistory] Call ${index + 1}:`, {
            call_id: call.call_id,
            status: call.status,
            ended_reason: call.ended_reason,
            success_evaluation: call.success_evaluation,
            duration: call.duration
          })
        })
      }

      setCalls(data.calls || [])
      setCount(data.count || 0)
      setLoading(false)

      // Save to localStorage for next time
      localStorage.setItem('call_history_cache', JSON.stringify(data))
    } catch (err) {
      console.error('[CallHistory] Error fetching:', err)
      setError(err.response?.data?.error || err.response?.data?.message || 'Failed to fetch call history')
      setLoading(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  if (loading) {
    return <div className="loading">Loading call history...</div>
  }

  if (error) {
    return <div className="error-message">Error: {error}</div>
  }

  return (
    <div className="call-history">
      <div className="section-header">
        <div className="header-left">
          <h2>Call History</h2>
          <div className="count-badges">
            <div className="count-badge total">{count} Total Calls</div>
          </div>
        </div>
        <button onClick={fetchCallHistory} className="refresh-button">
          Refresh
        </button>
      </div>

      {count === 0 ? (
        <div className="empty-state">
          <p>No call history found</p>
        </div>
      ) : (
        <div className="calls-grid">
          {calls.map((call) => (
            <div key={call.id} className={`call-card ${call.status}`}>
              <div className="call-header">
                <div className="call-id-section">
                  <strong>Call ID:</strong>
                  <span className="call-id">{call.call_id}</span>
                </div>
                <div className={`status-badge ${call.status}`}>
                  {call.status || 'Unknown'}
                </div>
              </div>

              <div className="call-details">
                <div className="detail-row">
                  <span className="label">AWB:</span>
                  <span className="value">{call.awb}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Customer:</span>
                  <span className="value">{call.customer_name}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Phone:</span>
                  <span className="value">
                    <a href={`tel:${call.customer_phone}`} style={{color: '#667eea', textDecoration: 'none'}}>
                      {call.customer_phone}
                    </a>
                  </span>
                </div>
                <div className="detail-row">
                  <span className="label">Order Type:</span>
                  <span className="value">{call.order_type}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Call Type:</span>
                  <span className="value">{call.call_type || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Duration:</span>
                  <span className="value">{formatDuration(call.duration)}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Cost:</span>
                  <span className="value cost">₹{call.cost || 0}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Ended Reason:</span>
                  <span className="value ended-reason">{call.ended_reason || 'Pending'}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Success Evaluation:</span>
                  <span className={`value success-badge ${call.success_evaluation === 'true' ? 'success-true' : call.success_evaluation === 'false' ? 'success-false' : ''}`}>
                    {call.success_evaluation === 'true' ? 'Successful' : call.success_evaluation === 'false' ? 'Not Successful' : 'Pending'}
                  </span>
                </div>
                <div className="detail-row">
                  <span className="label">Recording:</span>
                  <span className="value">
                    <a
                      href={`https://dashboard.vapi.ai/call/${call.call_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{color: '#667eea', fontWeight: 600}}
                    >
                      View in VAPI Dashboard →
                    </a>
                  </span>
                </div>
              </div>

              <div className="call-timestamps">
                <div className="timestamp-row">
                  <span className="label">Started:</span>
                  <span className="value">{formatDate(call.call_started_at)}</span>
                </div>
                {call.call_ended_at && (
                  <div className="timestamp-row">
                    <span className="label">Ended:</span>
                    <span className="value">{formatDate(call.call_ended_at)}</span>
                  </div>
                )}
                <div className="timestamp-row">
                  <span className="label">Created:</span>
                  <span className="value">{formatDate(call.created_at)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default CallHistory
