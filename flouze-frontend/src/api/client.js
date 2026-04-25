import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const client = axios.create({
  baseURL: '/api/v1',
  withCredentials: true, // send refresh-token httpOnly cookie automatically
})

// Inject access token into every request
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Silent token refresh on 401
let _isRefreshing = false
let _queue = []

const _processQueue = (err, token) => {
  _queue.forEach(({ resolve, reject }) => (err ? reject(err) : resolve(token)))
  _queue = []
}

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const status = error.response?.status

    // Don't retry auth endpoints or already-retried requests
    if (
      status !== 401 ||
      original._retry ||
      original.url?.includes('/auth/')
    ) {
      return Promise.reject(error)
    }

    if (_isRefreshing) {
      return new Promise((resolve, reject) =>
        _queue.push({ resolve, reject })
      ).then((token) => {
        original.headers.Authorization = `Bearer ${token}`
        return client(original)
      })
    }

    original._retry = true
    _isRefreshing = true

    try {
      const { data } = await axios.post(
        '/api/v1/auth/refresh',
        {},
        { withCredentials: true }
      )
      const newToken = data.access_token
      useAuthStore.getState().setAccessToken(newToken)
      _processQueue(null, newToken)
      original.headers.Authorization = `Bearer ${newToken}`
      return client(original)
    } catch (refreshErr) {
      _processQueue(refreshErr, null)
      useAuthStore.getState().logout()
      window.location.href = '/login'
      return Promise.reject(refreshErr)
    } finally {
      _isRefreshing = false
    }
  }
)

export default client
