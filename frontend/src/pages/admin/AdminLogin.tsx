import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { adminLogin } from '../../api/services'

const AdminLogin: React.FC = () => {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    const token = localStorage.getItem('admin_token')
    if (token) {
      navigate('/admin/dashboard', { replace: true })
    }
  }, [navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await adminLogin(username, password)
      localStorage.setItem('admin_token', res.data.token)
      navigate('/admin/dashboard')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Неверный логин или пароль')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="bg-white rounded-2xl p-8 w-full max-w-sm shadow-xl">
        <h1 className="text-indigo-600 text-2xl font-bold text-center mb-2">CareerAI</h1>
        <p className="text-slate-400 text-center mb-6">Вход в админ-панель</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
            placeholder="Логин" className="w-full p-3 border border-slate-200 rounded-xl outline-none focus:border-indigo-500" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            placeholder="Пароль" className="w-full p-3 border border-slate-200 rounded-xl outline-none focus:border-indigo-500" />
          {error && <div className="text-red-500 text-sm text-center">{error}</div>}
          <button type="submit" disabled={loading}
            className="w-full py-3 rounded-xl text-white font-semibold bg-indigo-500 hover:bg-indigo-600 transition-colors disabled:opacity-50">
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default AdminLogin
