import { useState, useEffect } from 'react'
import axios from 'axios'
import Toast, { showToast } from './Toast'
import './OFDOrders.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://ofdautocall.onrender.com/api'

// Configure axios to skip ngrok browser warning
axios.defaults.headers.common['ngrok-skip-browser-warning'] = 'true'

function OFDOrders() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [callingAwb, setCallingAwb] = useState(null)
  const [schedulerStatus, setSchedulerStatus] = useState(null)
  const [scheduledTime, setScheduledTime] = useState('10:00')
  const [calledAwbs, setCalledAwbs] = useState(new Set())

  // New state for tabs and pending calls
  const [activeTab, setActiveTab] = useState('all') // 'all' or 'pending'
  const [pendingCalls, setPendingCalls] = useState(null)
  const [loadingPending, setLoadingPending] = useState(false)

  // Loading states for buttons
  const [isStartingScheduler, setIsStartingScheduler] = useState(false)
  const [isStoppingScheduler, setIsStoppingScheduler] = useState(false)
  const [isRunningNow, setIsRunningNow] = useState(false)
  const [isCleaningUp, setIsCleaningUp] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [countdown, setCountdown] = useState(null)

  // State for copied phone numbers
  const [copiedPhone, setCopiedPhone] = useState(null)

  // State for expanded cards (accordion)
  const [expandedOrderDetails, setExpandedOrderDetails] = useState({}) // { awb: 'basic' | 'call' | 'recording' }

  // State for frontend console logs
  const [frontendLogs, setFrontendLogs] = useState([])

  const toggleOrderSection = (awb, section) => {
    setExpandedOrderDetails(prev => ({
      ...prev,
      [awb]: prev[awb] === section ? null : section
    }))
  }

  // Intercept console.log, console.error, console.warn
  useEffect(() => {
    const originalLog = console.log
    const originalError = console.error
    const originalWarn = console.warn

    const addFrontendLog = (message, type) => {
      const timestamp = new Date().toLocaleTimeString()
      setFrontendLogs(prev => [...prev.slice(-49), { time: timestamp, message: String(message), type }])
    }

    console.log = (...args) => {
      originalLog.apply(console, args)
      addFrontendLog(args.join(' '), 'info')
    }

    console.error = (...args) => {
      originalError.apply(console, args)
      addFrontendLog(args.join(' '), 'error')
    }

    console.warn = (...args) => {
      originalWarn.apply(console, args)
      addFrontendLog(args.join(' '), 'warning')
    }

    return () => {
      console.log = originalLog
      console.error = originalError
      console.warn = originalWarn
    }
  }, [])

  // Convert 24h to 12h AM/PM format for display
  const formatTime12h = (time24) => {
    if (!time24) return ''
    const [hours, minutes] = time24.split(':')
    const h = parseInt(hours)
    const ampm = h >= 12 ? 'PM' : 'AM'
    const h12 = h % 12 || 12
    return `${h12}:${minutes} ${ampm}`
  }

  // Countdown timer calculation
  const calculateCountdown = (scheduledTimes) => {
    if (!scheduledTimes || scheduledTimes.length === 0) return null

    const now = new Date()
    const currentMinutes = now.getHours() * 60 + now.getMinutes()

    // Find next scheduled time
    for (let time of scheduledTimes) {
      const [hours, minutes] = time.split(':').map(Number)
      const scheduledMinutes = hours * 60 + minutes

      if (scheduledMinutes > currentMinutes) {
        const diff = scheduledMinutes - currentMinutes
        const hoursLeft = Math.floor(diff / 60)
        const minutesLeft = diff % 60
        return {
          time: time,
          formatted: formatTime12h(time),
          hoursLeft,
          minutesLeft,
          totalMinutes: diff
        }
      }
    }

    // If no time found today, next is tomorrow's first time
    const [hours, minutes] = scheduledTimes[0].split(':').map(Number)
    const scheduledMinutes = hours * 60 + minutes
    const diff = (24 * 60 - currentMinutes) + scheduledMinutes
    const hoursLeft = Math.floor(diff / 60)
    const minutesLeft = diff % 60
    return {
      time: scheduledTimes[0],
      formatted: formatTime12h(scheduledTimes[0]) + ' (Tomorrow)',
      hoursLeft,
      minutesLeft,
      totalMinutes: diff
    }
  }

  useEffect(() => {
    // OPTIMIZED: Load data ONCE on mount, then use manual refresh only
    fetchOFDOrders()
    fetchSchedulerStatus()
  }, []) // Empty dependency - run once on mount only

  // Separate useEffect for countdown timer - updates every minute
  useEffect(() => {
    // Initial countdown calculation
    if (schedulerStatus?.scheduled_times) {
      setCountdown(calculateCountdown(schedulerStatus.scheduled_times))
    }

    // Update countdown timer every 10 seconds for real-time feel
    const countdownInterval = setInterval(() => {
      if (schedulerStatus?.scheduled_times) {
        const newCountdown = calculateCountdown(schedulerStatus.scheduled_times)
        setCountdown(newCountdown)
        console.log('[Countdown Update]', new Date().toLocaleTimeString(), newCountdown)
      }
    }, 10000)  // Update every 10 seconds for real-time updates

    return () => {
      clearInterval(countdownInterval)
    }
  }, [schedulerStatus?.scheduled_times]) // Re-run when scheduled_times changes

  // NEW: Auto-refresh scheduler status when calling session is active
  useEffect(() => {
    let statusPollInterval = null

    // If calling session is active, poll scheduler status every 3 seconds
    if (schedulerStatus?.live_session?.is_calling) {
      console.log('[Live Session] Auto-polling enabled - refreshing every 3 seconds')
      statusPollInterval = setInterval(() => {
        fetchSchedulerStatus()
      }, 3000) // Poll every 3 seconds during active calls
    }

    return () => {
      if (statusPollInterval) {
        clearInterval(statusPollInterval)
        console.log('[Live Session] Auto-polling disabled')
      }
    }
  }, [schedulerStatus?.live_session?.is_calling]) // Re-run when is_calling status changes

  // REMOVED: fetchCalledOrders() - no longer needed, call history is in OFD orders

  const fetchPendingCalls = async () => {
    setLoadingPending(true)
    try {
      const response = await axios.get(`${API_BASE_URL}/orders/pending-calls/`)
      setPendingCalls(response.data)
      setLoadingPending(false)
    } catch (err) {
      console.error('Failed to fetch pending calls:', err)
      setLoadingPending(false)
    }
  }

  const fetchOFDOrders = async (bypassCache = false) => {
    setError(null)

    try {
      // Add ?refresh=true to bypass backend cache if needed
      const url = bypassCache
        ? `${API_BASE_URL}/orders/ofd/?refresh=true`
        : `${API_BASE_URL}/orders/ofd/`

      const response = await axios.get(url)

      // Ensure response data has proper structure
      const responseData = response.data || {}
      if (!responseData.orders) {
        responseData.orders = []
      }
      if (typeof responseData.total_count === 'undefined') {
        responseData.total_count = responseData.orders.length
      }
      if (typeof responseData.ofd_count === 'undefined') {
        responseData.ofd_count = 0
      }
      if (typeof responseData.undelivered_count === 'undefined') {
        responseData.undelivered_count = 0
      }

      setData(responseData)
      setLoading(false)

      // Update called AWBs from order data (no separate API call needed)
      const awbs = new Set(
        responseData.orders
          .filter(order => order.call_history?.has_been_called)
          .map(order => order.awb)
      )
      setCalledAwbs(awbs)

      // Cache temporarily disabled - no save to localStorage
    } catch (err) {
      console.error('OFD Orders API Error:', err)
      console.error('Error response:', err.response)
      console.error('Error message:', err.message)
      const errorMsg = err.response?.data?.error || err.response?.data?.message || err.message || 'Failed to fetch OFD orders'
      setError(errorMsg)
      setLoading(false)
    }
  }

  const fetchSchedulerStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/orders/scheduler/`)
      setSchedulerStatus(response.data)
      return response.data  // Return for smart polling
    } catch (err) {
      console.error('Failed to fetch scheduler status:', err)
      return null
    }
  }

  const pollCallStatus = async (callId) => {
    const maxPolls = 40 // Poll for max 200 seconds (40 * 5 seconds)
    let pollCount = 0

    const pollInterval = setInterval(async () => {
      try {
        pollCount++

        const statusResponse = await axios.get(`${API_BASE_URL}/orders/check-call-status/${callId}/`)

        console.log(`[Poll ${pollCount}] Call status:`, statusResponse.data.call_status)

        // If call has ended, stop polling
        if (statusResponse.data.is_ended) {
          clearInterval(pollInterval)
          console.log('✅ Call completed! Updated data:', statusResponse.data)

          // Auto-refresh orders to show updated call history
          console.log('[Auto-Refresh] Individual call completed - refreshing orders')
          fetchOFDOrders()

          // Show completion notification
          const completionInfo = `
