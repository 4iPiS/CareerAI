import React, { useEffect, useState } from 'react'
import { getAdminFeatures, createFeature, updateFeature, deleteFeature } from '../../api/services'

const AdminFeatures: React.FC = () => {
  const [features, setFeatures] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [editId, setEditId] = useState<number | null>(null)
  const [formData, setFormData] = useState({ label: '', code: '', data_type: 'numeric', is_common: true, sort_order: 0, is_active: true, description: '', examples: [] as string[] })

  useEffect(() => {
    getAdminFeatures()
      .then((res) => setFeatures(res.data.features))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    try {
      if (editId) {
        await updateFeature(editId, formData)
      } else {
        await createFeature(formData)
      }
      setEditId(null)
      setFormData({ label: '', code: '', data_type: 'numeric', is_common: true, sort_order: 0, is_active: true, description: '', examples: [] })
      getAdminFeatures().then((res) => setFeatures(res.data.features))
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка сохранения')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить признак?')) return
    try {
      await deleteFeature(id)
      setFeatures(features.filter((f) => f.id !== id))
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка удаления')
    }
  }

  const startEdit = (f: any) => {
    setEditId(f.id)
    setFormData({
      label: f.label || '',
      code: f.code || '',
      data_type: f.data_type || 'numeric',
      is_common: f.is_common ?? true,
      sort_order: f.sort_order || 0,
      is_active: f.is_active ?? true,
      description: f.description || '',
      examples: f.examples || [],
    })
  }

  if (loading) return <div className="text-center py-10">Загрузка...</div>

  return (
    <div className="space-y-6">

      {/* Form */}
      <div className="bg-white rounded-xl p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">{editId ? 'Редактировать' : 'Новый признак'}</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Название</label>
            <input value={formData.label} onChange={(e) => setFormData({ ...formData, label: e.target.value })}
              className="w-full p-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Код</label>
            <input value={formData.code} onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              className="w-full p-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Тип данных</label>
            <select value={formData.data_type} onChange={(e) => setFormData({ ...formData, data_type: e.target.value })}
              className="w-full p-2 border rounded-lg">
            <option value="numeric">Числовой</option>
            <option value="categorical">Категориальный</option>
            <option value="text">Текст</option>
          </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Порядок сортировки</label>
            <input type="number" value={formData.sort_order} onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
              className="w-full p-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Описание</label>
            <textarea value={formData.description || ''} onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full p-2 border rounded-lg" rows={2} />
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={formData.is_common}
                onChange={(e) => setFormData({ ...formData, is_common: e.target.checked })}
                className="" /> Общий признак
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="" /> Активен
            </label>
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <button onClick={handleSave} className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">
            {editId ? 'Сохранить' : 'Создать'}
          </button>
          {editId && (
            <button onClick={() => { setEditId(null); setFormData({ label: '', code: '', data_type: 'numeric', is_common: true, sort_order: 0, is_active: true, description: '', examples: [] }) }}
              className="px-4 py-2 bg-slate-200 rounded-lg hover:bg-slate-300">
              Отмена
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Код</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Название</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Тип</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Описание</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Примеры</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Общий</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Активен</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Действия</th>
            </tr>
          </thead>
          <tbody>
            {features.map((f) => (
              <tr key={f.id} className="border-t">
                <td className="px-4 py-3 text-sm">{f.code}</td>
                <td className="px-4 py-3 text-sm">{f.label}</td>
                <td className="px-4 py-3 text-sm">{f.data_type}</td>
                <td className="px-4 py-3 text-sm">{f.description || '—'}</td>
                <td className="px-4 py-3 text-sm">{(f.examples || []).join(', ') || '—'}</td>
                <td className="px-4 py-3 text-sm">{f.is_common ? 'да' : 'нет'}</td>
                <td className="px-4 py-3 text-sm">{f.is_active ? 'да' : 'нет'}</td>
                <td className="px-4 py-3 text-sm">
                  <button onClick={() => startEdit(f)} className="text-indigo-500 hover:text-indigo-700 mr-2">Ред.</button>
                  <button onClick={() => handleDelete(f.id)} className="text-red-500 hover:text-red-700">Удал.</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default AdminFeatures
