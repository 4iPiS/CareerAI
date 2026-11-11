import React, { useEffect, useState, useCallback } from 'react'
import { getSessions, downloadResponsesCsv } from '../../api/services'
import { sessionStatusColor, sessionStatusLabel } from '../../utils/helpers'

const AdminResponses: React.FC = () => {
  const [sessions, setSessions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)

  const loadSessions = useCallback(async () => {
    try {
      const res = await getSessions(50)
      setSessions(res.data.sessions || [])
    } catch (e: any) {
      alert(e.response?.data?.detail || e.message || 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const handleExportCsv = async () => {
    setExporting(true)
    try {
      const res = await downloadResponsesCsv()
      const blob = new Blob([res.data], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'responses.csv'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e: any) {
      alert(e.response?.data?.detail || e.message || 'Ошибка экспорта')
    } finally {
      setExporting(false)
    }
  }

  if (loading) return <div className="text-center py-10">Загрузка...</div>

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button
          onClick={handleExportCsv}
          disabled={exporting}
          className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50"
        >
          {exporting ? 'Экспорт...' : 'Экспорт CSV'}
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">ID</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Статус</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Вопросов</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Источник</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Метки</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Оценка</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Рекомендации</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id} className="border-t">
                <td className="px-4 py-3 text-sm">{s.id}</td>
              <td className="py-2">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${sessionStatusColor(s.status)}`}>
                    {sessionStatusLabel(s.status)}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">{s.questions_asked}</td>
                <td className="px-4 py-3 text-sm">{s.source}</td>
                <td className="px-4 py-3 text-sm">{(s.chosen_fields || []).join(', ') || '—'}</td>
                <td className="px-4 py-3 text-sm">{s.feedback_score ?? '—'}</td>
                <td className="px-4 py-3 text-sm">{(s.recommendations || []).slice(0, 3).map((r: any) => r.field).join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default AdminResponses
