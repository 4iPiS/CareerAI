import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { adminLogout, getAdminMe } from '../../api/services'

const MENU_ITEMS = [
  { path: '/admin/dashboard', label: 'Дашборд' },
  { path: '/admin/directions', label: 'Направления' },
  { path: '/admin/features', label: 'Признаки' },
  { path: '/admin/questions', label: 'Вопросы' },
  { path: '/admin/custom', label: 'Анкета вуза' },
  { path: '/admin/media', label: 'Медиатека' },
  { path: '/admin/users', label: 'Пользователи' },
  { path: '/admin/responses', label: 'Ответы' },
  { path: '/admin/settings', label: 'Настройки' },
  { path: '/admin/recommendations', label: 'Рекомендации' },
]

const AdminLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [authReady, setAuthReady] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('admin_token')
    if (!token) {
      navigate('/admin', { replace: true })
      return
    }
    // Validate token via /me endpoint
    getAdminMe()
      .then(() => setAuthReady(true))
      .catch(() => {
        localStorage.removeItem('admin_token')
        navigate('/admin', { replace: true })
      })
  }, [navigate])

  const handleLogout = async () => {
    try { await adminLogout() } catch {}
    localStorage.removeItem('admin_token')
    navigate('/admin')
  }

  if (!authReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100">
        <div className="text-slate-600">Проверка доступа...</div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-slate-100">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`fixed lg:static inset-y-0 left-0 z-50 w-56 bg-slate-900 text-slate-300 flex flex-col transition-transform ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      }`}>
        <div className="p-4 border-b border-slate-700">
          <h1 className="text-white font-bold text-lg">CareerAI</h1>
          <p className="text-slate-400 text-xs">админ-панель</p>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {MENU_ITEMS.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <Link key={item.path} to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-indigo-500 text-white' : 'hover:bg-slate-800'
                }`}>
                {item.label}
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-slate-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h2 className="text-lg font-semibold text-slate-800">
              {MENU_ITEMS.find((i) => i.path === location.pathname)?.label || 'Панель'}
            </h2>
          </div>
          <button
            onClick={handleLogout}
            className="px-3 py-1.5 rounded-lg text-sm text-slate-600 hover:bg-slate-100 transition-colors"
          >
            Выйти
          </button>
        </header>

        {/* Content */}
        <main className="flex-1 p-4 md:p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}

export default AdminLayout
