import React, { useEffect, useState } from 'react'
import { getAdminSettings, updateAdminSettings } from '../../api/services'
import MediaPicker from './MediaPicker'

const AdminSettings: React.FC = () => {
  const [settings, setSettings] = useState({
    university_name: '',
    university_url: '',
    abitur_url: '',
    tagline: '',
    logo_path: '',
    hero_image_path: '',
    presenter_video_path: '',
    primary_color: '#667eea',
    primary_alpha: 1,
    consent_text: 'Я даю согласие на обработку персональных данных',
    custom_form_position: 'start',
    contact_email: '',
    support_phone: '',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  // Медиа-пикер: { field: 'logo_path' | 'hero_image_path' | 'presenter_video_path', kind: 'image' | 'video' }
  const [picker, setPicker] = useState<{ field: string; kind: string } | null>(null)

  useEffect(() => {
    getAdminSettings()
      .then((res) => setSettings({ ...settings, ...res.data.settings }))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    await updateAdminSettings(settings)
    setSaving(false)
    alert('Сохранено')
  }

  if (loading) return <div className="text-center py-10">Загрузка...</div>

  return (
    <div className="space-y-6">

      {/* Общие */}
      <div className="bg-white rounded-xl p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-500 mb-3">Общие настройки</h2>
        <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Название вуза</label>
          <input value={settings.university_name} onChange={(e) => setSettings({ ...settings, university_name: e.target.value })}
            className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">URL вуза</label>
          <input value={settings.university_url} onChange={(e) => setSettings({ ...settings, university_url: e.target.value })}
            className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">URL абитуриента</label>
          <input value={settings.abitur_url} onChange={(e) => setSettings({ ...settings, abitur_url: e.target.value })}
            className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Подзаголовок</label>
          <input value={settings.tagline} onChange={(e) => setSettings({ ...settings, tagline: e.target.value })}
            className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
        </div>
        </div>
      </div>

      {/* Визуал */}
      <div className="bg-white rounded-xl p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-500 mb-3">Визуальные элементы</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Основной цвет + прозрачность</label>
          <div className="flex items-center gap-2">
            <input type="color" value={settings.primary_color} onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })}
              className="w-12 h-10 rounded cursor-pointer" />
            <input type="range" min="0" max="1" step="0.1" value={settings.primary_alpha ?? 1}
              onChange={(e) => setSettings({ ...settings, primary_alpha: parseFloat(e.target.value) })}
              className="flex-1" />
            <span className="text-xs text-slate-500 w-8">{settings.primary_alpha ?? 1}</span>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Логотип</label>
          <div className="flex gap-2">
            <input value={settings.logo_path} readOnly
              placeholder="Выберите логотип из медиатеки"
              className="flex-1 p-2 border border-slate-200 rounded-lg outline-none bg-slate-50" />
            <button type="button" onClick={() => setPicker({ field: 'logo_path', kind: 'image' })}
              className="px-3 py-2 bg-slate-200 hover:bg-slate-300 rounded-lg text-sm font-medium">
              Выбрать
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-1">Отображается в правом верхнем углу анкеты.</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Фоновое изображение</label>
          <div className="flex gap-2">
            <input value={settings.hero_image_path} readOnly
              placeholder="Выберите фон из медиатеки"
              className="flex-1 p-2 border border-slate-200 rounded-lg outline-none bg-slate-50" />
            <button type="button" onClick={() => setPicker({ field: 'hero_image_path', kind: 'image' })}
              className="px-3 py-2 bg-slate-200 hover:bg-slate-300 rounded-lg text-sm font-medium">
              Выбрать
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-1">Фон стартового экрана и вопросов анкеты.</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Видео презентера</label>
          <div className="flex gap-2">
            <input value={settings.presenter_video_path} readOnly
              placeholder="Выберите видео из медиатеки"
              className="flex-1 p-2 border border-slate-200 rounded-lg outline-none bg-slate-50" />
            <button type="button" onClick={() => setPicker({ field: 'presenter_video_path', kind: 'video' })}
              className="px-3 py-2 bg-slate-200 hover:bg-slate-300 rounded-lg text-sm font-medium">
              Выбрать
            </button>
          </div>
        </div>
        </div>
      </div>

      {/* Анкета и контакты */}
      <div className="bg-white rounded-xl p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-500 mb-3">Анкета и контакты</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Позиция анкеты вуза</label>
          <select value={settings.custom_form_position} onChange={(e) => setSettings({ ...settings, custom_form_position: e.target.value })}
            className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500">
            <option value="start">В начале опроса</option>
            <option value="end">В конце опроса</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Контактный email</label>
          <input value={settings.contact_email} onChange={(e) => setSettings({ ...settings, contact_email: e.target.value })}
            className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Телефон поддержки</label>
          <input value={settings.support_phone} onChange={(e) => setSettings({ ...settings, support_phone: e.target.value })}
            className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-1">Текст согласия</label>
          <textarea value={settings.consent_text} onChange={(e) => setSettings({ ...settings, consent_text: e.target.value })}
            rows={2} className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
        </div>
        </div>
      </div>

      <button onClick={handleSave} disabled={saving}
        className="px-6 py-2.5 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50">
        {saving ? 'Сохранение...' : 'Сохранить настройки'}
      </button>

      {/* Модалка выбора файла из медиатеки */}
      {picker && (
        <MediaPicker
          kind={picker.kind}
          title={picker.kind === 'video' ? 'Выбор видео' : 'Выбор изображения'}
          onPick={(path) => setSettings((prev) => ({ ...prev, [picker.field]: path }))}
          onClose={() => setPicker(null)}
        />
      )}
    </div>
  )
}

export default AdminSettings
