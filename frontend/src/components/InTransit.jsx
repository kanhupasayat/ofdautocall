import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import * as XLSX from 'xlsx'
import './InTransit.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://ofdautocall.onrender.com/api'

// Configure axios to skip ngrok browser warning
axios.defaults.headers.common['ngrok-skip-browser-warning'] = 'true'

function InTransit() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [allOrders, setAllOrders] = useState([])
  const [displayOrders, setDisplayOrders] = useState([])
  const [count, setCount] = useState(0)
  const [delayedCount, setDelayedCount] = useState(0)

  const [filters, setFilters] = useState({
    rto: false,
    delivered: false,
    lost: false,
    damaged: false,
    cancelled: false,
    destroyed: false
  })

  useEffect(() => {
    // Check if cache is from today, if not clear it (daily refresh)
    const lastRefreshDate = localStorage.getItem('in_transit_last_refresh')
    const today = new Date().toDateString()

    if (lastRefreshDate !== today) {
      // New day detected, clear cache to force fresh data
      localStorage.removeItem('in_transit_cache')
      localStorage.setItem('in_transit_last_refresh', today)
    }

    // Load from localStorage first (instant load)
    const cachedData = localStorage.getItem('in_transit_cache')
    if (cachedData) {
      try {
        const parsed = JSON.parse(cachedData)
        const orders = parsed.orders || []
        setAllOrders(orders)
        setCount(parsed.count)
        setDelayedCount(parsed.delayed_count)
        setDisplayOrders(orders)
        setLoading(false)
      } catch (e) {
        console.error('Failed to parse cached In Transit data')
      }
    }

    fetchInTransit()
  }, [])

  const fetchInTransit = async () => {
    setError(null)

    try {
      const response = await axios.get(`${API_BASE_URL}/orders/in-transit/?verified=true`)
      const orders = response.data.orders || []
      setAllOrders(orders)
      setCount(response.data.count)
      setDelayedCount(response.data.delayed_count)
      setDisplayOrders(orders)
      setLoading(false)

      // Save to localStorage for next time
      localStorage.setItem('in_transit_cache', JSON.stringify(response.data))
    } catch (err) {
      console.error('InTransit API Error:', err)
      console.error('Error response:', err.response)
      console.error('Error message:', err.message)
      const errorMsg = err.response?.data?.error || err.response?.data?.message || err.message || 'Failed to fetch orders'
      setError(errorMsg)
      setLoading(false)
    }
  }

  const applyFilters = useCallback(() => {
    // Check if any filter is active
    const anyFilterActive = Object.values(filters).some(f => f)

    if (!anyFilterActive) {
      // No filter active, show all orders
      setDisplayOrders(allOrders)
      return
    }

    // At least one filter is active, show only matching orders
    let filtered = allOrders.filter(order => {
      const status = (order.current_status || '').toLowerCase()

      // Check if order matches any of the active filters
      if (filters.rto && status.includes('rto')) return true
      if (filters.delivered && status.includes('delivered')) return true
      if (filters.lost && status.includes('lost')) return true
      if (filters.damaged && status.includes('damaged')) return true
      if (filters.cancelled && status.includes('cancel')) return true
      if (filters.destroyed && (status.includes('destroyed') || status.includes('disposed'))) return true

      return false
    })

    setDisplayOrders(filtered)
  }, [filters, allOrders])

  useEffect(() => {
    applyFilters()
  }, [applyFilters])

  const toggleFilter = (filterName) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: !prev[filterName]
    }))
  }

  const handleExportToExcel = () => {
    if (!displayOrders || displayOrders.length === 0) {
      alert('No data to export!')
      return
    }

    // Prepare data for Excel
    const excelData = displayOrders.map((order, index) => ({
      'S.No': index + 1,
      'AWB': order.awb,
      'Customer Name': order.customer_name || 'N/A',
      'Customer Mobile': order.customer_mobile || 'N/A',
      'Customer Address': order.customer_address || 'N/A',
      'Pincode': order.customer_pincode || 'N/A',
      'Order Date': order.order_date || 'N/A',
      'Estimated Delivery': order.estimated_delivery_date || 'N/A',
      'Status': order.current_status || 'In Transit',
      'Delayed': order.is_delayed ? 'Yes' : 'No',
      'Weight (kg)': order.weight || 'N/A',
      'COD Amount': order.cod_amount ? `₹${order.cod_amount}` : 'N/A',
      'Last Scan Location': order.last_scan?.scan_location || 'N/A',
      'Last Scan Time': order.last_scan?.scan_datetime || 'N/A',
      'Tracking URL': order.tracking_url || 'N/A'
    }))

    // Create worksheet
    const ws = XLSX.utils.json_to_sheet(excelData)

    // Set column widths
    ws['!cols'] = [
      { wch: 6 },  // S.No
      { wch: 18 }, // AWB
      { wch: 20 }, // Customer Name
      { wch: 15 }, // Mobile
      { wch: 40 }, // Address
      { wch: 10 }, // Pincode
      { wch: 12 }, // Order Date
      { wch: 18 }, // Estimated Delivery
      { wch: 25 }, // Status
      { wch: 10 }, // Delayed
      { wch: 12 }, // Weight
      { wch: 12 }, // COD Amount
      { wch: 25 }, // Last Scan Location
      { wch: 20 }, // Last Scan Time
      { wch: 50 }  // Tracking URL
    ]

    // Create workbook
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'In Transit Orders')

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().split('T')[0]
    const filename = `InTransit_Orders_${timestamp}.xlsx`

    // Download
    XLSX.writeFile(wb, filename)

    alert(`✅ Excel exported successfully!\n\nFile: ${filename}\nRecords: ${displayOrders.length}`)
  }

  if (loading) {
    return <div className="loading">Loading in-transit orders...</div>
  }

  if (error) {
    return <div className="error-message">Error: {error}</div>
  }

  return (
    <div className="in-transit">
      <div className="section-header">
        <div className="header-left">
          <h2>In Transit Orders</h2>
          <div className="count-badges">
            <div className="count-badge total">{displayOrders.length} Showing / {count} Total</div>
            {delayedCount > 0 && (
              <div className="count-badge delayed">{delayedCount} Delayed</div>
            )}
          </div>
        </div>
        <div style={{display: 'flex', gap: '1rem'}}>
          <button
            onClick={() => { localStorage.removeItem('in_transit_cache'); fetchInTransit(); }}
            style={{
              padding: '0.6rem 1.5rem',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              fontWeight: '600',
              cursor: 'pointer',
              fontSize: '0.95rem',
              transition: 'all 0.3s'
            }}
          >
            🔄 Refresh Data
          </button>
          <button onClick={handleExportToExcel} className="export-button">
            Export to Excel
          </button>
        </div>
      </div>

      <div style={{marginBottom: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.75rem'}}>
        <button
          onClick={() => toggleFilter('delivered')}
          style={{
            padding: '0.4rem 1rem',
            borderRadius: '20px',
            fontWeight: '600',
            fontSize: '0.85rem',
            border: filters.delivered ? '2px solid #c62828' : '2px solid #ddd',
            background: filters.delivered ? '#ffebee' : 'white',
            color: filters.delivered ? '#c62828' : '#666',
            cursor: 'pointer',
            transition: 'all 0.3s'
          }}
        >
          {filters.delivered ? '✓ Delivered' : 'Delivered'}
        </button>

        <button
          onClick={() => toggleFilter('rto')}
          style={{
            padding: '0.4rem 1rem',
            borderRadius: '20px',
            fontWeight: '600',
            fontSize: '0.85rem',
            border: filters.rto ? '2px solid #e65100' : '2px solid #ddd',
            background: filters.rto ? '#fff3e0' : 'white',
            color: filters.rto ? '#e65100' : '#666',
            cursor: 'pointer',
            transition: 'all 0.3s'
          }}
        >
          {filters.rto ? '✓ RTO' : 'RTO'}
        </button>

        <button
          onClick={() => toggleFilter('lost')}
          style={{
            padding: '0.4rem 1rem',
            borderRadius: '20px',
            fontWeight: '600',
            fontSize: '0.85rem',
            border: filters.lost ? '2px solid #6a1b9a' : '2px solid #ddd',
            background: filters.lost ? '#f3e5f5' : 'white',
            color: filters.lost ? '#6a1b9a' : '#666',
            cursor: 'pointer',
            transition: 'all 0.3s'
          }}
        >
          {filters.lost ? '✓ Lost' : 'Lost'}
        </button>

        <button
          onClick={() => toggleFilter('damaged')}
          style={{
            padding: '0.4rem 1rem',
            borderRadius: '20px',
            fontWeight: '600',
            fontSize: '0.85rem',
            border: filters.damaged ? '2px solid #d84315' : '2px solid #ddd',
            background: filters.damaged ? '#fbe9e7' : 'white',
            color: filters.damaged ? '#d84315' : '#666',
            cursor: 'pointer',
            transition: 'all 0.3s'
          }}
        >
          {filters.damaged ? '✓ Damaged' : 'Damaged'}
        </button>

        <button
          onClick={() => toggleFilter('cancelled')}
          style={{
            padding: '0.4rem 1rem',
            borderRadius: '20px',
            fontWeight: '600',
            fontSize: '0.85rem',
            border: filters.cancelled ? '2px solid #0277bd' : '2px solid #ddd',
            background: filters.cancelled ? '#e1f5fe' : 'white',
            color: filters.cancelled ? '#0277bd' : '#666',
            cursor: 'pointer',
            transition: 'all 0.3s'
          }}
        >
          {filters.cancelled ? '✓ Cancelled' : 'Cancelled'}
        </button>

        <button
          onClick={() => toggleFilter('destroyed')}
          style={{
            padding: '0.4rem 1rem',
            borderRadius: '20px',
            fontWeight: '600',
            fontSize: '0.85rem',
            border: filters.destroyed ? '2px solid #455a64' : '2px solid #ddd',
            background: filters.destroyed ? '#eceff1' : 'white',
            color: filters.destroyed ? '#455a64' : '#666',
            cursor: 'pointer',
            transition: 'all 0.3s'
          }}
        >
          {filters.destroyed ? '✓ Destroyed' : 'Destroyed'}
        </button>
      </div>

      {displayOrders.length === 0 ? (
        <div className="empty-state">
          <p>No orders to display</p>
        </div>
      ) : (
        <div className="orders-grid">
          {displayOrders.map((order) => (
            <div key={order.awb} className={`order-card ${order.is_delayed ? 'delayed' : ''}`}>
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
                <div className="status-badge transit">
                  {order.status}
                </div>
              </div>

              {order.is_delayed && (
                <div className="delay-alert">
                  <span className="alert-icon">⚠</span>
                  <span>Delivery Delayed</span>
                </div>
              )}

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

                <div className={`delivery-date ${order.is_delayed ? 'overdue' : ''}`}>
                  <span className="label">Est. Delivery:</span>
                  <span className="value">
                    {order.estimated_delivery_date || 'Not Available'}
                  </span>
                  {order.is_delayed && (
                    <span className="overdue-tag">OVERDUE</span>
                  )}
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
                    {order.last_scan.remarks && (
                      <div className="scan-remarks">{order.last_scan.remarks}</div>
                    )}
                  </div>
                </div>
              )}

              {order.scan_history && order.scan_history.length > 0 && (
                <details className="scan-history">
                  <summary>View Scan History ({order.scan_history.length} scans)</summary>
                  <div className="history-list">
                    {order.scan_history.map((scan, index) => (
                      <div key={index} className="history-item">
                        <div className="history-location">{scan.scan_location}</div>
                        <div className="history-time">{scan.scan_datetime}</div>
                        {scan.remarks && (
                          <div className="history-remarks">{scan.remarks}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default InTransit
