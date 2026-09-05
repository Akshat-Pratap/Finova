import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Datasets from './pages/Datasets'
import Reconciliation from './pages/Reconciliation'
import Transactions from './pages/Transactions'
import Exceptions from './pages/Exceptions'
import Integrations from './pages/Integrations'
import Reports from './pages/Reports'
import Forecast from './pages/Forecast'
import AuditLog from './pages/AuditLog'
import Settings from './pages/Settings'

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="datasets" element={<Datasets />} />
            <Route path="reconciliation" element={<Reconciliation />} />
            <Route path="transactions" element={<Transactions />} />
            <Route path="exceptions" element={<Exceptions />} />
            <Route path="integrations" element={<Integrations />} />
            <Route path="reports" element={<Reports />} />
            <Route path="forecast" element={<Forecast />} />
            <Route path="audit" element={<AuditLog />} />
            <Route path="settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  )
}
