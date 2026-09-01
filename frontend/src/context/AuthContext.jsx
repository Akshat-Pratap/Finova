import React, { createContext, useContext, useState, useEffect } from 'react'
import { getMe, loginUser, registerUser, getOrganizations } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [activeOrg, setActiveOrg] = useState(null)
  const [organizations, setOrganizations] = useState([])
  const [loading, setLoading] = useState(true)
  const [role, setRole] = useState('OWNER')

  useEffect(() => {
    async function initAuth() {
      const token = localStorage.getItem('finova_token')
      const storedOrgId = localStorage.getItem('finova_org_id')
      if (token) {
        try {
          const res = await getMe()
          if (res.success && res.user) {
            setUser(res.user)
            const orgsRes = await getOrganizations()
            if (orgsRes.success && orgsRes.organizations?.length > 0) {
              setOrganizations(orgsRes.organizations)
              const current = orgsRes.organizations.find(o => o.organization_id === storedOrgId) || orgsRes.organizations[0]
              setActiveOrg(current)
              localStorage.setItem('finova_org_id', current.organization_id)
            }
          }
        } catch (err) {
          console.warn('Session restoration failed:', err.message)
          // Default to demo sandbox session if token invalid
          _initDemoSession()
        }
      } else {
        _initDemoSession()
      }
      setLoading(false)
    }

    function _initDemoSession() {
      const demoUser = {
        user_id: 'usr_demo_cfo',
        email: 'cfo@finova.ai',
        full_name: 'Chief Finance Officer',
      }
      const demoOrg = {
        organization_id: 'org_default',
        name: 'Finova Global Financials',
        base_currency: 'INR',
      }
      setUser(demoUser)
      setActiveOrg(demoOrg)
      setOrganizations([demoOrg])
      setRole('OWNER')
      localStorage.setItem('finova_org_id', 'org_default')
    }

    initAuth()
  }, [])

  const login = async (email, password) => {
    const res = await loginUser({ email, password })
    if (res.success) {
      localStorage.setItem('finova_token', res.access_token)
      setUser(res.user)
      setActiveOrg(res.organization)
      setRole(res.role || 'OWNER')
      localStorage.setItem('finova_org_id', res.organization.organization_id)
      const orgsRes = await getOrganizations().catch(() => ({ organizations: [res.organization] }))
      if (orgsRes?.organizations) setOrganizations(orgsRes.organizations)
      return res
    }
  }

  const register = async (email, password, full_name, org_name) => {
    const res = await registerUser({ email, password, full_name, organization_name: org_name })
    if (res.success) {
      localStorage.setItem('finova_token', res.access_token)
      setUser(res.user)
      setActiveOrg(res.organization)
      setRole('OWNER')
      localStorage.setItem('finova_org_id', res.organization.organization_id)
      setOrganizations([res.organization])
      return res
    }
  }

  const switchOrganization = (org) => {
    setActiveOrg(org)
    localStorage.setItem('finova_org_id', org.organization_id)
  }

  const logout = () => {
    localStorage.removeItem('finova_token')
    localStorage.removeItem('finova_org_id')
    setUser(null)
    setActiveOrg(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        activeOrg,
        organizations,
        role,
        loading,
        login,
        register,
        logout,
        switchOrganization,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
