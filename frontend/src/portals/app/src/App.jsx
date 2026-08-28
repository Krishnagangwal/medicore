import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext.jsx'
import LoginPage from './pages/LoginPage.jsx'
import SignupPage from './pages/SignupPage.jsx'
import NurseDashboardPage from './nurse/pages/DashboardPage.jsx'
import NursePatientsPage from './nurse/pages/PatientsPage.jsx'
import DoctorMainPage from './doctor/pages/MainPage.jsx'

function dashboardPathForRole(role) {
  if (role === 'NURSE') return '/nurse/dashboard'
  if (role === 'DOCTOR') return '/doctor'
  return null
}

// Gates a role's dashboard: bounce unauthenticated visitors to /login, and
// authenticated-but-wrong-role visitors to their own dashboard instead of
// showing a mismatched screen.
function RoleProtectedRoute({ role, children }) {
  const { isAuthenticated, user } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (user?.role !== role) {
    const ownPath = dashboardPathForRole(user?.role)
    return <Navigate to={ownPath || '/login'} replace />
  }
  return children
}

function RootRedirect() {
  const { isAuthenticated, user } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <Navigate to={dashboardPathForRole(user?.role) || '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      <Route
        path="/nurse/dashboard"
        element={
          <RoleProtectedRoute role="NURSE">
            <NurseDashboardPage />
          </RoleProtectedRoute>
        }
      />
      {/* Alerts tab / notification bell target — reuses the dashboard, same as the original nurse portal */}
      <Route
        path="/nurse/alerts"
        element={
          <RoleProtectedRoute role="NURSE">
            <NurseDashboardPage />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/nurse/patients"
        element={
          <RoleProtectedRoute role="NURSE">
            <NursePatientsPage />
          </RoleProtectedRoute>
        }
      />

      <Route
        path="/doctor"
        element={
          <RoleProtectedRoute role="DOCTOR">
            <DoctorMainPage />
          </RoleProtectedRoute>
        }
      />

      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<RootRedirect />} />
    </Routes>
  )
}
