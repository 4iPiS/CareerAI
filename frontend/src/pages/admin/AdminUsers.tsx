import React, { useEffect, useState, useCallback } from 'react'
import { getAdminUsers, createUser, updateUser, deleteUser } from '../../api/services'

interface AdminUser {
  id: number
  username: string
  role: string
  is_active: boolean
  created_at?: string
}

const AdminUsers: React.FC = () => {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [editId, setEditId] = useState<number | null>(null)
  const [newUser, setNewUser] = useState({ username: '', password: '' })
  const [editUser, setEditUser] = useState({ is_active: true, current_password: '', new_password: '', confirm_password: '' })
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  const [deletePassword, setDeletePassword] = useState('')

  const loadUsers = useCallback(async () => {
    try {
      const res = await getAdminUsers()
      setUsers(res.data.users || [])
    } catch (e: any) {
      alert(e.response?.data?.detail || e.message || 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const handleCreate = async () => {
    if (!newUser.username || !newUser.password) {
      alert('Введите логин и пароль')
      return
    }
    try {
      await createUser(newUser)
      setNewUser({ username: '', password: '' })
      loadUsers()
    } catch (e: any) {
      alert(e.response?.data?.detail || e.message || 'Ошибка создания')
    }
  }

  const handleUpdate = async () => {
    if (!editId) return
    try {
      const payload: any = { is_active: editUser.is_active }
      if (editUser.new_password) {
        if (editUser.new_password !== editUser.confirm_password) {
          alert('Пароли не совпадают')
          return
        }
        payload.password = editUser.new_password
        payload.current_password = editUser.current_password
      }
      await updateUser(editId, payload)
      setEditId(null)
      setEditUser({ is_active: true, current_password: '', new_password: '', confirm_password: '' })
      loadUsers()
    } catch (e: any) {
      alert(e.response?.data?.detail || e.message || 'Ошибка обновления')
    }
  }

  const confirmDelete = (id: number) => {
    setDeleteConfirmId(id)
    setDeletePassword('')
  }

  const handleDelete = async () => {
    if (!deleteConfirmId) return
    if (!deletePassword) {
      alert('Введите пароль администратора')
      return
    }
    try {
      await deleteUser(deleteConfirmId, deletePassword)
      setDeleteConfirmId(null)
      setDeletePassword('')
      loadUsers()
    } catch (e: any) {
      alert(e.response?.data?.detail || e.message || 'Ошибка удаления')
    }
  }

  if (loading) return <div className="text-center py-10">Загрузка...</div>

  return (
    <div className="space-y-6">
      {/* Create */}
      <div className="bg-white rounded-xl p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">Новый пользователь</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Логин</label>
            <input value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              className="w-full p-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Пароль</label>
            <input type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
              className="w-full p-2 border rounded-lg" />
          </div>
        </div>
        <button onClick={handleCreate} className="mt-4 px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">
          Создать
        </button>
      </div>

      {/* Edit */}
      {editId && (
        <div className="bg-white rounded-xl p-5 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">Редактирование</h2>
          <div className="space-y-3">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={editUser.is_active} onChange={(e) => setEditUser({ ...editUser, is_active: e.target.checked })}
                className="w-4 h-4" />
              Активен
            </label>
            <input type="password" value={editUser.current_password} onChange={(e) => setEditUser({ ...editUser, current_password: e.target.value })}
              placeholder="Текущий пароль (для смены пароля)" className="w-full p-2 border rounded-lg" />
            <input type="password" value={editUser.new_password} onChange={(e) => setEditUser({ ...editUser, new_password: e.target.value })}
              placeholder="Новый пароль" className="w-full p-2 border rounded-lg" />
            <input type="password" value={editUser.confirm_password} onChange={(e) => setEditUser({ ...editUser, confirm_password: e.target.value })}
              placeholder="Повторите новый пароль" className="w-full p-2 border rounded-lg" />
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={handleUpdate} className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">
              Сохранить
            </button>
            <button onClick={() => setEditId(null)} className="px-4 py-2 bg-slate-200 rounded-lg hover:bg-slate-300">
              Отмена
            </button>
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      {deleteConfirmId !== null && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-xl">
            <h3 className="text-lg font-semibold text-slate-800 mb-3">Подтверждение удаления</h3>
            <p className="text-sm text-slate-600 mb-4">
              Введите пароль администратора для удаления пользователя «{users.find((u) => u.id === deleteConfirmId)?.username}».
            </p>
            <input
              type="password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              placeholder="Пароль администратора"
              className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500 mb-4"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="px-4 py-2 bg-slate-200 rounded-lg hover:bg-slate-300 text-sm"
              >
                Отмена
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm"
              >
                Удалить
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">ID</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Логин</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Роль</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Создан</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Активен</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Действия</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="px-4 py-3 text-sm font-mono">{u.id}</td>
                <td className="px-4 py-3 text-sm">{u.username}</td>
                <td className="px-4 py-3 text-sm text-slate-600">{u.role || '—'}</td>
                <td className="px-4 py-3 text-sm text-slate-500">{u.created_at ? new Date(u.created_at).toLocaleDateString('ru-RU') : '—'}</td>
                <td className="px-4 py-3 text-sm">{u.is_active ? 'да' : 'нет'}</td>
                <td className="px-4 py-3 text-sm">
                  <button onClick={() => setEditId(u.id)} className="text-indigo-500 hover:text-indigo-700 mr-2">Ред.</button>
                  <button onClick={() => confirmDelete(u.id)} className="text-red-500 hover:text-red-700">Удал.</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default AdminUsers
