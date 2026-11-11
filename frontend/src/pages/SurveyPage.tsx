import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSurvey } from '../contexts/SurveyContext'
import { submitAnswer, submitSurveyData, getSettings } from '../api/services'
import type { SurveyProgress, Settings } from '../api/types'
import {
    saveProgress,
    clearProgress,
    mediaUrl,
    getStageName,
    getProgressPercent,
    escapeHtml,
    isValidEmail,
    isValidPhone,
    shade,
} from '../utils/helpers'

const RATING_LABELS = ['Очень низкий', 'Низкий', 'Средний', 'Высокий', 'Очень высокий']

const SurveyPage: React.FC = () => {
    const navigate = useNavigate()
    const { sessionId, progress, currentQuestion, setProgress, setCurrentQuestion, showResults } = useSurvey()
    const [rating, setRating] = useState<number | null>(null)
    const [egeValues, setEgeValues] = useState<Record<string, string>>({})
    const [customFirst, setCustomFirst] = useState(false)
    const [egeSelectValues, setEgeSelectValues] = useState<string[]>([])
    const [customData, setCustomData] = useState<Record<string, any>>({})
    const [consent, setConsent] = useState(false)
    const [loading, setLoading] = useState(false)
    // Отдельный флаг отправки ответа: при нём опрос НЕ заменяется заглушкой,
    // а накрывается оверлеем «Формируем рекомендации…»
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState('')
    const [salary, setSalary] = useState(100000)
    const [heroImage, setHeroImage] = useState('')
    const [settings, setSettings] = useState<Settings>({})

    // Загрузка начального вопроса
    useEffect(() => {
        if (!sessionId) {
            setLoading(true)
            fetch('/api/v1/start', { method: 'POST' })
                .then((res) => {
                    if (!res.ok) throw new Error('API error')
                    return res.json()
                })
                .then((data: SurveyProgress) => {
                    // Извлекаем progress из question.progress (API возвращает его внутри question)
                    const progressData = data.progress || (data.question as any)?.progress
                    setProgress({ ...data, progress: progressData })
                    if (data.question) setCurrentQuestion(data.question)
                    saveProgress(progressData)
                })
                .catch(() => navigate('/'))
                .finally(() => setLoading(false))
        }
    }, [sessionId, setProgress, setCurrentQuestion, navigate])

    // Загрузка настроек (логотип, фон, primary color)
    useEffect(() => {
        getSettings()
            .then((res) => {
                const s = res.data.settings
                setSettings(s)
                setCustomFirst(s.custom_form_position !== 'end')

                if (s.hero_image_path) {
                    const imgUrl = mediaUrl(s.hero_image_path)
                    if (imgUrl) {
                        setHeroImage(imgUrl)
                        document.documentElement.style.setProperty('--hero-image', `url('${imgUrl}')`)
                    }
                }

                if (s.primary_color) {
                    let c = s.primary_color.startsWith('#') ? s.primary_color : '#' + s.primary_color
                    let hex = c.replace('#', '')
                    let alpha = s.primary_alpha ?? 1
                    if (hex.length === 8) {
                        alpha = parseInt(hex.slice(6, 8), 16) / 255
                        hex = hex.slice(0, 6)
                    }
                    c = '#' + hex
                    const d = shade(c)
                    const num = parseInt(hex, 16)
                    const r = (num >> 16) & 255
                    const g = (num >> 8) & 255
                    const b = num & 255
                    const dr = Math.round(r * 0.7)
                    const dg = Math.round(g * 0.6)
                    const db = Math.round(b * 0.9)
                    const root = document.documentElement.style
                    root.setProperty('--primary', c)
                    root.setProperty('--primary-dark', d)
                    root.setProperty('--primary-soft', `rgba(${r}, ${g}, ${b}, ${alpha * 0.35})`)
                    root.setProperty('--primary-dark-soft', `rgba(${dr}, ${dg}, ${db}, ${alpha * 0.25})`)
                    root.setProperty('--primary-bg', `rgba(${r}, ${g}, ${b}, ${alpha * 0.95})`)
                    // Сохраняем rgba-варианты с альфой для градиентов и подсветки
                    root.setProperty('--primary-rgba', `rgba(${r}, ${g}, ${b}, ${alpha})`)
                    root.setProperty('--primary-dark-rgba', `rgba(${dr}, ${dg}, ${db}, ${alpha})`)
                }
            })
            .catch(() => {})
    }, [])

    // Обновление фона вопроса при изменении currentQuestion
    useEffect(() => {
        if (currentQuestion?.image_url) {
            const imgUrl = mediaUrl(currentQuestion.image_url)
            if (imgUrl) {
                setHeroImage(imgUrl)
                document.documentElement.style.setProperty('--hero-image', `url('${imgUrl}')`)
            } else {
                setHeroImage('')
                document.documentElement.style.removeProperty('--hero-image')
            }
        }
    }, [currentQuestion])

    const handleSubmit = async () => {
        if (!sessionId || !currentQuestion) return
        setError('')

        // --- Custom form (university questionnaire) ---
        if (currentQuestion.is_custom) {
            setSubmitting(true)
            const fields = currentQuestion.fields || []
            const data: Record<string, any> = {}
            let hasError = false
            for (const f of fields) {
                const el = customData[f.code]
                const val = f.field_type === 'checkbox' ? el : (el || '').trim()
                if (f.required && !val) {
                    setError('Заполните обязательные поля')
                    hasError = true
                    break
                }
                if (val) {
                    if (f.field_type === 'email' && !isValidEmail(val)) {
                        setError('Укажите корректный email')
                        hasError = true
                        break
                    }
                    if (f.field_type === 'phone' && !isValidPhone(val)) {
                        setError('Укажите корректный телефон')
                        hasError = true
                        break
                    }
                }
                data[f.code] = val
            }
            if (!consent) {
                setError('Необходимо согласие на обработку персональных данных')
                hasError = true
            }
            if (hasError) {
                setSubmitting(false)
                return
            }

            try {
                const res = await submitSurveyData(sessionId, data, consent)
                const resp = res.data
                if (resp.done) {
                    clearProgress()
                    showResults(resp.recommendations)
                    // Сохраняем рекомендации в localStorage для перезагрузки
                    if (sessionId) localStorage.setItem('sessionId', sessionId)
                    if (resp.recommendations) localStorage.setItem('recommendations', JSON.stringify(resp.recommendations))
                    navigate('/results')
                } else if (resp.question) {
                    const progressData = resp.progress || (resp.question as any)?.progress
                    setProgress({ ...resp, progress: progressData })
                    setCurrentQuestion(resp.question)
                    saveProgress(progressData)
                    setRating(null)
                    setEgeValues({})
                    setEgeSelectValues([])
                    setCustomData({})
                    setConsent(false)
                    setError('')
                }
            } catch (e: any) {
                setError(e.response?.data?.detail || 'Ошибка отправки')
            } finally {
                setSubmitting(false)
            }
            return
        }

        // --- Regular questions ---
        let answer: any = null
        let questionId: number | string = currentQuestion.id

        if (currentQuestion.is_salary) {
            answer = salary
        } else if (currentQuestion.is_ege_select) {
            if (egeSelectValues.length === 0) {
                setError('Выберите хотя бы один предмет')
                return
            }
            answer = egeSelectValues
        } else if (currentQuestion.is_ege) {
            const subjects = currentQuestion.subjects || []
            const values: Record<string, number> = {}
            let hasError = false
            if (hasError) {
                return
            }
            answer = values
        } else {
            if (!rating) {
                setError('Выберите значение')
                return
            }
            answer = rating
        }

        setSubmitting(true)
        try {
            const res = await submitAnswer(sessionId, questionId, answer)
            const resp = res.data
            if (resp.done) {
                clearProgress()
                showResults(resp.recommendations)
                navigate('/results')
            } else if (resp.question) {
                const progressData = resp.progress || (resp.question as any)?.progress
                setProgress({ ...resp, progress: progressData })
                setCurrentQuestion(resp.question)
                saveProgress(progressData)
                setRating(null)
                setEgeValues({})
                setEgeSelectValues([])
                setCustomData({})
                setConsent(false)
                setError('')
            }
        } catch (e: any) {
            setError(e.response?.data?.detail || 'Ошибка отправки')
        } finally {
            setSubmitting(false)
        }
    }

    const isRatingAnswer = currentQuestion && !currentQuestion.is_custom && !currentQuestion.is_salary && !currentQuestion.is_ege_select && !currentQuestion.is_ege

    if (loading || !currentQuestion || !settings.university_name) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-900">
                <div className="text-white text-xl">
                    {loading ? 'Загрузка…' : 'Подготовка опроса…'}
                </div>
            </div>
        )
    }

    const logoPath = settings.logo_path || ''
    const uniName = escapeHtml(settings.university_name) || 'CareerAI'

    const bgGradient = `linear-gradient(160deg, var(--primary-rgba, ${settings.primary_color || '#667eea'}) 0%, var(--primary-dark-rgba, ${shade(settings.primary_color || '#667eea')}) 50%, var(--primary-rgba, ${settings.primary_color || '#667eea'}) 100%)`

    return (
        <div className="min-h-screen relative"
            style={{
                // Фон: градиент из настроек с учётом прозрачности, поверх — картинка (если задана)
                backgroundImage: heroImage ? `url('${heroImage}'), ${bgGradient}` : bgGradient,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                backgroundRepeat: 'no-repeat',
                backgroundAttachment: 'fixed',
                ...(heroImage ? { backgroundBlendMode: 'overlay' } : {}),
            }}>
            {/* Цветной полупрозрачный оверлей — цвет из настроек с альфой */}
            <div className="absolute inset-0 pointer-events-none"
                style={{
                    background: `linear-gradient(to bottom right, var(--primary-soft, rgba(102,126,234,0.10)), var(--primary-bg, rgba(102,126,234,0.08)), var(--primary-soft, rgba(102,126,234,0.10)))`,
                }} />

            {/* Полноэкранный оверлей ожидания рекомендаций: финальный шаг
                (ЕГЭ / анкета) может занимать несколько секунд — модель и
                LLM-объяснения. Без него слайд выглядит «зависшим». */}
            {submitting && currentQuestion && (currentQuestion.is_ege || (currentQuestion.is_custom && !customFirst)) && (
                <div className="fixed inset-0 z-50 flex items-center justify-center"
                    style={{ background: 'rgba(15,23,42,0.72)', backdropFilter: 'blur(4px)' }}>
                    <div className="bg-slate-800/95 rounded-2xl px-10 py-8 shadow-2xl border border-white/10 text-center max-w-sm mx-4">
                        <div className="flex justify-center mb-5">
                            <div className="w-14 h-14 rounded-full border-4 border-indigo-500/30 border-t-indigo-400 animate-spin" />
                        </div>
                        <div className="text-white text-lg font-semibold">Формируем рекомендации…</div>
                        <div className="text-slate-400 text-sm mt-2">
                            Анализируем ваши ответы — это займёт несколько секунд
                        </div>
                    </div>
                </div>
            )}

            {/* Logo — full aspect ratio, no clipping */}
            {logoPath && (
                <div className="absolute top-4 right-4 w-20 h-20">
                    <div className="w-full h-full rounded-full bg-white shadow-xl border-2 flex items-center justify-center overflow-hidden"
                        style={{ borderColor: 'var(--primary-soft, rgba(102,126,234,0.35))' }}>
                        <img src={`/media/${logoPath}`} alt="Logo" className="w-[110%] h-[110%] object-contain" />
                    </div>
                </div>
            )}

            {/* Badge */}
            <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur-md border border-white/15 rounded-full px-5 py-2 text-slate-200 text-sm font-semibold">
                {uniName}
            </div>

            {/* Bottom panel */}
            <div className="fixed bottom-0 left-0 right-0 z-10 max-h-[86vh] overflow-y-auto bg-slate-900/75 backdrop-blur-xl rounded-t-3xl p-5 pb-8"
                style={{ borderTop: '2px solid var(--primary, #667eea)' }}>
                {/* Progress */}
                <div className="mb-4">
                    <div className="flex justify-between text-slate-300 text-xs mb-2">
                        <span>{getStageName(progress?.progress?.stage)}</span>
                        <span>{progress?.progress?.current || 0}/{progress?.progress?.total || 0}</span>
                    </div>
                    <div className="h-1.5 bg-white/12 rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-700"
                            style={{
                                width: `${getProgressPercent(progress)}%`,
                                background: 'linear-gradient(90deg, var(--primary, #667eea), var(--primary-dark, #764ba2))',
                            }} />
                    </div>
                </div>

                {/* Question */}
                <h2 className="text-white text-xl font-semibold text-center mb-5 drop-shadow"
                    style={{ textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)' }}>
                    {escapeHtml(currentQuestion.text)}
                </h2>

                {/* Error */}
                {error && <div className="text-red-400 text-center mb-3">{error}</div>}

                {/* Rating scale */}
                {isRatingAnswer && (
                    <>
                        <div className="flex gap-3 mb-5 justify-center">
                            {[1, 2, 3, 4, 5].map((v) => (
                                <button key={v}
                                    onClick={() => setRating(v)}
                                    className={`flex-1 min-w-[50px] rounded-2xl py-3 text-center transition-all cursor-pointer border ${rating === v
                                        ? 'border-transparent scale-105'
                                        : 'bg-white/10 border-white/20 hover:bg-white/20'
                                        }`}
                                    style={rating === v ? {
                                        background: 'linear-gradient(135deg, var(--primary, #667eea), var(--primary-dark, #764ba2))',
                                    } : undefined}>
                                    <div className="text-white text-xl font-bold">{v}</div>
                                    <div className="text-slate-300 text-[10px]">{RATING_LABELS[v - 1]}</div>
                                </button>
                            ))}
                        </div>
                    </>
                )}

                {/* Salary */}
                {currentQuestion.is_salary && (
                    <div className="mb-5">
                        <input type="number" value={salary} onChange={(e) => setSalary(parseInt(e.target.value) || 0)}
                            placeholder="100000"
                            className="w-full p-3 rounded-full bg-black/40 text-white text-center border-2 border-white/20 focus:border-indigo-500 outline-none" />
                    </div>
                )}

                {/* EGE select */}
                {currentQuestion.is_ege_select && currentQuestion.subjects && (
                    <div className="grid grid-cols-2 gap-2 mb-5 max-h-48 overflow-y-auto">
                        {currentQuestion.subjects.map((s: any) => (
                            <label key={s.code} className="bg-white/8 border border-white/16 rounded-xl p-3 flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={egeSelectValues.includes(s.code)}
                                    onChange={(e) => {
                                        if (e.target.checked) setEgeSelectValues([...egeSelectValues, s.code])
                                        else setEgeSelectValues(egeSelectValues.filter((c) => c !== s.code))
                                    }}
                                    className="accent-primary w-4 h-4" />
                                <span className="text-slate-200 text-sm">{escapeHtml(s.label)}</span>
                            </label>
                        ))}
                    </div>
                )}

                {/* EGE scores */}
                {currentQuestion.is_ege && currentQuestion.subjects && (
                    <div className="grid grid-cols-2 gap-3 mb-5">
                        {currentQuestion.subjects.map((s: any) => (
                            <div key={s.code} className="bg-white/8 border border-white/16 rounded-xl p-3">
                                <label className="text-slate-300 text-sm block mb-1">{escapeHtml(s.label)}</label>
                                <input type="number" min={0} max={100} step={1} inputMode="numeric" value={egeValues[s.code] ?? ''}
                                    onChange={(e) => setEgeValues({ ...egeValues, [s.code]: e.target.value })}
                                    placeholder="0-100"
                                    className="w-full bg-black/40 text-white text-center border border-white/18 rounded-lg p-2 outline-none" />
                            </div>
                        ))}
                    </div>
                )}

                {/* Custom form */}
                {currentQuestion.is_custom && currentQuestion.fields && (
                    <div className="mb-5 space-y-3 max-h-48 overflow-y-auto">
                        {currentQuestion.fields.map((f: any) => (
                            <div key={f.code}>
                                <div className="text-slate-200 text-sm font-semibold block mb-1">
                                    {escapeHtml(f.label)}{f.required ? <span className="text-red-400"> *</span> : null}
                                </div>
                                {f.description ? (
                                    <div className="text-slate-400 text-xs mb-1">{escapeHtml(f.description)}</div>
                                ) : null}
                                {f.field_type === 'select' ? (
                                    <select value={customData[f.code] || ''} onChange={(e) => setCustomData({ ...customData, [f.code]: e.target.value })}
                                        className="w-full p-2 rounded-xl bg-slate-800/65 text-white border border-white/18 focus:border-indigo-500 outline-none">
                                        <option value="">— выберите —</option>
                                        {(f.options || []).map((o: string) => <option key={o} value={o}>{escapeHtml(o)}</option>)}
                                    </select>
                                ) : f.field_type === 'checkbox' ? (
                                    <input type="checkbox" checked={customData[f.code] || false}
                                        onChange={(e) => setCustomData({ ...customData, [f.code]: e.target.checked })}
                                        className="accent-primary w-5 h-5 mt-1" />
                                ) : f.field_type === 'date' ? (
                                    <input type="date" value={customData[f.code] || ''}
                                        onChange={(e) => setCustomData({ ...customData, [f.code]: e.target.value })}
                                        className="w-full p-2 rounded-xl bg-slate-800/65 text-white border border-white/18 focus:border-indigo-500 outline-none" />
                                ) : (
                                    <input type={f.field_type === 'email' ? 'email' : f.field_type === 'phone' ? 'tel' : f.field_type === 'number' ? 'number' : 'text'}
                                        inputMode={f.field_type === 'email' ? 'email' : f.field_type === 'phone' ? 'tel' : undefined}
                                        placeholder={(f.examples && f.examples[0])
                                            || (f.field_type === 'email' ? 'name@example.ru'
                                                : f.field_type === 'phone' ? '+7 ___ ___-__-__'
                                                    : f.field_type === 'number' ? 'Например, 100'
                                                        : f.field_type === 'date' ? '' : 'Введите значение')}
                                        value={customData[f.code] || ''}
                                        onChange={(e) => setCustomData({ ...customData, [f.code]: e.target.value })}
                                        className="w-full p-2 rounded-xl bg-slate-800/65 text-white border border-white/18 focus:border-indigo-500 outline-none" />
                                )}
                            </div>
                        ))}
                        <label className="flex items-start gap-2 text-slate-300 text-sm bg-white/5 border border-white/12 rounded-xl p-3 cursor-pointer">
                            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)}
                                className="accent-primary w-4 h-4 mt-0.5" />
                            <span>{escapeHtml(currentQuestion.consent_text || 'Я даю согласие на обработку персональных данных')}</span>
                        </label>
                    </div>
                )}

                {/* Next button */}
                <button onClick={handleSubmit} disabled={loading || submitting}
                    className={`w-full py-3 rounded-full text-white font-semibold transition-all ${loading || submitting ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02]'
                        }`}
                    style={{ background: 'linear-gradient(135deg, var(--primary, #667eea), var(--primary-dark, #764ba2))' }}>
                    {submitting ? (
                        // Финальный шаг: считаются рекомендации (модель/LLM) —
                        // это может занять несколько секунд, показываем честный статус
                        (currentQuestion.is_ege || (currentQuestion.is_custom && !customFirst))
                            ? '⏳ Формируем рекомендации…'
                            : 'Загрузка...'
                    ) :
                        currentQuestion.is_custom ? (customFirst ? 'Начать опрос' : 'Получить рекомендации') :
                            currentQuestion.is_ege ? 'Получить рекомендации' :
                                currentQuestion.is_ege_select ? 'Далее' :
                                    currentQuestion.is_salary ? 'Выбрать предметы ЕГЭ' :
                                        'Далее'}
                </button>
            </div>
        </div>
    )
}

export default SurveyPage