✅ Call Completed!

Status: ${statusResponse.data.call_status}
Ended Reason: ${statusResponse.data.ended_reason || 'N/A'}
Success: ${statusResponse.data.success_evaluation === 'true' ? 'Successful' : statusResponse.data.success_evaluation === 'false' ? 'Not Successful' : 'N/A'}
Duration: ${statusResponse.data.duration ? Math.round(statusResponse.data.duration) + 's' : 'N/A'}
Cost: ${statusResponse.data.cost ? '$' + statusResponse.data.cost.toFixed(4) : 'N/A'}

Check "Call History" tab for full details.
          `
          alert(completionInfo)
        }

        // Stop polling after max attempts
        if (pollCount >= maxPolls) {
          clearInterval(pollInterval)
          console.log('⏱️ Polling timeout - call may still be in progress')
        }

      } catch (error) {
        console.error('Error polling call status:', error)
        clearInterval(pollInterval)
      }
    }, 5000) // Poll every 5 seconds
  }

  const handleMakeCall = async (order) => {
    setCallingAwb(order.awb)

    try {
      const response = await axios.post(`${API_BASE_URL}/orders/make-call/`, {
        phone_number: order.customer_mobile,
        order_data: {
          awb: order.awb,
          customer_name: order.customer_name,
          order_type: order.order_type,
          current_status: order.current_status,
          customer_address: order.customer_address,
          customer_pincode: order.customer_pincode,
          cod_amount: order.cod_amount
        }
      })

      showToast(
        'Call Initiated Successfully!',
        `Calling ${order.customer_name}. Click "📞 Refresh Call Status" button after 2-3 minutes to see call details.`,
        'success'
      )
      setCallingAwb(null)

      // DISABLED: Automatic polling to save VAPI API calls
      // User will manually click "Refresh Call Status" button when needed
      // pollCallStatus(response.data.id)

      // Add AWB to called list and refresh
      setCalledAwbs(prev => new Set([...prev, order.awb]))

      // Refresh orders to update call tags (no separate fetchCalledOrders needed)
      setTimeout(() => {
        if (activeTab === 'pending') {
          fetchPendingCalls()
        }
      }, 2000)
    } catch (err) {
      showToast(
        'Call Failed',
        err.response?.data?.error || err.message,
        'error'
      )
      setCallingAwb(null)
    }
  }

  const handleStartScheduler = async () => {
    // Validate time - only allow between 8 AM to 8 PM
    const [hours, minutes] = scheduledTime.split(':').map(Number)

    if (hours < 8 || hours >= 20) {
      showToast(
        'Invalid Time',
        `Calls can only be scheduled between 8:00 AM to 8:00 PM. You selected: ${formatTime12h(scheduledTime)}`,
        'warning'
      )
      return
    }

    setIsStartingScheduler(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/orders/scheduler/`, {
        action: 'start',
        time: scheduledTime
      })
      showToast(
        'Scheduler Started!',
        `Daily calls will be made at ${formatTime12h(scheduledTime)}`,
        'success'
      )
      fetchSchedulerStatus()
    } catch (err) {
      showToast(
        'Scheduler Start Failed',
        err.response?.data?.error || err.message,
        'error'
      )
    } finally {
      setIsStartingScheduler(false)
    }
  }

  const handleStopScheduler = async () => {
    setIsStoppingScheduler(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/orders/scheduler/`, {
        action: 'stop'
      })
      showToast('Scheduler Stopped', response.data.message, 'info')
      fetchSchedulerStatus()
    } catch (err) {
      showToast(
        'Scheduler Stop Failed',
        err.response?.data?.error || err.message,
        'error'
      )
    } finally {
      setIsStoppingScheduler(false)
    }
  }

  const handleRunNow = async () => {
    if (!window.confirm('This will call ALL OFD and Undelivered orders immediately. Continue?')) {
      return
    }

    setIsRunningNow(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/orders/scheduler/`, {
        action: 'run_now'
      })
      showToast('Calls Started', response.data.message, 'success')
    } catch (err) {
      showToast(
        'Run Failed',
        err.response?.data?.error || err.message,
        'error'
      )
    } finally {
      setIsRunningNow(false)
    }
  }

  const handleCleanupDelivered = async () => {
    if (!window.confirm('⚠️ This will check all orders via iThink API and DELETE delivered/RTO orders from database. Continue?')) {
      return
    }

    setIsCleaningUp(true)
    try {
      const response = await axios.post(`${API_BASE_URL}/orders/cleanup-delivered/`)
      const { deleted_count, kept_count } = response.data
      showToast(
        'Cleanup Complete!',
        `Deleted: ${deleted_count} orders | Kept: ${kept_count} active orders`,
        'success'
      )

      // Refresh data
      fetchOFDOrders()
      fetchPendingCalls()
    } catch (err) {
      showToast(
        'Cleanup Failed',
        err.response?.data?.error || err.message,
        'error'
      )
    } finally {
      setIsCleaningUp(false)
    }
  }

  const handleCopyPhone = async (phone) => {
    try {
      await navigator.clipboard.writeText(phone)
      setCopiedPhone(phone)
      showToast('Copied!', `Phone number ${phone} copied to clipboard`, 'success')

      // No timeout - stays copied until another number is copied
    } catch (err) {
      showToast('Copy Failed', 'Failed to copy phone number', 'error')
    }
  }

  const handleRefreshCallStatus = async () => {
    setIsRefreshing(true)
    try {
      // SMART FILTERING: Only fetch calls with missing data (Pending)
      // Filter: ended_reason is null OR empty
      const pendingCallIds = data.orders
        .filter(order => {
          const history = order.call_history
          // Has call_id AND (no ended_reason OR ended_reason is empty/pending)
          return history?.call_id && (!history.ended_reason || history.ended_reason === 'Pending')
        })
        .map(order => order.call_history.call_id)

      if (pendingCallIds.length === 0) {
        showToast(
          'All Calls Updated!',
          'All calls already have status. Nothing to refresh!',
          'info'
        )
        setIsRefreshing(false)
        return
      }

      console.log(`[Smart Refresh] Fetching status for ${pendingCallIds.length} pending calls (skipping already complete calls)`)
      console.log(`[Smart Refresh] Call IDs:`, pendingCallIds)

      const response = await axios.post(`${API_BASE_URL}/orders/poll-call-status/`, {
        call_ids: pendingCallIds
      })

      const { updated_calls, failed_calls } = response.data

      console.log(`[Smart Refresh] Response - Updated: ${updated_calls?.length || 0}, Failed: ${failed_calls?.length || 0}`)

      // Log details of each updated call
      if (updated_calls && updated_calls.length > 0) {
        updated_calls.forEach(call => {
          console.log(`[Call Updated] ${call.call_id}: ended_reason=${call.ended_reason}, status=${call.status}`)
        })
      }

      // Log details of failed calls
      if (failed_calls && failed_calls.length > 0) {
        failed_calls.forEach(call => {
          console.error(`[Call Failed] ${call.call_id}: ${call.error}`)
        })
      }

      showToast(
        'Call Status Updated!',
        `Updated: ${updated_calls?.length || 0} calls${failed_calls?.length > 0 ? `, Failed: ${failed_calls.length}` : ''}`,
        'success'
      )

      // IMPORTANT: Clear localStorage cache and force backend refresh with cache bypass
      localStorage.removeItem('ofd_orders_cache')

      // Fetch fresh data from backend with cache bypass (refresh=true)
      setTimeout(() => {
        fetchOFDOrders(true) // true = bypass backend cache
      }, 500) // Small delay to let database updates propagate
    } catch (err) {
      showToast(
        'Refresh Failed',
        err.response?.data?.error || err.message,
        'error'
      )
    } finally {
      setIsRefreshing(false)
    }
  }

  if (loading) {
    return <div className="loading">Loading OFD and Undelivered orders...</div>
  }

  if (error) {
    return <div className="error-message">Error: {error}</div>
  }

  if (!data) {
    return null
  }

  return (
    <div className="ofd-orders">
      <Toast />
      <div className="section-header">
        <div className="header-left">
          <h2>Out For Delivery & Undelivered Orders</h2>
          <div className="count-badges">
            <div className="count-badge total">{data.total_count} Total Orders</div>
            {data.ofd_count > 0 && (
              <div className="count-badge ofd">{data.ofd_count} OFD</div>
            )}
            {data.undelivered_count > 0 && (
              <div className="count-badge undelivered">{data.undelivered_count} Undelivered</div>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <button
            onClick={() => { localStorage.removeItem('ofd_orders_cache'); fetchOFDOrders(true); }}
            style={{
              padding: '0.65rem 1.25rem',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              fontWeight: '600',
              cursor: 'pointer',
              fontSize: '0.9rem',
              transition: 'all 0.3s',
              boxShadow: '0 2px 8px rgba(102, 126, 234, 0.3)',
              whiteSpace: 'nowrap'
            }}
            onMouseOver={(e) => {
              e.target.style.transform = 'translateY(-2px)'
              e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)'
            }}
            onMouseOut={(e) => {
              e.target.style.transform = 'translateY(0)'
              e.target.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.3)'
            }}
          >
            🔄 Refresh Data
          </button>

          <button
            onClick={handleRefreshCallStatus}
            disabled={isRefreshing}
            style={{
              padding: '0.65rem 1.25rem',
              borderRadius: '10px',
              background: isRefreshing
                ? 'linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%)'
                : 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
              color: 'white',
              border: 'none',
              fontWeight: '600',
              cursor: isRefreshing ? 'not-allowed' : 'pointer',
              fontSize: '0.9rem',
              transition: 'all 0.3s',
              opacity: isRefreshing ? 0.7 : 1,
              boxShadow: isRefreshing ? 'none' : '0 2px 8px rgba(79, 172, 254, 0.3)',
              whiteSpace: 'nowrap'
            }}
            onMouseOver={(e) => {
              if (!isRefreshing) {
                e.target.style.transform = 'translateY(-2px)'
                e.target.style.boxShadow = '0 4px 12px rgba(79, 172, 254, 0.4)'
              }
            }}
            onMouseOut={(e) => {
              e.target.style.transform = 'translateY(0)'
              e.target.style.boxShadow = isRefreshing ? 'none' : '0 2px 8px rgba(79, 172, 254, 0.3)'
            }}
            title="Poll VAPI for latest call status"
          >
            {isRefreshing ? '⏳ Updating...' : '📞 Call Status'}
          </button>

          <button
            onClick={() => { localStorage.clear(); sessionStorage.clear(); location.reload(); }}
            style={{
              padding: '0.65rem 1.25rem',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
              color: 'white',
              border: 'none',
              fontWeight: '600',
              cursor: 'pointer',
              fontSize: '0.9rem',
              transition: 'all 0.3s',
              boxShadow: '0 2px 8px rgba(240, 147, 251, 0.3)',
              whiteSpace: 'nowrap'
            }}
            onMouseOver={(e) => {
              e.target.style.transform = 'translateY(-2px)'
              e.target.style.boxShadow = '0 4px 12px rgba(240, 147, 251, 0.4)'
            }}
            onMouseOut={(e) => {
              e.target.style.transform = 'translateY(0)'
              e.target.style.boxShadow = '0 2px 8px rgba(240, 147, 251, 0.3)'
            }}
            title="Clear all browser cache and reload"
          >
            🗑️ Clear Cache
          </button>
        </div>
      </div>

      <div className="scheduler-panel">
        <h3>Auto Call Scheduler</h3>
        <div className="scheduler-controls">
          <div className="time-input-group">
            <label htmlFor="scheduled-time">Scheduled Time:</label>
            <input
              type="time"
              id="scheduled-time"
              value={scheduledTime}
              onChange={(e) => setScheduledTime(e.target.value)}
              disabled={schedulerStatus?.running}
            />
          </div>

          <div className="scheduler-buttons">
            {schedulerStatus?.running ? (
              <>
                <div className="status-indicator running">
                  Running at {formatTime12h(schedulerStatus.scheduled_time)}
                </div>
                <button onClick={handleStopScheduler} className="stop-button">
                  Stop Scheduler
                </button>
              </>
            ) : (
              <>
                <button onClick={handleStartScheduler} className="start-button">
                  Start Scheduler at {formatTime12h(scheduledTime)}
                </button>
                <div className="time-preview">
                  {formatTime12h(scheduledTime)}
                </div>
              </>
            )}

            <button onClick={handleRunNow} className="run-now-button">
              Call All Now
            </button>

            <button
              onClick={handleCleanupDelivered}
              className="cleanup-button"
              style={{
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                marginLeft: '10px'
              }}
            >
              🗑️ Cleanup Delivered
            </button>
          </div>
        </div>

        {/* Live Session Status - Always show when scheduler status exists */}
        {schedulerStatus && (
          <div style={{
            marginTop: '1.5rem',
            padding: '1.5rem',
            background: schedulerStatus.live_session?.is_calling
              ? 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)'
              : 'linear-gradient(135deg, #ecf0f115 0%, #95a5a615 100%)',
            borderRadius: '12px',
            border: schedulerStatus.live_session?.is_calling
              ? '2px solid #667eea'
              : '2px solid #bdc3c7',
            boxShadow: schedulerStatus.live_session?.is_calling
              ? '0 4px 15px rgba(102, 126, 234, 0.3)'
              : '0 2px 8px rgba(0,0,0,0.1)'
          }}>
            {/* Header with Live Badge */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1.5rem'
            }}>
              <h3 style={{
                margin: 0,
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                fontSize: '1.25rem',
                color: '#2c3e50'
              }}>
                📊 Live Call Session
                {schedulerStatus.live_session.is_calling && (
                  <span style={{
                    padding: '0.35rem 1rem',
                    background: 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)',
                    color: 'white',
                    borderRadius: '20px',
                    fontSize: '0.75rem',
                    fontWeight: '700',
                    letterSpacing: '0.5px',
                    animation: 'pulse 2s infinite',
                    boxShadow: '0 2px 10px rgba(231, 76, 60, 0.4)'
                  }}>
                    🔴 LIVE
                  </span>
                )}
              </h3>

              {/* Current Time */}
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.75rem', color: '#7f8c8d', marginBottom: '0.25rem' }}>
                  Current Time
                </div>
                <div style={{ fontSize: '1rem', fontWeight: '700', color: '#2c3e50', fontFamily: 'monospace' }}>
                  {schedulerStatus.current_time || new Date().toLocaleTimeString('en-US', { hour12: false })}
                </div>
              </div>
            </div>

            {/* Next Schedule Info - Only when NOT calling */}
            {!schedulerStatus.live_session.is_calling && countdown && (
              <div style={{
                background: 'linear-gradient(135deg, #3498db 0%, #2980b9 100%)',
                padding: '1.25rem',
                borderRadius: '10px',
                marginBottom: '1.5rem',
                color: 'white',
                boxShadow: '0 4px 15px rgba(52, 152, 219, 0.3)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.85rem', opacity: 0.9, marginBottom: '0.5rem' }}>
                      ⏰ Next Automatic Call Session
                    </div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.75rem' }}>
                      {countdown.formatted}
                    </div>
                    <div style={{ fontSize: '0.9rem', opacity: 0.95, lineHeight: '1.8' }}>
                      📞 Call times: {schedulerStatus.scheduled_times?.map(formatTime12h).join(' • ')}
                      <br />
                      🗑️ Daily cleanup: {schedulerStatus.cleanup_time ? formatTime12h(schedulerStatus.cleanup_time) : '9:45 AM'}
                    </div>
                  </div>

                  {/* Countdown Timer */}
                  <div style={{
                    background: 'rgba(255,255,255,0.2)',
                    padding: '1rem 1.5rem',
                    borderRadius: '10px',
                    textAlign: 'center',
                    minWidth: '180px',
                    backdropFilter: 'blur(10px)'
                  }}>
                    <div style={{ fontSize: '0.75rem', marginBottom: '0.5rem', opacity: 0.9 }}>
                      Starts in
                    </div>
                    <div style={{
                      fontSize: '2rem',
                      fontWeight: '700',
                      fontFamily: 'monospace',
                      letterSpacing: '2px'
                    }}>
                      {countdown.hoursLeft > 0 && `${countdown.hoursLeft}h `}
                      {countdown.minutesLeft}m
                    </div>
                    <div style={{ fontSize: '0.7rem', marginTop: '0.25rem', opacity: 0.8 }}>
                      ({countdown.totalMinutes} minutes)
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Session Start Info - When calling */}
            {schedulerStatus.live_session.is_calling && schedulerStatus.live_session.session_start && (
              <div style={{
                background: 'rgba(46, 204, 113, 0.1)',
                border: '1px solid rgba(46, 204, 113, 0.3)',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                marginBottom: '1.25rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem'
              }}>
                <span style={{ fontSize: '1.25rem' }}>🚀</span>
                <div>
                  <div style={{ fontSize: '0.75rem', color: '#7f8c8d' }}>Session Started</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: '600', color: '#27ae60' }}>
                    {schedulerStatus.live_session.session_start}
                  </div>
                </div>
              </div>
            )}

            {schedulerStatus.live_session.is_calling ? (
              <>
                {/* Progress Bar */}
                {schedulerStatus.live_session.total_to_call > 0 && (
                  <div style={{ marginBottom: '1rem' }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginBottom: '0.5rem',
                      fontSize: '0.85rem',
                      fontWeight: '600'
                    }}>
                      <span>Progress: {schedulerStatus.live_session.completed} / {schedulerStatus.live_session.total_to_call}</span>
                      <span>{Math.round((schedulerStatus.live_session.completed / schedulerStatus.live_session.total_to_call) * 100)}%</span>
                    </div>
                    <div style={{
                      width: '100%',
                      height: '20px',
                      background: '#e0e0e0',
                      borderRadius: '10px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${(schedulerStatus.live_session.completed / schedulerStatus.live_session.total_to_call) * 100}%`,
                        height: '100%',
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        transition: 'width 0.5s ease'
                      }}></div>
                    </div>
                  </div>
                )}

                {/* Current Order */}
                {schedulerStatus.live_session.current_order && (
                  <div style={{
                    padding: '0.75rem',
                    background: 'white',
                    borderRadius: '6px',
                    marginBottom: '1rem',
                    border: '2px solid #667eea'
                  }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#667eea', marginBottom: '0.25rem' }}>
                      📞 Currently Calling:
                    </div>
                    <div style={{ fontSize: '0.9rem', fontWeight: '600' }}>
                      {schedulerStatus.live_session.current_order.awb} - {schedulerStatus.live_session.current_order.customer_name}
                      {schedulerStatus.live_session.current_order.retry_count > 0 && (
                        <span style={{
                          marginLeft: '0.5rem',
                          padding: '0.2rem 0.5rem',
                          background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                          color: 'white',
                          borderRadius: '8px',
                          fontSize: '0.7rem'
                        }}>
                          Retry #{schedulerStatus.live_session.current_order.retry_count}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Stats */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '0.75rem',
                  marginBottom: '1rem'
                }}>
                  <div style={{
                    padding: '0.75rem',
                    background: 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)',
                    borderRadius: '6px',
                    textAlign: 'center',
                    color: 'white'
                  }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '700' }}>{schedulerStatus.live_session.successful}</div>
                    <div style={{ fontSize: '0.75rem' }}>Successful</div>
                  </div>
                  <div style={{
                    padding: '0.75rem',
                    background: 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)',
                    borderRadius: '6px',
                    textAlign: 'center',
                    color: 'white'
                  }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '700' }}>{schedulerStatus.live_session.failed}</div>
                    <div style={{ fontSize: '0.75rem' }}>Failed</div>
                  </div>
                  <div style={{
                    padding: '0.75rem',
                    background: 'linear-gradient(135deg, #f39c12 0%, #e67e22 100%)',
                    borderRadius: '6px',
                    textAlign: 'center',
                    color: 'white'
                  }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '700' }}>{schedulerStatus.live_session.skipped}</div>
                    <div style={{ fontSize: '0.75rem' }}>Skipped</div>
                  </div>
                </div>

                {/* Live Logs */}
                {schedulerStatus.live_session.logs && schedulerStatus.live_session.logs.length > 0 && (
                  <div>
                    <div style={{ fontSize: '0.9rem', fontWeight: '700', marginBottom: '0.5rem' }}>
                      📝 Live Logs (Last 10):
                    </div>
                    <div style={{
                      maxHeight: '200px',
                      overflowY: 'auto',
                      background: '#2c3e50',
                      borderRadius: '6px',
                      padding: '0.75rem',
                      fontFamily: 'monospace',
                      fontSize: '0.8rem'
                    }}>
                      {schedulerStatus.live_session.logs.slice(-10).reverse().map((log, index) => (
                        <div key={index} style={{
                          padding: '0.25rem 0',
                          borderBottom: index < schedulerStatus.live_session.logs.slice(-10).length - 1 ? '1px solid #34495e' : 'none',
                          color: log.type === 'success' ? '#2ecc71' : log.type === 'error' ? '#e74c3c' : log.type === 'warning' ? '#f39c12' : '#ecf0f1'
                        }}>
                          <span style={{ color: '#95a5a6' }}>[{log.time}]</span> {log.message}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div style={{
                textAlign: 'center',
                padding: '2.5rem 1.5rem',
                color: '#7f8c8d'
              }}>
                <div style={{
                  fontSize: '4rem',
                  marginBottom: '1rem',
                  opacity: 0.6
                }}>
                  {schedulerStatus?.running ? '⏳' : '⏸️'}
                </div>
                <div style={{
                  fontSize: '1.25rem',
                  fontWeight: '700',
                  color: '#2c3e50',
                  marginBottom: '0.75rem'
                }}>
                  {schedulerStatus?.running ? 'Waiting for Next Session' : 'Scheduler Stopped'}
                </div>
                <div style={{
                  fontSize: '0.95rem',
                  color: '#7f8c8d',
                  lineHeight: '1.6',
                  maxWidth: '500px',
                  margin: '0 auto'
                }}>
                  {schedulerStatus?.running ? (
                    <>
                      The scheduler is running in the background.
                      Calls will automatically start at the scheduled times.
                    </>
                  ) : (
                    'Start the scheduler to enable automatic calls at scheduled times.'
                  )}
                </div>

                {/* Backend Session Logs - Always show if available */}
                {schedulerStatus?.live_session?.logs && schedulerStatus.live_session.logs.length > 0 && (
                  <div style={{
                    marginTop: '1.5rem',
                    background: 'rgba(52, 152, 219, 0.05)',
                    border: '1px solid rgba(52, 152, 219, 0.2)',
                    borderRadius: '8px',
                    padding: '1rem',
                    textAlign: 'left'
                  }}>
                    <div style={{
                      fontSize: '0.9rem',
                      fontWeight: '700',
                      color: '#3498db',
                      marginBottom: '0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      🖥️ Backend Session Logs (Last 10)
                    </div>
                    <div style={{
                      maxHeight: '200px',
                      overflowY: 'auto',
                      background: '#2c3e50',
                      borderRadius: '6px',
                      padding: '0.75rem',
                      fontFamily: 'monospace',
                      fontSize: '0.8rem'
                    }}>
                      {schedulerStatus.live_session.logs.slice(-10).reverse().map((log, index) => (
                        <div key={index} style={{
                          padding: '0.25rem 0',
                          borderBottom: index < Math.min(10, schedulerStatus.live_session.logs.length) - 1 ? '1px solid #34495e' : 'none',
                          color: log.type === 'success' ? '#2ecc71' : log.type === 'error' ? '#e74c3c' : log.type === 'warning' ? '#f39c12' : '#ecf0f1'
                        }}>
                          <span style={{ color: '#95a5a6' }}>[{log.time}]</span> {log.message}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Frontend Console Logs - Always show if available */}
                {frontendLogs.length > 0 && (
                  <div style={{
                    marginTop: '1.5rem',
                    background: 'rgba(155, 89, 182, 0.05)',
                    border: '1px solid rgba(155, 89, 182, 0.2)',
                    borderRadius: '8px',
                    padding: '1rem',
                    textAlign: 'left'
                  }}>
                    <div style={{
                      fontSize: '0.9rem',
                      fontWeight: '700',
                      color: '#9b59b6',
                      marginBottom: '0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      💻 Frontend Console Logs (Last 10)
                    </div>
                    <div style={{
                      maxHeight: '200px',
                      overflowY: 'auto',
                      background: '#2c3e50',
                      borderRadius: '6px',
                      padding: '0.75rem',
                      fontFamily: 'monospace',
                      fontSize: '0.8rem'
                    }}>
                      {frontendLogs.slice(-10).reverse().map((log, index) => (
                        <div key={index} style={{
                          padding: '0.25rem 0',
                          borderBottom: index < Math.min(10, frontendLogs.length) - 1 ? '1px solid #34495e' : 'none',
                          color: log.type === 'error' ? '#e74c3c' : log.type === 'warning' ? '#f39c12' : log.type === 'info' ? '#3498db' : '#ecf0f1'
                        }}>
                          <span style={{ color: '#95a5a6' }}>[{log.time}]</span> {log.message}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="tabs-container">
        <button
          className={`tab ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          📦 All Orders ({data.total_count})
        </button>
        <button
          className={`tab ${activeTab === 'pending' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('pending')
            if (!pendingCalls) fetchPendingCalls()
          }}
        >
          📞 Pending Calls
        </button>
      </div>

      {/* All Orders Tab */}
      {activeTab === 'all' && (!data.orders || data.orders.length === 0 ? (
        <div className="empty-state">
          <p>No OFD or Undelivered orders found</p>
        </div>
      ) : (
        <div className="orders-grid">
          {data.orders.map((order) => (
            <div key={order.awb} className={`order-card ${order.order_type === 'OFD' ? 'ofd-card' : 'undelivered-card'}`}>
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
                  {calledAwbs.has(order.awb) && (
                    <span style={{
                      marginLeft: '0.5rem',
                      padding: '0.25rem 0.75rem',
                      background: 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)',
                      color: 'white',
                      borderRadius: '12px',
                      fontSize: '0.75rem',
                      fontWeight: '700',
                      letterSpacing: '0.5px'
                    }}>
                      ✓ CALLED
                    </span>
                  )}
                </div>
                <div className={`status-badge ${order.order_type === 'OFD' ? 'ofd-status' : 'undelivered-status'}`}>
                  {order.order_type}
                </div>
              </div>

              {order.current_status && (
                <div className="current-status-display">
                  <span className="status-label">Status:</span>
                  <span className="status-text">{order.current_status}</span>
                </div>
              )}

              <button
                onClick={() => handleMakeCall(order)}
                disabled={callingAwb === order.awb}
                className="call-button"
              >
                {callingAwb === order.awb ? 'Calling...' : 'Make Call'}
              </button>

              {/* Basic Info - Always Visible */}
              <div className="order-details">
                <div className="detail-row">
                  <span className="label">Customer:</span>
                  <span className="value">{order.customer_name || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Mobile:</span>
                  <span className="value" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {order.customer_mobile || 'N/A'}
                    {order.customer_mobile && order.customer_mobile !== 'N/A' && (
                      <button
                        onClick={() => handleCopyPhone(order.customer_mobile)}
                        className="copy-phone-btn"
                        title="Copy phone number"
                        style={{
                          background: copiedPhone === order.customer_mobile
                            ? 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)'
                            : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                          border: 'none',
                          borderRadius: '8px',
                          padding: '0.4rem 0.6rem',
                          color: 'white',
                          cursor: 'pointer',
                          fontSize: '0.85rem',
                          fontWeight: '600',
                          transition: 'all 0.3s ease',
                          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                        }}
                      >
                        {copiedPhone === order.customer_mobile ? '✓ Copied' : '📋 Copy'}
                      </button>
                    )}
                  </span>
                </div>
              </div>

              {/* More Info Button */}
              <button
                onClick={() => toggleOrderSection(order.awb, 'basic')}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  marginTop: '1rem',
                  background: expandedOrderDetails[order.awb] === 'basic'
                    ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                    : 'linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%)',
                  border: 'none',
                  borderRadius: '12px',
                  color: 'white',
                  fontWeight: '700',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                }}
              >
                {expandedOrderDetails[order.awb] === 'basic' ? '▼ Hide Details' : '▶ More Info'}
              </button>

              {/* Collapsible Order Details */}
              {expandedOrderDetails[order.awb] === 'basic' && (
                <div className="order-details" style={{
                  marginTop: '1rem',
                  padding: '1rem',
                  background: 'rgba(255, 255, 255, 0.5)',
                  borderRadius: '12px',
                  animation: 'fadeInUp 0.3s ease-out'
                }}>
                  <div className="detail-row">
                    <span className="label">Address:</span>
                    <span className="value">{order.customer_address || 'N/A'}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Pincode:</span>
                    <span className="value">{order.customer_pincode || 'N/A'}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Order Date:</span>
                    <span className="value">{order.order_date || 'N/A'}</span>
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
              )}

              {/* Call History Section */}
              {order.call_history && (
                <>
                  <button
                    onClick={() => toggleOrderSection(order.awb, 'call')}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      marginTop: '1rem',
                      background: expandedOrderDetails[order.awb] === 'call'
                        ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
                        : 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                      border: 'none',
                      borderRadius: '12px',
                      color: 'white',
                      fontWeight: '700',
                      fontSize: '0.9rem',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    📞 {expandedOrderDetails[order.awb] === 'call' ? '▼ Hide Call Details' : `▶ Call Details (${order.call_history.call_count})`}
                  </button>

                  {expandedOrderDetails[order.awb] === 'call' && (
                    <div style={{
                      marginTop: '1rem',
                      padding: '1rem',
                      background: 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)',
                      borderRadius: '12px',
                      border: '2px solid #667eea50',
                      animation: 'fadeInUp 0.3s ease-out'
                    }}>
                      <div className="detail-row" style={{ marginBottom: '0.5rem' }}>
                        <span className="label">Call Status:</span>
                        <span className="value" style={{
                          fontWeight: '700',
                          color: order.call_history.has_been_called ? '#27ae60' : '#95a5a6'
                        }}>
                          {order.call_history.has_been_called ? `✓ Called (${order.call_history.call_count})` : '⊗ Not Called Yet'}
                        </span>
                      </div>

                      {order.call_history.has_been_called && (
                        <>
                          <div className="detail-row" style={{ marginBottom: '0.5rem' }}>
                            <span className="label">Ended Reason:</span>
                            <span className="value" style={{
                              fontWeight: '600',
                              color: order.call_history.ended_reason === 'Pending' ? '#f39c12' : '#34495e'
                            }}>
                              {order.call_history.ended_reason || 'Pending'}
                            </span>
                          </div>

                          <div className="detail-row" style={{ marginBottom: '0.5rem' }}>
                            <span className="label">Success:</span>
                            <span style={{
                              padding: '0.25rem 0.75rem',
                              background: (order.call_history.success_evaluation === 'pass' || order.call_history.success_evaluation === 'Successful')
                                ? 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)'
                                : (order.call_history.success_evaluation === 'fail' || order.call_history.success_evaluation === 'Failed')
                                ? 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)'
                                : 'linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%)',
                              color: 'white',
                              borderRadius: '12px',
                              fontSize: '0.75rem',
                              fontWeight: '700',
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px'
                            }}>
                              {order.call_history.success_evaluation === 'pass' ? '✓ PASS' : order.call_history.success_evaluation === 'fail' ? '✗ FAIL' : (order.call_history.success_evaluation || 'Pending')}
                            </span>
                          </div>

                          <div className="detail-row">
                            <span className="label">Last Call Time:</span>
                            <span className="value" style={{ fontWeight: '600' }}>
                              {order.call_history.last_call_time || 'N/A'}
                            </span>
                          </div>
                        </>
                      )}

                      {/* Call Duration */}
                      {order.call_history.duration && (
                        <div className="detail-row" style={{ marginBottom: '0.5rem' }}>
                          <span className="label">Duration:</span>
                          <span className="value" style={{ fontWeight: '600' }}>
                            {Math.floor(order.call_history.duration / 60)}m {order.call_history.duration % 60}s
                          </span>
                        </div>
                      )}

                      {/* Recording Player - NEW! */}
                      {order.call_history.recording_url && (
                        <div style={{
                          marginTop: '1rem',
                          padding: '0.75rem',
                          background: 'linear-gradient(135deg, #667eea10 0%, #764ba210 100%)',
                          borderRadius: '6px',
                          border: '1px solid #667eea30'
                        }}>
                          <div style={{
                            fontSize: '0.85rem',
                            fontWeight: '700',
                            color: '#667eea',
                            marginBottom: '0.5rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                          }}>
                            🎙️ Call Recording
                          </div>
                          <audio
                            controls
                            style={{
                              width: '100%',
                              height: '40px',
                              borderRadius: '6px'
                            }}
                            preload="metadata"
                          >
                            <source src={order.call_history.recording_url} type="audio/mpeg" />
                            <source src={order.call_history.recording_url} type="audio/wav" />
                            Your browser does not support the audio element.
                          </audio>
                          <div style={{
                            marginTop: '0.5rem',
                            textAlign: 'center'
                          }}>
                            <a
                              href={order.call_history.recording_url}
                              download
                              style={{
                                fontSize: '0.8rem',
                                color: '#667eea',
                                textDecoration: 'none',
                                fontWeight: '600'
                              }}
                            >
                              📥 Download Recording
                            </a>
                          </div>
                        </div>
                      )}

                      {/* Transcript - Improved UI */}
                      {order.call_history.transcript && (
                        <div style={{
                          marginTop: '1rem',
                          padding: '1rem',
                          background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
                          borderRadius: '8px',
                          border: '1px solid #cbd5e0',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                        }}>
                          <div style={{
                            fontSize: '0.9rem',
                            fontWeight: '700',
                            color: '#2d3748',
                            marginBottom: '0.75rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            paddingBottom: '0.5rem',
                            borderBottom: '2px solid #cbd5e0'
                          }}>
                            💬 Conversation Transcript
                          </div>
                          <div style={{
                            maxHeight: '250px',
                            overflowY: 'auto',
                            background: 'white',
                            padding: '1rem',
                            borderRadius: '6px',
                            boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.06)'
                          }}>
                            {order.call_history.transcript.split('\n').map((line, index) => {
                              const isAI = line.startsWith('AI:')
                              const isUser = line.startsWith('User:')

                              if (!line.trim()) return null

                              return (
                                <div key={index} style={{
                                  marginBottom: '0.75rem',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  alignItems: isAI ? 'flex-start' : 'flex-end'
                                }}>
                                  <div style={{
                                    maxWidth: '85%',
                                    padding: '0.6rem 0.9rem',
                                    borderRadius: '12px',
                                    background: isAI
                                      ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                                      : 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                                    color: 'white',
                                    fontSize: '0.85rem',
                                    lineHeight: '1.5',
                                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                                    wordBreak: 'break-word'
                                  }}>
                                    <div style={{
                                      fontSize: '0.7rem',
                                      opacity: 0.9,
                                      marginBottom: '0.25rem',
                                      fontWeight: '600',
                                      textTransform: 'uppercase',
                                      letterSpacing: '0.5px'
                                    }}>
                                      {isAI ? '🤖 AI Assistant' : '👤 Customer'}
                                    </div>
                                    <div>
                                      {line.replace(/^(AI:|User:)\s*/, '')}
                                    </div>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}

                      {order.call_history.needs_retry && order.call_history.has_been_called && (
                        <div style={{
                          marginTop: '0.75rem',
                          padding: '0.5rem',
                          background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                          color: 'white',
                          borderRadius: '6px',
                          fontSize: '0.8rem',
                          fontWeight: '600',
                          textAlign: 'center'
                        }}>
                          🔁 Retry #{order.call_history.retry_count + 1} Needed
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}

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
            </div>
          ))}
        </div>
      ))}

      {/* Pending Calls Tab */}
      {activeTab === 'pending' && (
        <div>
          {loadingPending ? (
            <div className="loading">Loading pending calls...</div>
          ) : !pendingCalls ? (
            <div className="empty-state">
              <p>Click to load pending calls</p>
            </div>
          ) : pendingCalls.total_count === 0 ? (
            <div className="empty-state">
              <p>✓ No pending calls! All orders have been called successfully.</p>
            </div>
          ) : (
            <>
              <div className="count-badges" style={{marginBottom: '1.5rem'}}>
                <div className="count-badge total">
                  📞 {pendingCalls.total_count} Pending Calls
                </div>
                {pendingCalls.not_called_count > 0 && (
                  <div className="count-badge" style={{background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'}}>
                    🆕 {pendingCalls.not_called_count} Not Called
                  </div>
                )}
                {pendingCalls.retry_count > 0 && (
                  <div className="count-badge" style={{background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'}}>
                    🔁 {pendingCalls.retry_count} Retry Needed
                  </div>
                )}
              </div>

              <div className="orders-grid">
                {pendingCalls.pending_calls.map((order) => (
                  <div key={order.awb} className="order-card pending-call-card">
                    {order.call_status === 'not_called' ? (
                      <div className="not-called-badge">🆕 NOT CALLED</div>
                    ) : (
                      <div className="retry-badge">🔁 RETRY #{order.retry_count + 1}</div>
                    )}

                    <div className="order-header">
                      <div className="awb-number">
                        <strong>AWB:</strong>
                        <span>{order.awb}</span>
                      </div>
                      <div className={`status-badge ${order.order_type === 'OFD' ? 'ofd-status' : 'undelivered-status'}`}>
                        {order.order_type}
                      </div>
                    </div>

                    {order.current_status && (
                      <div className="current-status-display">
                        <span className="status-label">Status:</span>
                        <span className="status-text">{order.current_status}</span>
                      </div>
                    )}

                    {order.last_call_reason && (
                      <div className="last-call-info">
                        <strong>Last Call Failed:</strong>
                        Reason: {order.last_call_reason}
                      </div>
                    )}

                    <button
                      onClick={() => handleMakeCall(order)}
                      disabled={callingAwb === order.awb}
                      className="call-button"
                      style={{
                        background: order.call_status === 'retry_needed'
                          ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
                          : 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
                      }}
                    >
                      {callingAwb === order.awb ? 'Calling...' : order.call_status === 'retry_needed' ? '🔁 Retry Call' : '📞 Make Call'}
                    </button>

                    <div className="order-details">
                      <div className="detail-row">
                        <span className="label">Customer:</span>
                        <span className="value">{order.customer_name || 'N/A'}</span>
                      </div>
                      <div className="detail-row">
                        <span className="label">Mobile:</span>
                        <span className="value" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          {order.customer_mobile || 'N/A'}
                          {order.customer_mobile && order.customer_mobile !== 'N/A' && (
                            <button
                              onClick={() => handleCopyPhone(order.customer_mobile)}
                              className="copy-phone-btn"
                              title="Copy phone number"
                              style={{
                                background: copiedPhone === order.customer_mobile
                                  ? 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)'
                                  : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                border: 'none',
                                borderRadius: '8px',
                                padding: '0.4rem 0.6rem',
                                color: 'white',
                                cursor: 'pointer',
                                fontSize: '0.85rem',
                                fontWeight: '600',
                                transition: 'all 0.3s ease',
                                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
                              }}
                            >
                              {copiedPhone === order.customer_mobile ? '✓ Copied' : '📋 Copy'}
                            </button>
                          )}
                        </span>
                      </div>
                      <div className="detail-row">
                        <span className="label">Address:</span>
                        <span className="value">{order.customer_address || 'N/A'}</span>
                      </div>
                      <div className="detail-row">
                        <span className="label">Pincode:</span>
                        <span className="value">{order.customer_pincode || 'N/A'}</span>
                      </div>
                      {order.cod_amount && (
                        <div className="detail-row">
                          <span className="label">COD Amount:</span>
                          <span className="value cod">₹{order.cod_amount}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default OFDOrders
