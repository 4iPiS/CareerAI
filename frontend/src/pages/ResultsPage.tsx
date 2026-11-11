import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSurvey } from '../contexts/SurveyContext'

import { mediaUrl } from '../utils/helpers'
import { submitFeedback, getDirections } from '../api/services'
import type { Recommendation } from '../api/types'

type Verdict = 'good' | 'partial' | 'bad'

type Block = {
    kind: 'strength' | 'weakness' | 'advice' | 'plain'
    text: string
}

const VERDICT_META: Record<Verdict, {
    label: string
    hint: string
    color: string
    bg: string
    border: string
    barGradient: string
}> = {
    good: {
        label: 'Подходит',
        hint: 'Направление хорошо совпадает с вашим профилем.',
        color: '#4ade80',
        bg: 'rgba(74,222,128,0.10)',
        border: 'rgba(74,222,128,0.35)',
        barGradient: 'linear-gradient(90deg, #22c55e, #4ade80)',
    },
    partial: {
        label: 'Частично подходит',
        hint: 'Есть совпадения, но часть навыков нужно развить.',
        color: '#fbbf24',
        bg: 'rgba(251,191,36,0.10)',
        border: 'rgba(251,191,36,0.35)',
        barGradient: 'linear-gradient(90deg, #f59e0b, #fbbf24)',
    },
    bad: {
        label: 'Пока не подходит',
        hint: 'Совпадение с профилем слабое — рассмотрите варианты выше.',
        color: '#f87171',
        bg: 'rgba(248,113,113,0.10)',
        border: 'rgba(248,113,113,0.35)',
        barGradient: 'linear-gradient(90deg, #ef4444, #f87171)',
    },
}

function verdictFromRec(rec: Recommendation): Verdict {
    if (rec.verdict) {
        if (rec.verdict === 'ПОДХОДИТ') return 'good'
        if (rec.verdict === 'ЧАСТИЧНО ПОДХОДИТ') return 'partial'
        if (rec.verdict === 'НЕ ПОДХОДИТ') return 'bad'
    }
    // Fallback: разбираем старый текстовый формат explanation
    const m = (rec.explanation || '').match(/Вердикт:.*?([Дд]а|[Нн]ет|[Оо]тчасти)\s+подходит/)
    if (m) {
        if (m[1].toLowerCase() === 'да') return 'good'
        if (m[1].toLowerCase() === 'отчасти') return 'partial'
        return 'bad'
    }
    const p = rec.probability ?? 0
    return p >= 55 ? 'good' : p >= 30 ? 'partial' : 'bad'
}

function fallbackBlocks(rec: Recommendation): Block[] {
    // Для старого формата: explanation был строкой с блоками через ' | '
    const blocks: Block[] = []
    const parts = (rec.explanation || '').split(' | ')
    for (const part of parts) {
        if (part.includes('Вердикт:')) continue
        if (part.includes('Почему подходит:') || part.includes('Сильные стороны:')) {
            blocks.push({ kind: 'strength', text: part.replace(/^.*?:\s*/, '') })
        } else if (part.includes('Почему не подходит:') || part.includes('Требуют внимания:')) {
            blocks.push({ kind: 'weakness', text: part.replace(/^.*?:\s*/, '') })
        } else if (part.includes('Совет:')) {
            blocks.push({ kind: 'advice', text: part.replace(/^.*?:\s*/, '') })
        } else if (part.trim()) {
            blocks.push({ kind: 'plain', text: part.trim() })
        }
    }
    return blocks
}

function structuredBlocks(rec: Recommendation): Block[] {
    const blocks: Block[] = []
    for (const s of rec.strengths || []) {
        if (s.trim()) blocks.push({ kind: 'strength', text: s.trim() })
    }
    for (const w of rec.weaknesses || []) {
        if (w.trim()) blocks.push({ kind: 'weakness', text: w.trim() })
    }
    return blocks
}

function skillChips(keySkills: string): string[] {
    return (keySkills || '')
        .split(/[,;|]/)
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, 8)
}

