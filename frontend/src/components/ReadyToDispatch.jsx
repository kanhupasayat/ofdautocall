import { useState, useEffect } from 'react'
import axios from 'axios'
import './ReadyToDispatch.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

// Configure axios to skip ngrok browser warning
axios.defaults.headers.common['ngrok-skip-browser-warning'] = 'true'

function ReadyToDispatch() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [verified, setVerified] = useState(false)
  const [filterEnabled, setFilterEnabled] = useState(false)
  const [filtering, setFiltering] = useState(false)

  useEffect(() => {
    // CACHE TEMPORARILY DISABLED FOR FASTER REFRESH
    localStorage.removeItem('ready_to_dispatch_cache')

    fetchReadyToDispatch()
  }, [])

  const fetchReadyToDispatch = async (applyFilter = false) => {
    setError(null)
    if (applyFilter) {
      setFiltering(true)
    }

    try {
      const url = applyFilter
        ? `${API_BASE_URL}/orders/ready-to-dispatch/?verified=true`
        : `${API_BASE_URL}/orders/ready-to-dispatch/`

      const response = await axios.get(url)

      // Ensure response data has proper structure
      const responseData = response.data || {}
      if (!responseData.orders) {
        responseData.orders = []
      }
      if (typeof responseData.count === 'undefined') {
        responseData.count = responseData.orders.length
      }

      setData(responseData)
      setVerified(responseData.verified || false)
      setLoading(false)
      setFiltering(false)

      // Cache temporarily disabled - no save to localStorage
    } catch (err) {
      console.error('ReadyToDispatch API Error:', err)
      console.error('Error response:', err.response)
      console.error('Error message:', err.message)
      const errorMsg = err.response?.data?.error || err.response?.data?.message || err.message || 'Failed to fetch orders'
      setError(errorMsg)
      setLoading(false)
      setFiltering(false)
    }
  }

  const handleFilterToggle = () => {
    const newFilterState = !filterEnabled
    setFilterEnabled(newFilterState)
    fetchReadyToDispatch(newFilterState)
  }

  if (loading) {
    return <div className="loading">Loading ready to dispatch orders...</div>
  }

  if (error) {
    return <div className="error-message">Error: {error}</div>
  }

  if (!data) {
    return null
  }

  return (
    <div className="ready-to-dispatch" style={{position: 'relative'}}>
      {filtering && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(255, 255, 255, 0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999,
          borderRadius: '12px'
        }}>
          <div style={{
            textAlign: 'center',
            padding: '2rem',
            background: 'white',
            borderRadius: '12px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
          }}>
            <div style={{
              fontSize: '3rem',
              marginBottom: '1rem',
              animation: 'spin 1s linear infinite'
            }}>⏳</div>
            <div style={{fontSize: '1.2rem', fontWeight: '600', color: '#667eea'}}>
              Applying Filter...
            </div>
            <div style={{fontSize: '0.9rem', color: '#666', marginTop: '0.5rem'}}>
              Fetching manifested orders
            </div>
          </div>
        </div>
      )}
      <div className="section-header">
        <h2>Manifested Orders (Last 5 Days)</h2>
        <div style={{display: 'flex', gap: '1rem', alignItems: 'center'}}>
          <div className="count-badge">{data.count} Orders</div>
          {(verified || data.verified) && (
            <div className="count-badge" style={{background: '#e8f5e9', color: '#2e7d32', border: '2px solid #2e7d32'}}>
              Verified
            </div>
          )}
          <button
            onClick={() => { localStorage.removeItem('ready_to_dispatch_cache'); setFilterEnabled(false); fetchReadyToDispatch(false); }}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: '20px',
              fontWeight: '600',
              fontSize: '0.95rem',
              border: '2px solid #667eea',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
          >
            🔄 Refresh
          </button>
          <button
            onClick={handleFilterToggle}
            disabled={filtering}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: '20px',
              fontWeight: '600',
              fontSize: '0.95rem',
              border: filterEnabled ? '2px solid #2e7d32' : '2px solid #667eea',
              background: filtering ? '#ccc' : (filterEnabled ? '#e8f5e9' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'),
              color: filtering ? '#666' : (filterEnabled ? '#2e7d32' : 'white'),
              cursor: filtering ? 'not-allowed' : 'pointer',
              transition: 'all 0.3s',
              opacity: filtering ? 0.7 : 1
            }}
          >
            {filtering ? '⏳ Filtering...' : (filterEnabled ? '✓ Filtered' : 'Apply Filter')}
          </button>
        </div>
      </div>

      {!data.orders || data.orders.length === 0 ? (
        <div className="empty-state">
          <p>No orders ready to dispatch</p>
        </div>
      ) : (
        <div className="orders-grid">
          {data.orders.map((order) => (
            <div key={order.awb} className="order-card">
              <div className="order-header">
                <div className="awb-number">
                  <strong>AWB:</strong>
                  {order.tracking_url ? (
                    <a href={order.tracking_url} target="_blank" rel="noopener noreferrer" className="tracking-link">
                      {order.awb}
                    </a>
                  ) : (
                    <span>{order.awb}</span>
                  )}
                </div>
                <div className="status-badge ready">
                  {order.current_status || order.status}
                </div>
              </div>

              <div className="order-details">
                <div className="detail-row">
                  <span className="label">Customer:</span>
                  <span className="value">{order.customer_name || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Mobile:</span>
                  <span className="value">{order.customer_mobile || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Address:</span>
                  <span className="value">{order.customer_address || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Pincode:</span>
                  <span className="value">{order.customer_pincode || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Weight:</span>
                  <span className="value">{order.weight ? `${order.weight} kg` : 'N/A'}</span>
                </div>
                {order.cod_amount && (
                  <div className="detail-row">
                    <span className="label">COD Amount:</span>
                    <span className="value cod">₹{order.cod_amount}</span>
                  </div>
                )}
              </div>

              {order.last_scan && Object.keys(order.last_scan).length > 0 && (
                <div className="last-scan">
                  <div className="scan-title">Last Scan:</div>
                  <div className="scan-info">
                    {order.last_scan.scan_location && (
                      <div>{order.last_scan.scan_location}</div>
                    )}
                    {order.last_scan.scan_datetime && (
                      <div className="scan-time">{order.last_scan.scan_datetime}</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ReadyToDispatch
