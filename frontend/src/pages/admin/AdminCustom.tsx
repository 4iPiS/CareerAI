import React, { useEffect, useState, useCallback } from 'react'
import {
  getCustomFields,
  createCustomField,
  updateCustomField,
  deleteCustomField,
} from '../../api/services'
import { esc, useOptionsManager } from '../../utils/adminHelpers'

const FIELD_TYPES = [
  { value: 'text', label: 'Текст' },
  { value: 'email', label: 'Email' },
  { value: 'phone', label: 'Телефон' },
  { value: 'select', label: 'Выбор' },
  { value: 'checkbox', label: 'Чекбокс' },
  { value: 'date', label: 'Дата' },
  { value: 'number', label: 'Число' },
]

interface CustomField {
  id?: number
  code: string
  label: string
  field_type: string
  options?: string[]
  required: boolean
  sort_order: number
  is_active: boolean
  description?: string
  examples?: string[]
}

const AdminCustom: React.FC = () => {
  const [fields, setFields] = useState<CustomField[]>([])
  const [loading, setLoading] = useState(true)
  const [editId, setEditId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  const [code, setCode] = useState('')
  const [label, setLabel] = useState('')
  const [fieldType, setFieldType] = useState('text')
  const [sortOrder, setSortOrder] = useState(0)
  const [required, setRequired] = useState(false)
  const [isActive, setIsActive] = useState(true)
  const [fieldDescription, setFieldDescription] = useState('')
  const [fieldExamples, setFieldExamples] = useState<string[]>([])
  const [exampleInput, setExampleInput] = useState('')

  const { options, addOption, removeOption, updateOption } =
    useOptionsManager([])

  const isChoice = ['select', 'checkbox'].includes(fieldType)

  const loadFields = useCallback(async () => {
    try {
      const res = await getCustomFields()
      setFields(res.data.fields || [])
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка загрузки полей')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadFields()
  }, [loadFields])

  const startEdit = useCallback(
    (f: CustomField) => {
      setEditId(f.id ?? null)
      setCode(f.code || '')
      setLabel(f.label || '')
      setFieldType(f.field_type || 'text')
      setSortOrder(f.sort_order ?? 0)
      setRequired(!!f.required)
      setIsActive(!!f.is_active)
      setFieldDescription(f.description || '')
      setFieldExamples(f.examples || [])
      setExampleInput('')

      if (isChoice) {
        // Reset options manager with existing options
        const initialOptions = f.options || []
        // We need to re-initialize options — use a timeout to let the hook settle
        setTimeout(() => {
          // Directly set via the form state
          ;(window as any).__customFieldOptions = initialOptions
        }, 0)
      }
    },
    [isChoice]
  )

  const handleSave = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault()
      if (!code.trim()) {
        alert('Введите код поля')
        return
      }

      setSaving(true)
      try {
        // Get current options from the DOM-managed state
        let fieldOptions: string[] | null = null
        if (isChoice) {
          // Read options from the hidden input or reconstruct
          fieldOptions = options.filter((o) => o.trim())
        }

        const payload = {
          code: code.trim(),
          label: label.trim(),
          field_type: fieldType,
          options: fieldOptions,
          required,
          sort_order: Number(sortOrder) || 0,
          is_active: isActive,
          description: fieldDescription.trim() || undefined,
          examples: fieldExamples.length ? fieldExamples : undefined,
        }

        if (editId) {
          await updateCustomField(editId, payload)
        } else {
          await createCustomField(payload)
        }

        setEditId(null)
        setCode('')
        setLabel('')
        setFieldType('text')
        setSortOrder(0)
        setRequired(false)
        setIsActive(true)
        setFieldDescription('')
        setFieldExamples([])
        setExampleInput('')
        await loadFields()
      } catch (e: any) {
        alert('Ошибка сохранения: ' + (e.response?.data?.detail || e.message))
      } finally {
        setSaving(false)
      }
    },
    [
      code,
      label,
      fieldType,
      sortOrder,
      required,
      isActive,
      editId,
      isChoice,
      options,
      loadFields,
    ]
  )

  const handleCancel = useCallback(() => {
    setEditId(null)
    setCode('')
    setLabel('')
    setFieldType('text')
    setSortOrder(0)
    setRequired(false)
    setIsActive(true)
    setFieldDescription('')
    setFieldExamples([])
    setExampleInput('')
  }, [])

  const handleDelete = useCallback(
    async (id: number) => {
      if (!confirm('Удалить поле?')) return
      try {
        await deleteCustomField(id)
        await loadFields()
      } catch (e: any) {
        alert('Ошибка удаления: ' + (e.response?.data?.detail || e.message))
      }
    },
    [loadFields]
  )

  const handleFieldTypeChange = useCallback(
    (value: string) => {
      setFieldType(value)
      if (!['select', 'checkbox'].includes(value)) {
        // Clear options when switching away from choice types
      }
    },
    []
  )

  if (loading) return <div className="text-center py-10">Загрузка...</div>

  return (
    <div className="space-y-6">

      <p className="text-sm text-slate-500">
        Анкета показывается абитуриенту по умолчанию сразу после кнопки «Начать опрос»
        (позицию можно сменить в «Настройках»). Ответы сохраняются по каждой сессии.
      </p>

      {/* Form */}
      <div className="bg-white rounded-xl p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4 text-slate-800">
          {editId !== null ? 'Редактирование' : 'Новое поле анкеты'}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              Код
            </label>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="email"
              className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              Подпись
            </label>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Email абитуриента"
              className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              Тип
            </label>
            <select
              value={fieldType}
              onChange={(e) => handleFieldTypeChange(e.target.value)}
              className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500"
            >
              {FIELD_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">
              Порядок
            </label>
            <input
              type="number"
              value={sortOrder}
              onChange={(e) => setSortOrder(Number(e.target.value) || 0)}
              className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Options for select/checkbox */}
        {isChoice && (
          <div className="mt-4 p-4 bg-slate-50 rounded-lg">
            <label className="block text-sm font-semibold text-slate-600 mb-2">
              Варианты
            </label>
            <div className="flex flex-col gap-2 max-h-48 overflow-y-auto mb-3">
              {options.map((opt, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    value={opt}
                    onChange={(e) => updateOption(index, e.target.value)}
                    placeholder={`Вариант ${index + 1}`}
                    className="flex-1 p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => removeOption(index)}
                    className="px-3 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 text-sm"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => addOption('')}
              className="px-4 py-2 bg-indigo-100 text-indigo-600 rounded-lg hover:bg-indigo-200 text-sm font-medium"
            >
              + Добавить вариант
            </button>
          </div>
        )}

        {/* Checkboxes */}
        <div className="flex gap-6 mt-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={required}
              onChange={(e) => setRequired(e.target.checked)}
              className="w-4 h-4 rounded text-indigo-500 focus:ring-indigo-500"
            />
            <span className="text-sm text-slate-700">Обязательное</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="w-4 h-4 rounded text-indigo-500 focus:ring-indigo-500"
            />
            <span className="text-sm text-slate-700">Активно</span>
          </label>
        </div>

        {/* Description */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-600 mb-1">Описание</label>
          <textarea value={fieldDescription} onChange={(e) => setFieldDescription(e.target.value)}
            placeholder="Краткое описание поля" className="w-full p-2 border rounded-lg" rows={2} />
        </div>

        {/* Examples */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-600 mb-1">Примеры значений</label>
          <input value={exampleInput} onChange={(e) => setExampleInput(e.target.value)}
            placeholder="Введите пример и нажмите Enter" className="w-full p-2 border rounded-lg"
            onKeyDown={(e) => { if (e.key === 'Enter' && exampleInput.trim()) { setFieldExamples([...fieldExamples, exampleInput.trim()]); setExampleInput('') } }} />
          <div className="flex flex-wrap gap-2 mt-2">
            {fieldExamples.map((ex, i) => (
              <span key={i} className="px-2 py-1 bg-slate-100 rounded text-sm">{ex}
                <button type="button" onClick={() => setFieldExamples(fieldExamples.filter((_, j) => j !== i))} className="ml-1 text-red-500">×</button>
              </span>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 mt-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2.5 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50 font-medium text-sm"
          >
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
          {editId !== null && (
            <button
              onClick={handleCancel}
              className="px-5 py-2.5 bg-slate-200 text-slate-700 rounded-lg hover:bg-slate-300 font-medium text-sm"
            >
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
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">
                Код
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">
                Подпись
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">
                Тип
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">
                Описание
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">
                Примеры
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">
                Обязат.
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">
                Активн.
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">
                Действия
              </th>
            </tr>
          </thead>
          <tbody>
            {fields.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-sm text-slate-400">
                  Полей пока нет
                </td>
              </tr>
            )}
            {fields.map((f) => (
              <tr key={f.id} className="border-t hover:bg-slate-50">
                <td className="px-4 py-3 text-sm font-mono text-slate-700">
                  {esc(f.code)}
                </td>
                <td className="px-4 py-3 text-sm text-slate-700">{esc(f.label)}</td>
                <td className="px-4 py-3 text-sm">
                  <span className="px-2 py-0.5 bg-slate-100 rounded text-xs font-medium text-slate-600">
                    {esc(f.field_type)}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">{esc(f.description || '—')}</td>
                <td className="px-4 py-3 text-sm">{(f.examples || []).join(', ') || '—'}</td>
                <td className="px-4 py-3 text-sm">{f.required ? 'да' : 'нет'}</td>
                <td className="px-4 py-3 text-sm">{f.is_active ? 'да' : 'нет'}</td>
                <td className="px-4 py-3 text-sm">
                  <button
                    onClick={() => startEdit(f)}
                    className="text-indigo-500 hover:text-indigo-700 mr-3 font-medium text-sm"
                  >
                    Ред.
                  </button>
                  <button
                    onClick={() => handleDelete(f.id!)}
                    className="text-red-500 hover:text-red-700 font-medium text-sm"
                  >
                    Удал.
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default AdminCustom
