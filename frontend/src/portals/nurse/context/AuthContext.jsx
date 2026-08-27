import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login as loginRequest } from '../services/api.js'
import { connectSocket, disconnectSocket } from '../services/socket.js'

const AuthContext = createContext(null)

const TOKEN_KEY = 'medicore_token'
const USER_KEY = 'medicore_user'

function readStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(readStoredUser)
  const navigate = useNavigate()

  // Restore the socket connection on a page refresh when a session already exists.
  useEffect(() => {
    if (token) connectSocket(token)
  }, [token])

  const login = useCallback(async (email, password) => {
    const { data } = await loginRequest(email, password)
    localStorage.setItem(TOKEN_KEY, data.accessToken)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    connectSocket(data.accessToken)
    setToken(data.accessToken)
    setUser(data.user)
    return data
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    disconnectSocket()
    setToken(null)
    setUser(null)
    navigate('/login')
  }, [navigate])

  const value = {
    user,
    token,
    login,
    logout,
    isAuthenticated: Boolean(token),
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