const ResultsPage: React.FC = () => {
    const navigate = useNavigate()
    const { sessionId: ctxSessionId, recommendations, reset } = useSurvey()
    const [sessionId, setSessionId] = useState<string | null>(ctxSessionId)
    const [selectedDirections, setSelectedDirections] = useState<string[]>([])
    const [feedbackScore, setFeedbackScore] = useState(0)
    const [feedbackMsg, setFeedbackMsg] = useState('')
    const [feedbackSent, setFeedbackSent] = useState(false)
    const [feedbackSending, setFeedbackSending] = useState(false)
    const [fallbackRecs, setFallbackRecs] = useState<Recommendation[] | null>(null)
    const [allDirections, setAllDirections] = useState<string[]>([])
    const [showOtherDirections, setShowOtherDirections] = useState(false)
    const bgGradient = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'

    const toggleDirection = (field: string) => {
        setSelectedDirections((prev) =>
            prev.includes(field) ? prev.filter((f) => f !== field) : [...prev, field],
        )
    }

    const handleSubmitFeedback = async () => {
        if (!sessionId) {
            setFeedbackMsg('Сессия не найдена — невозможно отправить отзыв.')
            return
        }
        if (selectedDirections.length === 0) {
            setFeedbackMsg('Выберите хотя бы одно направление.')
            return
        }
        setFeedbackSending(true)
        try {
            await submitFeedback(sessionId, selectedDirections, feedbackScore > 0 ? feedbackScore : undefined)
            setFeedbackSent(true)
            setFeedbackMsg('Ваш отзыв сохранён — он поможет сделать рекомендации точнее.')
        } catch (e: any) {
            setFeedbackMsg(e.response?.data?.detail || e.message || 'Не удалось отправить отзыв.')
        } finally {
            setFeedbackSending(false)
        }
    }

    useEffect(() => {
        if (!sessionId) {
            const saved = localStorage.getItem('sessionId')
            if (saved) setSessionId(saved)
        }
    }, [sessionId])

    useEffect(() => {
        if (!recommendations) {
            try {
                const saved = localStorage.getItem('recommendations')
                if (saved) {
                    const recs = JSON.parse(saved)
                    if (Array.isArray(recs) && recs.length > 0) {
                        setFallbackRecs(recs)
                    }
                }
            } catch {}
        }
    }, [recommendations])

    const displayRecs = recommendations || fallbackRecs

    // Загружаем ВСЕ активные направления — в обратной связи можно выбрать
    // любое направление каталога, а не только то, что рекомендовало.
    useEffect(() => {
        let active = true
        getDirections()
            .then((res) => {
                if (!active) return
                const names: string[] = (res.data.directions || []).map((d: any) => d.name)
                setAllDirections(names)
            })
            .catch(() => {})
        return () => { active = false }
    }, [])

    if (!displayRecs) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-6"
                style={{ backgroundImage: bgGradient }}>
                <div className="text-white text-xl">Результаты не найдены</div>
                <button onClick={() => { reset(); navigate('/') }}
                    className="py-3 px-8 rounded-full text-white font-semibold"
                    style={{ background: `linear-gradient(135deg, #667eea, #764ba2)` }}>
                    Начать опрос
                </button>
            </div>
        )
    }

    // Направления каталога, которых не было в рекомендациях
    const otherDirections = allDirections.filter(
        (name) => !displayRecs.some((rec) => rec.field === name),
    )

    const best = displayRecs[0]

    return (
        <div className="min-h-screen relative"
            style={{
                backgroundImage: bgGradient,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                backgroundRepeat: 'no-repeat',
                backgroundAttachment: 'fixed',
            }}>
            <div className="absolute inset-0 pointer-events-none"
                style={{
                    background: `linear-gradient(to bottom right, var(--primary-soft, rgba(102,126,234,0.10)), var(--primary-bg, rgba(102,126,234,0.08)), var(--primary-soft, rgba(102,126,234,0.10)))`,
                }} />

            <div className="w-full max-w-3xl mx-auto px-4 py-8 pb-20">
                <h2 className="text-white text-3xl font-bold text-center">Ваши рекомендации</h2>
                {best && (
                    <p className="text-white/70 text-center mt-2 mb-8">
                        Лучшее совпадение — <span className="font-semibold">{best.field}</span>
                        {typeof best.probability === 'number' && <> · {best.probability}% соответствия</>}
                    </p>
                )}

                {displayRecs.map((rec) => {
                    const imgUrl = rec.image ? mediaUrl(rec.image) : ''
                    const verdict = verdictFromRec(rec)
                    const meta = VERDICT_META[verdict]
                    const prob = Math.max(0, Math.min(100, rec.probability ?? 0))
                    const blocks = structuredBlocks(rec).length > 0
                        ? structuredBlocks(rec)
                        : fallbackBlocks(rec)
                    const advice = rec.advice || blocks.find((b) => b.kind === 'advice')?.text || ''
                    const summary = rec.summary ||
                        blocks.filter((b) => b.kind === 'plain').map((b) => b.text).join(' ')
                    const chips = skillChips(rec.key_skills)

                    return (
                        <div key={rec.rank}
                            className="bg-slate-800/95 rounded-2xl p-5 mb-5 shadow-lg"
                            style={{ border: `1px solid ${meta.border}` }}>

                            {imgUrl && (
                                <img src={imgUrl} alt={rec.field}
                                    className="w-full max-h-44 object-cover rounded-xl mb-4"
                                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                            )}

                            {/* Заголовок карточки */}
                            <div className="flex items-center gap-3 mb-4">
                                <div className="w-10 h-10 shrink-0 rounded-full flex items-center justify-center text-white font-bold"
                                    style={{ background: `linear-gradient(135deg, #667eea, #764ba2)` }}>
                                    {rec.rank}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className="text-white font-semibold text-lg leading-tight">{rec.field}</h3>
                                    {rec.code && <div className="text-slate-400 text-xs mt-0.5">Код ФГОС: {rec.code}</div>}
                                </div>
                                <div className="text-right shrink-0">
                                    <div className="text-2xl font-bold leading-none"
                                        style={{ color: meta.color }}>{prob}%</div>
                                    <div className="text-slate-400 text-xs mt-1">соответствие</div>
                                </div>
                            </div>

                            {/* Прогресс-бар процента */}
                            <div className="h-2.5 w-full rounded-full bg-slate-700 overflow-hidden mb-4">
                                <div className="h-full rounded-full transition-all duration-700"
                                    style={{ width: `${prob}%`, background: meta.barGradient }} />
                            </div>

                            {/* Вердикт */}
                            <div className="rounded-xl p-4 mb-4"
                                style={{ background: meta.bg, border: `1px solid ${meta.border}` }}>
                                <div className="text-lg font-bold" style={{ color: meta.color }}>
                                    {meta.label}
                                </div>
                                <div className="text-slate-400 text-sm mt-1">{meta.hint}</div>
                            </div>

                            {rec.description && (
                                <p className="text-slate-300 text-sm mb-4 leading-relaxed">{rec.description}</p>
                            )}

                            {/* Итоговое пояснение */}
                            {summary && (
                                <p className="text-slate-200 text-sm mb-4 leading-relaxed">{summary}</p>
                            )}

                            {/* Сильные стороны / пробелы */}
                            {blocks.filter((b) => b.kind !== 'advice' && b.kind !== 'plain').length > 0 && (
                                <div className="space-y-2 mb-4">
                                    {blocks.filter((b) => b.kind !== 'advice' && b.kind !== 'plain').map((block, i) => {
                                        const isStrength = block.kind === 'strength'
                                        return (
                                            <div key={i}
                                                className="flex items-start gap-2 rounded-xl p-3 text-sm leading-relaxed"
                                                style={{
                                                    background: isStrength
                                                        ? 'rgba(74,222,128,0.08)' : 'rgba(251,191,36,0.08)',
                                                    border: `1px solid ${isStrength
                                                        ? 'rgba(74,222,128,0.25)' : 'rgba(251,191,36,0.25)'}`,
                                                }}>
                                                <span className="shrink-0 mt-0.5">{isStrength ? '✓' : '⚠'}</span>
                                                <span className={isStrength ? 'text-green-200' : 'text-amber-200'}>
                                                    {block.text}
                                                </span>
                                            </div>
                                        )
                                    })}
                                </div>
                            )}

                            {/* Совет */}
                            {advice && (
                                <div className="flex items-start gap-2 rounded-xl p-3 text-sm leading-relaxed mb-2"
                                    style={{
                                        background: 'rgba(96,165,250,0.08)',
                                        border: '1px solid rgba(96,165,250,0.25)',
                                    }}>
                                    <span className="shrink-0 mt-0.5">💡</span>
                                    <span className="text-blue-200">{advice}</span>
                                </div>
                            )}

                            {/* Ключевые навыки — чипы */}
                            {chips.length > 0 && (
                                <div className="flex flex-wrap gap-1.5 mt-4">
                                    {chips.map((chip, i) => (
                                        <span key={i}
                                            className="text-xs px-2.5 py-1 rounded-full bg-white/5 text-slate-300 border border-white/10">
                                            {chip}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    )
                })}

                {/* Обратная связь */}
                {!feedbackSent ? (
                    <div className="bg-slate-800/95 rounded-2xl p-5 mb-5 border border-white/10">
                        <h3 className="text-white font-semibold text-lg mb-1">Помогите стать точнее</h3>
                        <p className="text-slate-400 text-sm mb-4">
                            Отметьте направления, которые вам действительно интересны, — это сделает будущие рекомендации лучше.
                        </p>
                        <div className="space-y-2 mb-4">
                            {displayRecs.map((rec) => (
                                <label key={rec.rank}
                                    className="flex items-center gap-3 text-slate-200 text-sm cursor-pointer hover:text-white">
                                    <input
                                        type="checkbox"
                                        checked={selectedDirections.includes(rec.field)}
                                        onChange={() => toggleDirection(rec.field)}
                                        className="w-4 h-4 accent-indigo-500"
                                    />
                                    {rec.field}
                                </label>
                            ))}
                            {otherDirections.length > 0 && (
                                <>
                                    <button
                                        type="button"
                                        onClick={() => setShowOtherDirections(!showOtherDirections)}
                                        className="text-indigo-300 text-sm font-medium hover:text-indigo-200 mt-1"
                                    >
                                        {showOtherDirections
                                            ? '▾ Скрыть остальные направления'
                                            : `▸ Ещё направления (${otherDirections.length})`}
                                    </button>
                                    {showOtherDirections && (
                                        <div className="space-y-2 max-h-64 overflow-y-auto pl-3 border-l border-white/15 mt-1">
                                            {otherDirections.map((name) => (
                                                <label key={name}
                                                    className="flex items-center gap-3 text-slate-300 text-sm cursor-pointer hover:text-white">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedDirections.includes(name)}
                                                        onChange={() => toggleDirection(name)}
                                                        className="w-4 h-4 accent-indigo-500"
                                                    />
                                                    {name}
                                                </label>
                                            ))}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                        <div className="flex items-center gap-1 mb-4">
                            {[1, 2, 3, 4, 5].map((n) => (
                                <button
                                    key={n}
                                    onClick={() => setFeedbackScore(n)}
                                    className={`text-2xl leading-none transition-colors ${
                                        feedbackScore >= n ? 'text-amber-400' : 'text-slate-600 hover:text-amber-200'
                                    }`}
                                    title={`Оценка ${n} из 5`}
                                >
                                    {feedbackScore >= n ? '★' : '☆'}
                                </button>
                            ))}
                            <span className="text-slate-400 text-sm ml-2">
                                {feedbackScore > 0 ? `${feedbackScore}/5` : 'Оцените рекомендации'}
                            </span>
                        </div>
                        {feedbackMsg && <div className="text-sm text-amber-300 mb-2">{feedbackMsg}</div>}
                        <button
                            onClick={handleSubmitFeedback}
                            disabled={feedbackSending}
                            className="w-full py-3 bg-indigo-500 text-white rounded-full font-semibold hover:bg-indigo-600 disabled:opacity-50 transition-colors"
                        >
                            {feedbackSending ? 'Отправка…' : 'Отправить отзыв'}
                        </button>
                    </div>
                ) : (
                    <div className="bg-green-500/10 border border-green-500/30 rounded-2xl p-5 mb-5 text-center">
                        <div className="text-green-300 font-semibold text-lg">Спасибо за отзыв!</div>
                        <div className="text-slate-400 text-sm mt-1">{feedbackMsg}</div>
                    </div>
                )}

                <button onClick={() => { reset(); navigate('/') }}
                    className="w-full py-3 bg-slate-700 text-white rounded-full font-semibold hover:bg-slate-600 transition-colors">
                    Пройти заново
                </button>
            </div>
        </div>
    )
}

export default ResultsPage
