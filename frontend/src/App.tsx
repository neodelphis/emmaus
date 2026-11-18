import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth'
import { ToastProvider } from './toast'
import { ProtectedRoute } from './components/ProtectedRoute'
import { RequireSuperAdmin } from './components/RequireSuperAdmin'
import { AdminLayout } from './components/admin/AdminLayout'
import { AdminLoginPage } from './pages/AdminLoginPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { VolunteerPage } from './pages/VolunteerPage'
import { AdminWeekPage } from './pages/AdminWeekPage'
import { AdminVolunteersPage } from './pages/AdminVolunteersPage'
import { AdminHoursPage } from './pages/AdminHoursPage'
import { AdminAccountPage } from './pages/AdminAccountPage'
import { NotFoundPage } from './pages/NotFoundPage'

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to="/admin/semaine" replace />} />
            <Route path="/b" element={<VolunteerPage />} />
            <Route path="/admin/connexion" element={<AdminLoginPage />} />
            <Route path="/admin/mot-de-passe-oublie" element={<ForgotPasswordPage />} />
            <Route path="/admin/reinitialiser" element={<ResetPasswordPage />} />
            <Route path="/admin" element={<ProtectedRoute />}>
              <Route element={<AdminLayout />}>
                <Route index element={<Navigate to="semaine" replace />} />
                <Route path="semaine" element={<AdminWeekPage />} />
                <Route path="benevoles" element={<AdminVolunteersPage />} />
                <Route
                  path="horaires"
                  element={
                    <RequireSuperAdmin>
                      <AdminHoursPage />
                    </RequireSuperAdmin>
                  }
                />
                <Route path="compte" element={<AdminAccountPage />} />
              </Route>
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ToastProvider>
  )
}
