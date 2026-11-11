import React, { useEffect, useState, useCallback, useRef } from 'react'
import {
    getAdminStats,
    getDatasetInfo,
    getTrainStatus,
    getTrainModels,
    generateDataset,
    startTraining,
    cancelTraining,
    exportDbToCsv,
    uploadRealCsv,
    getDatasetProgress,
    getRecommenderMetrics,
} from '../../api/services'
import { formatDate, formatNumber, trainStatusColor, trainStatusLabel } from '../../utils/helpers'
import { datasetLabel, esc } from '../../utils/adminHelpers'

interface StatCard {
    label: string
    value: number
}

const AdminDashboard: React.FC = () => {
    const [stats, setStats] = useState<any>(null)
    const [datasetInfo, setDatasetInfo] = useState<any>(null)
    const [runs, setRuns] = useState<any[]>([])
    const [models, setModels] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    const [datasetGenerating, setDatasetGenerating] = useState(false)
    const [datasetMsg, setDatasetMsg] = useState('')
    const [training, setTraining] = useState(false)
    const [trainError, setTrainError] = useState('')
    const [trainType, setTrainType] = useState('all')
    const [trainModelId, setTrainModelId] = useState<number | null>(null)
    const [uploading, setUploading] = useState(false)
    const [uploadMsg, setUploadMsg] = useState('')
    const [datasetProgress, setDatasetProgress] = useState<any>(null)
    const [uploadProgress, setUploadProgress] = useState(0)
    const [dismissedError, setDismissedError] = useState<number | null>(null)
    const [metricModalRun, setMetricModalRun] = useState<any>(null)
    const runsRef = useRef(runs)
    runsRef.current = runs
    const datasetGeneratingRef = useRef(false)
    useEffect(() => { datasetGeneratingRef.current = datasetGenerating }, [datasetGenerating])

    // Сбрасываем training при загрузке страницы — статус берётся из API
    useEffect(() => {
        setTraining(false)
    }, [])

    const fetchData = useCallback(async () => {
        setLoading(true)
        try {
            const [statsRes, dsRes, trainRes, modelsRes] = await Promise.allSettled([
                getAdminStats(),
                getDatasetInfo(),
                getTrainStatus(),
                getTrainModels(),
            ])

            if (statsRes.status === 'fulfilled') setStats(statsRes.value.data.stats)
            if (dsRes.status === 'fulfilled') setDatasetInfo(dsRes.value.data)
            if (trainRes.status === 'fulfilled') setRuns(trainRes.value.data.runs || [])
            if (modelsRes.status === 'fulfilled') setModels(modelsRes.value.data.models || [])
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchData()
    }, [fetchData])

    // Auto-refresh: опрашиваем статус каждые 3 секунды, пока открыта страница.
    // Поллинг всегда активен — раньше он останавливался до запуска обучения и
    // прогресс-бар навсегда «зависал» в оранжевой очереди до перезагрузки.
    useEffect(() => {
        let active = true
        let timer: ReturnType<typeof setTimeout> | null = null
        const poll = async () => {
            if (!active) return
            try {
                const [trainRes, modelsRes, dsProgRes] = await Promise.allSettled([
                    getTrainStatus(),
                    getTrainModels(),
                    getDatasetProgress(),
                ])
                if (!active) return
                if (trainRes.status === 'fulfilled') {
                    setRuns(trainRes.value.data.runs || [])
                }
                if (modelsRes.status === 'fulfilled') {
                    setModels(modelsRes.value.data.models || [])
                }
                if (dsProgRes.status === 'fulfilled' && dsProgRes.value.data && datasetGeneratingRef.current) {
                    setDatasetProgress(dsProgRes.value.data)
                }
            } catch {
                // Ошибка сети — повторим на следующем тике
            }
            if (active) timer = setTimeout(poll, 3000)
        }
        poll()
        return () => {
            active = false
            if (timer) clearTimeout(timer)
        }
    }, [])

    const statCards: StatCard[] = [
        { label: 'Всего сессий', value: stats?.total ?? 0 },
        { label: 'Завершено', value: stats?.completed ?? 0 },
        { label: 'В процессе', value: stats?.in_progress ?? 0 },
        { label: 'С профилем', value: stats?.with_profile ?? 0 },
        { label: 'С метками', value: stats?.labeled ?? 0 },
    ]

    const handleGenerateDataset = async () => {
        setDatasetGenerating(true)
        setDatasetMsg('')
        setDatasetProgress(null)
        try {
            const res = await generateDataset()
            setDatasetMsg(`Сгенерировано ${res.data.rows} строк`)
            await fetchData()
        } catch (e: any) {
            setDatasetMsg(e.response?.data?.detail || e.message || 'Ошибка генерации')
        } finally {
            // Генерация синхронная: по завершении запроса снимаем флаг
            setDatasetGenerating(false)
            setDatasetProgress(null)
        }
    }

    const handleStartTraining = async () => {
        setTraining(true)
        setTrainError('')
        try {
            // fine-tuning — это дообучение существующей модели на выбранных данных.
            // dataset передаём реальный тип выборки, model_id — базовая модель.
            const datasetForTrain = trainType === 'finetune' ? 'all' : trainType
            const payload: any = { dataset: datasetForTrain }
            if (trainType === 'finetune') {
                if (!trainModelId) {
                    alert('Выберите модель для дообучения')
                    setTraining(false)
                    return
                }
                payload.model_id = trainModelId
            }
            await startTraining(payload)
            setTrainError('')
            await fetchData()
        } catch (e: any) {
            setTrainError(e.response?.data?.detail || e.message || 'Ошибка запуска обучения')
        } finally {
            setTraining(false)
        }
    }

    const handleCancelTraining = async (runId: number) => {
        if (!confirm('Остановить обучение?')) return
        try {
            await cancelTraining(runId)
            await fetchData()
        } catch (e: any) {
            alert(e.response?.data?.detail || e.message || 'Ошибка остановки')
        }
    }

    const handleExportCsv = async () => {
        try {
            await exportDbToCsv()
            alert('Экспорт завершён — файл сохранён на сервере')
            await fetchData()
        } catch (e: any) {
            alert(e.response?.data?.detail || e.message || 'Ошибка экспорта')
        }
    }

    const handleUploadCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return
        setUploading(true)
        setUploadMsg('')
        setUploadProgress(0)
        try {
            const res = await uploadRealCsv(file, (ev) => {
                if (ev.lengthComputable)
                    setUploadProgress(Math.round((ev.loaded / ev.total) * 100))
            })
            setUploadMsg(res.data?.message || `Загружено: ${file.name}`)
            await fetchData()
        } catch (e: any) {
            setUploadMsg(e.response?.data?.detail || e.message || 'Ошибка загрузки')
        } finally {
            setUploading(false)
            setUploadProgress(0)
            e.target.value = ''
        }
    }

    if (loading) return <div className="text-center py-10">Загрузка дашборда…</div>

    const hasRunningRuns = runs.some((r) => r.status === 'running' || r.status === 'pending')

    return (
        <div className="space-y-6">
            {/* Stat cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                {statCards.map((card) => (
                    <div key={card.label} className="bg-white rounded-xl p-5 shadow-sm text-center">
                        <div className="text-2xl font-bold text-slate-800">{formatNumber(card.value)}</div>
                        <div className="text-sm text-slate-500 mt-1">{card.label}</div>
                    </div>
                ))}
            </div>

            {/* Dataset panel */}
            <div className="bg-white rounded-xl shadow-sm p-5">
                <h2 className="text-lg font-semibold text-slate-800 mb-3">Обучающая выборка</h2>

                <div className="flex gap-6 mb-3 text-sm">
                    <div>Признаков: <b>{datasetInfo?.active_features ?? '—'}</b></div>
                    <div>Направлений: <b>{datasetInfo?.active_directions ?? '—'}</b></div>
                </div>
                <div className="text-xs text-slate-500 mb-4">
                    При добавлении новых направлений или признаков в каталог — при следующей генерации выборки они автоматически включаются в обучение.
                </div>

                {runs.length > 0 ? (() => {
                    const lastRun = runs[0]
                    const m = lastRun.metrics || {}
                    const dsText = datasetLabel(lastRun.dataset, !!lastRun.model_id)
                    const isError = lastRun.status === 'error'
                    const isFailed = lastRun.status === 'failed'

                    return (
                        <div className={`mb-4 p-4 border rounded-lg ${
                            isError || isFailed
                                ? 'bg-red-50 border-red-300'
                                : lastRun.status === 'completed'
                                    ? 'bg-green-50 border-green-200'
                                    : 'bg-blue-50 border-blue-200'
                        }`}>
                            <div className={`font-semibold mb-1 ${
                                isError || isFailed ? 'text-red-800' :
                                    lastRun.status === 'completed' ? 'text-green-800' : 'text-blue-800'
                            }`}>
                                Последнее обучение #{esc(String(lastRun.id))}
                                <span className={`ml-2 inline-block px-2 py-0.5 rounded text-xs font-medium ${
                                    isError || isFailed ? 'bg-red-200 text-red-800' :
                                        lastRun.status === 'completed' ? 'bg-green-200 text-green-800' :
                                            'bg-blue-200 text-blue-800'
                                }`}>
                                    {trainStatusLabel(lastRun.status)}
                                </span>
                            </div>
                            <div className={`text-sm ${
                                isError || isFailed ? 'text-red-700' :
                                    lastRun.status === 'completed' ? 'text-green-700' : 'text-blue-700'
                            }`}>
                                Данные: <b>{esc(dsText)}</b> ·{' '}
                                Acc: <b>{m.accuracy != null ? Math.round(m.accuracy * 100) + '%' : '—'}</b> ·{' '}
                                F1: <b>{m.macro_f1 != null ? Math.round(m.macro_f1 * 100) + '%' : '—'}</b> ·{' '}
                                AUC: <b>{m.macro_auc != null ? Number(m.macro_auc).toFixed(3) : '—'}</b>
                            </div>
                            {/* Error message — prominently displayed */}
                            {lastRun.error_message && (
                                <div className="mt-3">
                                    <div className="flex items-start gap-2 bg-red-100 border border-red-300 rounded-lg p-3">
                                        <span className="text-red-600 text-lg flex-shrink-0">⚠️</span>
                                        <div className="flex-1">
                                            <div className="text-sm font-semibold text-red-800 mb-1">Ошибка обучения:</div>
                                            <div className="text-sm text-red-700 font-mono break-all bg-white rounded p-2 border border-red-200">
                                                {esc(lastRun.error_message)}
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => setDismissedError(lastRun.id)}
                                            className="text-red-400 hover:text-red-600 text-sm flex-shrink-0 ml-2"
                                            title="Скрыть">✕</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )
                })() : (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800">
                        Обучение ещё не проводилось
                    </div>
                )}

                {/* Dataset status */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                    <div>
                        <label className="block text-xs text-slate-500 mb-1">Синтетика (по каталогу)</label>
                        <div>
                            {datasetInfo?.synthetic?.exists ? (
                                datasetInfo.synthetic.rows != null ? (
                                    <span className="inline-block px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                                        готова ({formatNumber(datasetInfo.synthetic.rows)} строк)
                                    </span>
                                ) : (
                                    <span className="inline-block px-2 py-1 bg-green-100 text-green-800 text-xs rounded">готова</span>
                                )
                            ) : (
                                <span className="inline-block px-2 py-1 bg-red-100 text-red-800 text-xs rounded">не сгенерирована</span>
                            )}
                        </div>
                    </div>
                    <div>
                        <label className="block text-xs text-slate-500 mb-1">Реальные ответы (responses.csv)</label>
                        <div>
                            {datasetInfo?.real?.exists ? (
                                datasetInfo.real.rows != null ? (
                                    <span className="inline-block px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                                        {formatNumber(datasetInfo.real.rows)} строк
                                    </span>
                                ) : (
                                    <span className="inline-block px-2 py-1 bg-green-100 text-green-800 text-xs rounded">загружены</span>
                                )
                            ) : (
                                <span className="inline-block px-2 py-1 bg-red-100 text-red-800 text-xs rounded">нет</span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Dataset actions: две группы — синтетика и реальные ответы */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                    {/* Синтетическая выборка */}
                    <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                            Синтетическая выборка
                        </div>
                        <div className="flex flex-wrap gap-3">
                            <button
                                onClick={handleGenerateDataset}
                                disabled={datasetGenerating}
                                className="px-4 py-2 bg-indigo-500 text-white rounded-lg text-sm font-medium hover:bg-indigo-600 disabled:opacity-50 transition-colors"
                            >
                                {datasetGenerating ? 'Генерация…' : 'Сгенерировать'}
                            </button>
                            {datasetInfo?.synthetic?.exists && (
                                <a
                                    href="/api/admin/train/dataset/download"
                                    download
                                    className="px-4 py-2 bg-white text-indigo-600 border border-indigo-300 rounded-lg text-sm font-medium hover:bg-indigo-50 transition-colors"
                                >
                                    Скачать CSV
                                </a>
                            )}
                        </div>
                    </div>

                    {/* Реальные ответы */}
                    <div>
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                            Реальные ответы (responses.csv)
                        </div>
                        <div className="flex flex-wrap gap-3">
                            <label className="px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-600 transition-colors cursor-pointer">
                                Загрузить CSV
                                <input
                                    type="file"
                                    accept=".csv"
                                    hidden
                                    onChange={handleUploadCsv}
                                    disabled={uploading}
                                />
                            </label>
                            {datasetInfo?.real?.exists && (
                                <a
                                    href="/api/admin/train/dataset/download-real"
                                    download
                                    className="px-4 py-2 bg-white text-emerald-600 border border-emerald-300 rounded-lg text-sm font-medium hover:bg-emerald-50 transition-colors"
                                >
                                    Скачать ответы
                                </a>
                            )}
                            <button
                                onClick={handleExportCsv}
                                className="px-4 py-2 bg-white text-emerald-600 border border-emerald-300 rounded-lg text-sm font-medium hover:bg-emerald-50 transition-colors"
                            >
                                Экспортировать из БД
                            </button>
                        </div>
                    </div>
                </div>

                {datasetMsg && <div className="mt-2 text-sm text-slate-600">{datasetMsg}</div>}
                {uploadMsg && <div className="mt-2 text-sm text-slate-600">{uploadMsg}</div>}
                {datasetProgress && (
                    <div className="mt-3">
                        <div className="flex justify-between text-xs text-slate-600 mb-1">
                            <span>Генерация выборки</span>
                            <span>{Math.min(99, datasetProgress.progress ?? 0)}%</span>
                        </div>
                        <div className="w-full h-3 bg-slate-200 rounded-full overflow-hidden">
                            <div className="h-full bg-indigo-500 rounded-full transition-all duration-500" style={{ width: Math.max(Math.min(99, datasetProgress.progress ?? 0), 2) + '%' }}></div>
                        </div>
                        {datasetProgress.rows != null && datasetProgress.rows > 0 && (<div className="text-xs text-slate-500 mt-1">{datasetProgress.rows.toLocaleString('ru')} строк</div>)}
                    </div>
                )}
                {uploadProgress > 0 && uploadProgress < 100 && (
                    <div className="mt-3">
                        <div className="flex justify-between text-xs text-slate-600 mb-1">
                            <span>Загрузка CSV</span>
                            <span>{uploadProgress}%</span>
                        </div>
                        <div className="w-full h-3 bg-slate-200 rounded-full overflow-hidden">
                            <div className="h-full bg-indigo-500 rounded-full transition-all duration-300" style={{ width: uploadProgress + '%' }}></div>
                        </div>
                    </div>
                )}
            </div>


            {/* Training panel */}
            <div className="bg-white rounded-xl shadow-sm p-5">
                <h2 className="text-lg font-semibold text-slate-800 mb-3">Обучение модели</h2>

                <div className="flex flex-wrap gap-3 mb-4">
                    <button
                        onClick={handleStartTraining}
                        disabled={training || hasRunningRuns}
                        className="px-4 py-2 bg-indigo-500 text-white rounded-lg text-sm font-medium hover:bg-indigo-600 disabled:opacity-50 transition-colors"
                    >
                        {training ? 'Запуск…' : 'Запустить обучение'}
                    </button>
                    {hasRunningRuns && runs.find((r) => r.status === 'running') && (() => {
                        const run = runs.find((r) => r.status === 'running')
                        return (
                            <button
                                onClick={() => run && handleCancelTraining(run.id)}
                                className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600 transition-colors"
                            >
                                ⏹ Остановить
                            </button>
                        )
                    })()}
                </div>

                {/* Training type select */}
                <div className="mb-3">
                    <label className="block text-xs text-slate-500 mb-1">Обучение:</label>
                    <select
                        value={trainType}
                        onChange={(e) => setTrainType(e.target.value)}
                        className="w-full sm:w-auto p-2 border border-slate-200 rounded-lg text-sm outline-none focus:border-indigo-500"
                    >
                        <option value="synthetic">С нуля — только синтетика</option>
                        <option value="all">С нуля — синтетика + реальные</option>
                        <option value="real_only">С нуля — только реальные</option>
                        <option value="finetune">Fine-tuning — дообучение на реальных</option>
                    </select>
                </div>

                {/* Fine-tune model select */}
                {trainType === 'finetune' && (
                    <div className="mb-4">
                        <label className="block text-xs text-slate-500 mb-1">Модель для дообучения:</label>
                        <select
                            value={trainModelId || ''}
                            onChange={(e) => setTrainModelId(e.target.value ? Number(e.target.value) : null)}
                            className="w-full sm:w-auto p-2 border border-slate-200 rounded-lg text-sm outline-none focus:border-indigo-500"
                        >
                            <option value="">— Выберите модель —</option>
                            {models.map((m) => (
                                <option key={m.id} value={m.id}>
                                    #{m.id} — {m.metrics?.macro_f1 != null ? `F1: ${(m.metrics.macro_f1 * 100).toFixed(1)}%` : 'без метрик'}
                                </option>
                            ))}
                        </select>
                    </div>
                )}

                {trainError && <div className="text-sm text-red-600 mb-3">{trainError}</div>}
                {hasRunningRuns && (() => {
                    const run = runs.find((r) => r.status === 'running' || r.status === 'pending')
                    if (!run) return null
                    if (run.status === 'pending') {
                        return (
                            <div className="mt-3 mb-4">
                                <div className="flex justify-between text-xs text-slate-600 mb-1">
                                    <span>Очередь обучения (ожидает запуска)</span>
                                    <span>⏳</span>
                                </div>
                                <div className="w-full h-3 bg-slate-200 rounded-full overflow-hidden">
                                    <div className="h-full bg-amber-500 rounded-full animate-pulse"></div>
                                </div>
                            </div>
                        )
                    }
                    const totalEpochs = run.total_epochs || 80
                    const currentEpoch = run.current_epoch ?? 0
                    const pct = totalEpochs > 0 ? Math.round((currentEpoch / totalEpochs) * 100) : 0
                    return (
                        <div className="mt-3 mb-4">
                            <div className="flex justify-between text-xs text-slate-600 mb-1">
                                <span>Обучение: эпоха {currentEpoch}/{totalEpochs}</span>
                                <span>{pct}%</span>
                            </div>
                            <div className="w-full h-3 bg-slate-200 rounded-full overflow-hidden">
                                <div className="h-full bg-indigo-500 rounded-full transition-all duration-1000" style={{ width: Math.max(pct, 1) + '%' }}></div>
                            </div>
                        </div>
                    )
                })()}


                {/* Training runs table */}
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b text-left text-xs font-semibold text-slate-500 uppercase">
                                <th className="pb-2">ID</th>
                                <th className="pb-2">Статус</th>
                                <th className="pb-2">Данные</th>
                                <th className="pb-2">Top-1</th>
                                <th className="pb-2">Top-3</th>
                                <th className="pb-2">Top-5</th>
                                <th className="pb-2">Acc</th>
                                <th className="pb-2">F1</th>
                                <th className="pb-2">AUC</th>
                                <th className="pb-2">Эпохи</th>
                                <th className="pb-2">Дата</th>
                                <th className="pb-2">Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {runs.length === 0 ? (
                                <tr>
                                    <td colSpan={12} className="py-4 text-center text-slate-400">
                                        Нет запусков обучения
                                    </td>
                                </tr>
                            ) : (
                                runs.map((r) => {
                                    const m = r.metrics || {}
                                    const isError = r.status === 'error'
                                    const top1 = m.top1_accuracy != null ? Math.round(m.top1_accuracy * 100) : null
                                    const top3 = m.top3_accuracy != null ? Math.round(m.top3_accuracy * 100) : null
                                    const top5 = m.top5_accuracy != null ? Math.round(m.top5_accuracy * 100) : null
                                    return (
                                        <tr key={r.id} className="border-b">
                                            <td className="py-2 font-mono">{r.id}</td>
                                            <td className="py-2">
                                                <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${trainStatusColor(r.status)}`}>
                                                    {trainStatusLabel(r.status)}
                                                </span>
                                            </td>
                                            <td className="py-2 text-slate-600">{esc(datasetLabel(r.dataset, !!r.model_id))}</td>
                                            <td className="py-2 text-slate-600">{top1 != null ? top1 + '%' : '—'}</td>
                                            <td className="py-2 text-slate-600">{top3 != null ? top3 + '%' : '—'}</td>
                                            <td className="py-2 text-slate-600">{top5 != null ? top5 + '%' : '—'}</td>
                                            <td className="py-2 text-slate-600">
                                                {m.accuracy != null ? Math.round(m.accuracy * 100) + '%' : '—'}
                                            </td>
                                            <td className="py-2 text-slate-600">
                                                {m.macro_f1 != null ? Math.round(m.macro_f1 * 100) + '%' : '—'}
                                            </td>
                                            <td className="py-2 text-slate-600">
                                                {m.macro_auc != null ? Number(m.macro_auc).toFixed(3) : '—'}
                                            </td>
                                            <td className="py-2 text-slate-600">
                                                {r.total_epochs != null ? `${r.current_epoch ?? 0}/${r.total_epochs}` : '—'}
                                            </td>
                                            <td className="py-2 text-slate-600 text-xs">{formatDate(r.created_at)}</td>
                                            <td className="py-2">
                                                {/* Error message — shown inline */}
                                                {isError && r.error_message && (
                                                    <div className="mb-1">
                                                        <button
                                                            onClick={() => {
                                                                const msg = r.error_message || ''
                                                                alert('Ошибка обучения #' + r.id + ':\n' + msg)
                                                            }}
                                                            className="text-xs text-red-600 hover:text-red-800 font-medium underline"
                                                            title="Показать ошибку">
                                                            Показать ошибку
                                                        </button>
                                                    </div>
                                                )}
                                                {/* Cancel button */}
                                                {(r.status === 'running' || r.status === 'pending') && (
                                                    <button
                                                        onClick={() => handleCancelTraining(r.id)}
                                                        className="text-red-500 hover:text-red-700 text-xs font-medium"
                                                    >
                                                        Остановить
                                                    </button>
                                                )}
                                                {r.status === 'completed' && r.metrics?.per_direction && (
                                                    <button
                                                        onClick={() => setMetricModalRun(r)}
                                                        className="text-indigo-500 hover:text-indigo-700 text-xs font-medium ml-2"
                                                    >
                                        Метрики по классам
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    )
                                })
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Модальное окно: метрики по классам */}
                {metricModalRun && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
                        onClick={(e) => { if (e.target === e.currentTarget) setMetricModalRun(null) }}>
                        <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col m-4"
                            onClick={(e) => e.stopPropagation()}>
                            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
                                <h3 className="text-lg font-semibold text-slate-800">
                                    Метрики по классам — обучение #{metricModalRun.id}
                                </h3>
                                <button
                                    onClick={() => setMetricModalRun(null)}
                                    className="text-slate-400 hover:text-slate-600 text-2xl"
                                >
                                    ✕
                                </button>
                            </div>
                            <div className="p-6 overflow-y-auto">
                                <p className="text-sm text-slate-500 mb-4">
                                    Датасет: {esc(metricModalRun.dataset)} &nbsp;|&nbsp;
                                    Статус: {trainStatusLabel(metricModalRun.status)}
                                </p>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm border-collapse">
                                        <thead>
                                            <tr className="border-b text-left text-xs font-semibold text-slate-500">
                                                <th className="pb-3">Направление</th>
                                                <th className="pb-3 text-right">Поддержка</th>
                                                <th className="pb-3 text-right">Precision</th>
                                                <th className="pb-3 text-right">Recall</th>
                                                <th className="pb-3 text-right">F1</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {metricModalRun.metrics?.per_direction?.map((cls: any) => (
                                                <tr key={cls.label} className="border-b border-slate-100">
                                                    <td className="py-2 text-slate-700">{esc(cls.label)}</td>
                                                    <td className="py-2 text-right text-slate-600 font-mono">{cls.support ?? 0}</td>
                                                    <td className="py-2 text-right text-slate-600 font-mono">
                                                        {cls.precision != null ? (cls.precision * 100).toFixed(1) + '%' : '—'}
                                                    </td>
                                                    <td className="py-2 text-right text-slate-600 font-mono">
                                                        {cls.recall != null ? (cls.recall * 100).toFixed(1) + '%' : '—'}
                                                    </td>
                                                    <td className="py-2 text-right text-slate-600 font-mono">
                                                        {cls.f1 != null ? (cls.f1 * 100).toFixed(1) + '%' : '—'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                                {metricModalRun.metrics?.per_direction_by_f1 && (
                                    <div className="mt-6">
                                        <h4 className="text-sm font-semibold text-slate-700 mb-2">Топ направлений по F1</h4>
                                        <div className="space-y-1">
                                            {metricModalRun.metrics.per_direction_by_f1.slice(0, 5).map((d: any, i: number) => (
                                                <div key={i} className="flex justify-between text-sm text-slate-600">
                                                    <span>{i + 1}. {esc(d.field || d.label || '')}</span>
                                                    <span className="font-mono">{d.f1 != null ? (d.f1 * 100).toFixed(1) + '%' : '—'}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default AdminDashboard

