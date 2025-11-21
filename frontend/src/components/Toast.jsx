import { useState, useEffect } from 'react'
import './Toast.css'

let toastId = 0
const toasts = []
let updateToasts = null

function Toast() {
  const [toastList, setToastList] = useState([])

  useEffect(() => {
    updateToasts = setToastList
    return () => {
      updateToasts = null
    }
  }, [])

  const removeToast = (id) => {
    setToastList(prev => prev.filter(t => t.id !== id))
  }

  return (
    <div className="toast-container">
      {toastList.map((toast) => (
        <div
          key={toast.id}
          className={`toast toast-${toast.type}`}
          onClick={() => removeToast(toast.id)}
        >
          <div className="toast-icon">
            {toast.type === 'success' && '✓'}
            {toast.type === 'error' && '✗'}
            {toast.type === 'info' && 'ℹ'}
            {toast.type === 'warning' && '⚠'}
          </div>
          <div className="toast-content">
            <div className="toast-title">{toast.title}</div>
            {toast.message && <div className="toast-message">{toast.message}</div>}
          </div>
          <button className="toast-close" onClick={() => removeToast(toast.id)}>×</button>
        </div>
      ))}
    </div>
  )
}

// Toast API
export const showToast = (title, message = '', type = 'info', duration = 3000) => {
  const id = ++toastId
  const toast = { id, title, message, type }

  if (updateToasts) {
    updateToasts(prev => [...prev, toast])

    if (duration > 0) {
      setTimeout(() => {
        if (updateToasts) {
          updateToasts(prev => prev.filter(t => t.id !== id))
        }
      }, duration)
    }
  }
}

export default Toast
