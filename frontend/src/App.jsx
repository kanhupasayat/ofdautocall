import { useState, useEffect } from 'react'
import './App.css'
import OrderTracker from './components/OrderTracker'
import Login from './components/Login'
import { setupAxiosInterceptors, isAuthenticated, logout } from './utils/auth'

function App() {
  const [authenticated, setAuthenticated] = useState(false)

  useEffect(() => {
    // Setup axios interceptors for token handling
    setupAxiosInterceptors()

    // Check if user is already authenticated
    setAuthenticated(isAuthenticated())
  }, [])

  const handleLoginSuccess = () => {
    setAuthenticated(true)
  }

  const handleLogout = () => {
    logout()
    setAuthenticated(false)
  }

  if (!authenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <div>
            <h1>InTransit - Order Tracking System</h1>
            <p>Track your orders in real-time</p>
          </div>
          <button onClick={handleLogout} className="logout-button">
            Logout
          </button>
        </div>
      </header>
      <main className="app-main">
        <OrderTracker />
      </main>
    </div>
  )
}

export default App
