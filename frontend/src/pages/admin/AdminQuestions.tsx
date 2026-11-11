import React, { useEffect, useState } from 'react'
import { getAdminQuestions, createQuestion, updateQuestion, deleteQuestion, getAdminMedia } from '../../api/services'
import { useOptionsManager } from '../../utils/adminHelpers'

const AdminQuestions: React.FC = () => {
  const [questions, setQuestions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [editId, setEditId] = useState<number | null>(null)
  const [formData, setFormData] = useState({
    text: '', group_code: 'screening', feature_code: '', question_type: 'rating_1_5',
    threshold: 0, level: 0, sort_order: 0, is_active: true,
    examples: [] as string[], tags: [] as string[],
    exampleText: '', tagText: '',
    image_url: '', activation: '',
  })

  const { options, addOption, removeOption, updateOption, clearOptions, getOptions } = useOptionsManager([])
  const [_showPicker, setShowPicker] = useState(false)
  const [_mediaFiles, setMediaFiles] = useState<any[]>([])
  const [_pickerLoading, setPickerLoading] = useState(false)

  useEffect(() => {
    getAdminQuestions()
      .then((res) => setQuestions(res.data.questions))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    try {
      const { exampleText, tagText, activation, image_url, ...rest } = formData
      const isChoice = ['choice_single', 'choice_multi'].includes(formData.question_type)
      const options = isChoice ? getOptions() : null
      const activationValue = activation.trim() ? Number(activation) : null
      const activation_condition = activationValue != null
        ? { type: 'interest_ge', feature: formData.feature_code || '', value: activationValue }
        : null
      const apiData: any = {
        ...rest,
        image_url: image_url.trim() || null,
        options,
        activation_condition,
      }
      if (editId) {
        await updateQuestion(editId, apiData)
      } else {
        await createQuestion(apiData)
      }
      setEditId(null)
      setFormData({ text: '', group_code: 'screening', feature_code: '', question_type: 'rating_1_5', threshold: 0, level: 0, sort_order: 0, is_active: true, examples: [], tags: [], exampleText: '', tagText: '', image_url: '', activation: '' })
      getAdminQuestions().then((res) => setQuestions(res.data.questions))
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка сохранения')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить вопрос?')) return
    try {
      await deleteQuestion(id)
      setQuestions(questions.filter((q) => q.id !== id))
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка удаления')
    }
  }

  const startEdit = (q: any) => {
    setEditId(q.id)
    setFormData({
      text: q.text || '', group_code: q.group_code || 'screening', feature_code: q.feature_code || '',
      question_type: q.question_type || 'rating_1_5', threshold: q.threshold || 0,
      level: q.level || 0, sort_order: q.sort_order || 0, is_active: q.is_active ?? true,
      examples: q.examples || [], tags: q.tags || [], exampleText: '', tagText: '',
      image_url: q.image_url || '', activation: q.activation_condition ? (q.activation_condition.value || '') : '',
    })
    clearOptions()
    if (q.options) q.options.forEach((o: string) => addOption(o))
  }

  if (loading) return <div className="text-center py-10">Загрузка...</div>

  return (
    <div className="space-y-6">

      {/* Form */}
      <div className="bg-white rounded-xl p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">{editId ? 'Редактировать' : 'Новый вопрос'}</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Текст вопроса</label>
            <input value={formData.text} onChange={(e) => setFormData({ ...formData, text: e.target.value })}
              className="w-full p-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Группа</label>
            <select value={formData.group_code} onChange={(e) => setFormData({ ...formData, group_code: e.target.value })}
              className="w-full p-2 border rounded-lg">
            <option value="screening">Экран</option>
            <option value="detailed">Углублённый</option>
            <option value="personal">Личные качества</option>
            <option value="salary">Зарплата</option>
            <option value="ege_select">ЕГЭ выбор</option>
            <option value="ege">ЕГЭ баллы</option>
            <option value="custom">Анкета</option>
          </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Код признака</label>
            <input value={formData.feature_code} onChange={(e) => setFormData({ ...formData, feature_code: e.target.value })}
              className="w-full p-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Тип вопроса</label>
            <select value={formData.question_type} onChange={(e) => setFormData({ ...formData, question_type: e.target.value })}
              className="w-full p-2 border rounded-lg">
            <option value="rating_1_5">Рейтинг 1-5</option>
            <option value="choice_single">Одиночный выбор</option>
            <option value="choice_multi">Множественный выбор</option>
          </select>
          </div>
                    <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Картинка к вопросу</label>
            <div className="flex gap-2">
              <input value={formData.image_url} onChange={(e) => setFormData({ ...formData, image_url: e.target.value })} readOnly
                placeholder="image/xxx.jpg" className="flex-1 p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500 bg-slate-50" />
              <button type="button" onClick={async () => { setShowPicker(true); setPickerLoading(true); try { const res = await getAdminMedia(); setMediaFiles((res.data.files || []).filter((f:any) => f.kind === 'image')) } catch (e:any) { alert(e.response?.data?.detail || 'Ошибка') } finally { setPickerLoading(false) } }}
                className="px-3 py-2 bg-slate-200 hover:bg-slate-300 rounded-lg text-sm font-medium">Выбрать</button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Показывать если интерес к признаку ≥</label>
            <input type="number" step="0.1" value={formData.activation} onChange={(e) => setFormData({ ...formData, activation: e.target.value })}
              placeholder="напр. 3" className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
          </div>
<div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Порог</label>
            <input type="number" value={formData.threshold} onChange={(e) => setFormData({ ...formData, threshold: parseInt(e.target.value) || 0 })}
              className="w-full p-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Уровень</label>
            <input type="number" value={formData.level} onChange={(e) => setFormData({ ...formData, level: parseInt(e.target.value) || 0 })}
              className="w-full p-2 border rounded-lg" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Порядок сортировки</label>
            <input type="number" value={formData.sort_order} onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
              className="w-full p-2 border rounded-lg" />
          </div>
          {(formData.question_type === 'choice_single' || formData.question_type === 'choice_multi') && (
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Варианты ответов</label>
              {options.map((opt, i) => (
                <div key={i} className="flex gap-2 mb-2">
                  <input value={opt} onChange={(e) => updateOption(i, e.target.value)}
                    className="flex-1 p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                  <button type="button" onClick={() => removeOption(i)} className="px-2 text-red-500">×</button>
                </div>
              ))}
              <button type="button" onClick={() => addOption('')} className="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 rounded-lg text-sm">+ Добавить вариант</button>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Примеры ответов (Enter для добавления)</label>
            <input value={formData.exampleText} onChange={(e) => setFormData({ ...formData, exampleText: e.target.value })}
              className="w-full p-2 border rounded-lg"
              onKeyDown={(e) => { if (e.key === 'Enter' && formData.exampleText.trim()) { setFormData({ ...formData, examples: [...formData.examples, formData.exampleText.trim()], exampleText: '' }) } }} />
          <div className="flex flex-wrap gap-2">
            {(formData.examples || []).map((ex, i) => (
              <span key={i} className="px-2 py-1 bg-slate-100 rounded text-sm">{ex}
                <button type="button" onClick={() => setFormData({ ...formData, examples: formData.examples.filter((_, j) => j !== i) })} className="ml-1 text-red-500">×</button>
              </span>
            ))}
          </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Теги (Enter для добавления)</label>
            <input value={formData.tagText} onChange={(e) => setFormData({ ...formData, tagText: e.target.value })}
              className="w-full p-2 border rounded-lg"
              onKeyDown={(e) => { if (e.key === 'Enter' && formData.tagText.trim()) { setFormData({ ...formData, tags: [...formData.tags, formData.tagText.trim()], tagText: '' }) } }} />
          <div className="flex flex-wrap gap-2">
            {(formData.tags || []).map((t, i) => (
              <span key={i} className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-xs">{t}
                <button type="button" onClick={() => setFormData({ ...formData, tags: formData.tags.filter((_, j) => j !== i) })} className="ml-1 text-red-500">×</button>
              </span>
            ))}
          </div>
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <button onClick={handleSave} className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600">
            {editId ? 'Сохранить' : 'Создать'}
          </button>
          {editId && (
            <button onClick={() => { setEditId(null); setFormData({ text: '', group_code: 'screening', feature_code: '', question_type: 'rating_1_5', threshold: 0, level: 0, sort_order: 0, is_active: true, examples: [], tags: [], exampleText: '', tagText: '', image_url: '', activation: '' }); clearOptions() }}
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
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Группа</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Текст</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Тип</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Признак</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Примеры</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Теги</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Активен</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Действия</th>
            </tr>
          </thead>
          <tbody>
            {questions.map((q) => (
              <tr key={q.id} className="border-t">
                <td className="px-4 py-3 text-sm">{q.group_code}</td>
                <td className="px-4 py-3 text-sm">{q.text.slice(0, 50)}{q.text.length > 50 ? '...' : ''}</td>
                <td className="px-4 py-3 text-sm">{q.question_type}</td>
                <td className="px-4 py-3 text-sm">{q.feature_code || '—'}</td>
                <td className="px-4 py-3 text-sm">{(q.examples || []).join(', ') || '—'}</td>
                <td className="px-4 py-3 text-sm">{(q.tags || []).join(', ') || '—'}</td>
                <td className="px-4 py-3 text-sm">{q.is_active ? 'да' : 'нет'}</td>
                <td className="px-4 py-3 text-sm">
                  <button onClick={() => startEdit(q)} className="text-indigo-500 hover:text-indigo-700 mr-2">Ред.</button>
                  <button onClick={() => handleDelete(q.id)} className="text-red-500 hover:text-red-700">Удал.</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default AdminQuestions
