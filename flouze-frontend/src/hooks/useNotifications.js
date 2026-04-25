import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import client from '../api/client'

export function useNotifications() {
  const [notifications, setNotifications] = useState([])
  const [unread, setUnread] = useState(0)
  const token = useAuthStore((s) => s.accessToken)
  const wsRef = useRef(null)

  // Load existing notifications on token change (login)
  useEffect(() => {
    if (!token) { setNotifications([]); setUnread(0); return }
    client.get('/notifications')
      .then(({ data }) => {
        setNotifications(data.slice(0, 30))
        setUnread(data.filter((n) => !n.read_at).length)
      })
      .catch(() => {})
  }, [token])

  // WebSocket connection — reconnect whenever token changes
  useEffect(() => {
    if (!token) return

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(
      `${proto}//${window.location.host}/api/v1/ws?token=${encodeURIComponent(token)}`
    )
    wsRef.current = ws

    ws.onmessage = (e) => {
      try {
        const notif = JSON.parse(e.data)
        const entry = {
          id: notif.id,
          type: notif.type,
          payload: notif.payload,
          read_at: null,
          created_at: new Date().toISOString(),
        }
        setNotifications((prev) => [entry, ...prev].slice(0, 30))
        setUnread((c) => c + 1)
      } catch {
        // malformed message — ignore
      }
    }

    ws.onerror = () => {
      // Silently degrade — REST polling still works
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [token])

  const markRead = useCallback(async (id) => {
    try {
      await client.patch(`/notifications/${id}/read`)
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n))
      )
      setUnread((c) => Math.max(0, c - 1))
    } catch {
      // ignore
    }
  }, [])

  const markAllRead = useCallback(async () => {
    const ids = notifications.filter((n) => !n.read_at).map((n) => n.id)
    await Promise.all(ids.map((id) => client.patch(`/notifications/${id}/read`).catch(() => {})))
    setNotifications((prev) => prev.map((n) => ({ ...n, read_at: n.read_at ?? new Date().toISOString() })))
    setUnread(0)
  }, [notifications])

  return { notifications, unread, markRead, markAllRead }
}
