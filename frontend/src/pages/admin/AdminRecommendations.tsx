import React, { useState, useEffect } from 'react'
import { getRecommenderSettings, updateRecommenderSettings, previewPrompt } from '../../api/services'

const PROVIDER_CONFIGS: Record<string, { url: string; model: string; key: string }> = {
  openai: { url: 'https://api.openai.com/v1', model: 'gpt-4o-mini', key: 'sk-' },
  sbercloud: { url: 'https://gigachat.devices.sbercloud.ru/api/v1', model: 'GigaChat', key: '' },
  deepseek: { url: 'https://api.deepseek.com/v1', model: 'deepseek-chat', key: 'sk-' },
  anthropic: { url: 'https://api.anthropic.com/v1', model: 'claude-3-5-sonnet-20241022', key: 'sk-ant-' },
  ollama: { url: 'http://host.docker.internal:11434/v1', model: 'llama3', key: '' },
  lmstudio: { url: 'http://host.docker.internal:1234/v1', model: 'qwen2.5-7b-instruct', key: '' },
  vllm: { url: 'http://host.docker.internal:8000/v1', model: 'Llama-3.1-8B-Instruct', key: '' },
  custom: { url: '', model: '', key: '' },
}

const AdminRecommendations: React.FC = () => {
  const [engine, setEngine] = useState<'local' | 'api'>('local')
  const [provider, setProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [promptPreview, setPromptPreview] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getRecommenderSettings()
      .then((res) => {
        const s = res.data.settings
        setEngine(s.engine || 'local')
        setProvider(s.api_provider || 'openai')
        setApiKey(s.api_key || '')
        setBaseUrl(s.api_base_url || PROVIDER_CONFIGS[s.api_provider]?.url || '')
        setModel(s.api_model || PROVIDER_CONFIGS[s.api_provider]?.model || '')
        setSystemPrompt(s.system_prompt || '')
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleProviderChange = (p: string) => {
    setProvider(p)
    const cfg = PROVIDER_CONFIGS[p]
    setBaseUrl(cfg.url)
    setModel(cfg.model)
  }

  const handleSave = async () => {
    setSaving(true)
    await updateRecommenderSettings({
      engine,
      api_provider: provider,
      api_key: apiKey,
      api_base_url: baseUrl,
      api_model: model,
      system_prompt: systemPrompt,
    })
    setSaving(false)
    alert('Сохранено')
  }

  const handlePreview = async () => {
    try {
      const res = await previewPrompt({})
      setPromptPreview(res.data.full_prompt || '(пусто)')
    } catch (e: any) {
      alert('Ошибка: ' + (e.response?.data?.detail || e.message))
    }
  }

  if (loading) return <div className="text-center py-10">Загрузка...</div>

  return (
    <div className="space-y-6 max-w-3xl">

      {/* Engine toggle */}
      <div className="flex rounded-xl overflow-hidden border border-slate-200">
        <button onClick={() => setEngine('local')}
          className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
            engine === 'local' ? 'bg-indigo-500 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}>
          Локальная модель (Keras)
        </button>
        <button onClick={() => setEngine('api')}
          className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
            engine === 'api' ? 'bg-indigo-500 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}>
          Внешний API
        </button>
      </div>

      {engine === 'api' && (
        <div className="bg-white rounded-xl p-5 shadow-sm space-y-4">
          <h2 className="font-semibold text-slate-800">Настройки API</h2>

          <div>
            <label className="block text-sm text-slate-500 mb-1">Провайдер</label>
            <select value={provider} onChange={(e) => handleProviderChange(e.target.value)}
              className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500">
              <option value="openai">OpenAI</option>
              <option value="sbercloud">СберCloud (GigaChat)</option>
              <option value="deepseek">DeepSeek</option>
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="ollama">Ollama (локальная)</option>
              <option value="lmstudio">LM Studio (локальная)</option>
              <option value="vllm">vLLM (локальная)</option>
              <option value="custom">Другой (кастомный URL)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-slate-500 mb-1">API ключ</label>
            <input value={apiKey} onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-... или ваш ключ" autoComplete="off"
              className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
          </div>

          <div>
            <label className="block text-sm text-slate-500 mb-1">Модель LLM</label>
            <input value={model} onChange={(e) => setModel(e.target.value)}
              placeholder="gpt-4o-mini (по умолчанию)"
              className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
          </div>

          <div>
            <label className="block text-sm text-slate-500 mb-1">Базовый URL</label>
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://api.example.com/v1"
              className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
          </div>

          <div>
            <label className="block text-sm text-slate-500 mb-1">Системный промпт</label>
            <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)}
              rows={8} className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500 font-mono text-sm resize-y" />
          </div>
        </div>
      )}

      {/* Preview */}
      <div>
        <button onClick={handlePreview}
          className="px-4 py-2 rounded-lg text-white text-sm font-semibold bg-indigo-500 hover:bg-indigo-600">
          Предпросмотр полного промпта
        </button>
        {promptPreview && (
          <textarea value={promptPreview} readOnly rows={15}
            className="w-full mt-3 p-3 font-mono text-xs bg-slate-50 border border-slate-200 rounded-lg resize-y" />
        )}
      </div>

      <button onClick={handleSave} disabled={saving}
        className="px-6 py-2.5 rounded-lg text-white font-semibold bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50">
        {saving ? 'Сохранение...' : 'Сохранить'}
      </button>
    </div>
  )
}

export default AdminRecommendations
