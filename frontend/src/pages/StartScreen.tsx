import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSettings } from '../api/services'
import type { Settings } from '../api/types'
import { shade, mediaUrl, escapeHtml } from '../utils/helpers'

const StartScreen: React.FC = () => {
    const navigate = useNavigate()
    const [settings, setSettings] = useState<Settings>({})
    const [heroImage, setHeroImage] = useState('')
    const [customFirst, setCustomFirst] = useState(false)

    useEffect(() => {
        getSettings()
            .then((res) => {
                const s = res.data.settings
                setSettings(s)
                setCustomFirst(s.custom_form_position !== 'end')

                // Устанавливаем hero image
                if (s.hero_image_path) {
                    const imgUrl = mediaUrl(s.hero_image_path)
                    if (imgUrl) {
                        setHeroImage(imgUrl)
                        document.documentElement.style.setProperty('--hero-image', `url('${imgUrl}')`)
                    }
                }

                // Устанавливаем primary color
                if (s.primary_color) {
                    let c = s.primary_color.startsWith('#') ? s.primary_color : '#' + s.primary_color
                    let hex = c.replace('#', '')

                    // Извлекаем alpha из 8-значного hex (#RRGGBBAA) если есть
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

    const bgGradient = `linear-gradient(160deg, var(--primary-rgba, ${settings.primary_color || '#667eea'}) 0%, var(--primary-dark-rgba, ${shade(settings.primary_color || '#667eea')}) 50%, var(--primary-rgba, ${settings.primary_color || '#667eea'}) 100%)`

    const handleStart = () => navigate('/survey')

    const logoPath = settings.logo_path || ''

    return (
        <div className="min-h-screen relative overflow-hidden"
            style={{
                // Фон: градиент из настроек с учётом прозрачности, поверх — картинка (если задана)
                backgroundImage: heroImage ? `url('${heroImage}'), ${bgGradient}` : bgGradient,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                backgroundRepeat: 'no-repeat',
                backgroundAttachment: 'fixed',
                ...(heroImage ? { backgroundBlendMode: 'overlay' } : {}),
            }}>
            {/* Цветной полупрозрачный оверлей (не затеняет фон полностью) — цвет из настроек с альфой */}
            <div className="absolute inset-0 pointer-events-none"
                style={{
                    background: `linear-gradient(to bottom right, var(--primary-soft, rgba(102,126,234,0.20)), var(--primary-bg, rgba(102,126,234,0.15)), var(--primary-soft, rgba(102,126,234,0.20)))`,
                }} />

            {/* Логотип — правильное соотношение сторон, без растяжения */}
            {logoPath && (
                <div className="absolute top-4 right-4 w-16 h-16">
                    <div className="w-full h-full rounded-full bg-white shadow-xl border-2 flex items-center justify-center overflow-hidden"
                        style={{ borderColor: 'var(--primary-soft, rgba(102,126,234,0.35))' }}>
                        <img src={`/media/${logoPath}`} alt="Logo" className="w-full h-full object-contain" />
                    </div>
                </div>
            )}

            {/* Badge */}
            <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur-md border border-white/15 rounded-full px-5 py-2 text-slate-200 text-sm font-semibold">
                {escapeHtml(settings.university_name) || 'Университет'}
            </div>

            {/* Content */}
            <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-6 py-20">
                <h1 className="text-3xl md:text-4xl font-extrabold text-white text-center mb-3 drop-shadow-lg"
                    style={{ textShadow: '0 2px 6px rgba(0, 0, 0, 0.5)' }}>
                    {escapeHtml(settings.university_name) || 'CareerAI'}
                </h1>
                <p className="text-slate-200 text-center max-w-lg leading-relaxed mb-8 drop-shadow"
                    style={{ textShadow: '0 1px 4px rgba(0, 0, 0, 0.35)' }}>
                    {escapeHtml(settings.tagline) || 'Подберём направления подготовки под ваши интересы'}
                </p>
                <button
                    onClick={handleStart}
                    className="bg-white/95 px-9 py-4 rounded-full text-xl font-bold shadow-xl hover:scale-105 transition-transform"
                    style={{
                        animation: 'pulse 1.5s infinite',
                        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.2)',
                        color: 'var(--primary, #667eea)',
                    }}>
                    {customFirst ? 'Заполнить анкету' : 'Начать опрос'}
                </button>
            </div>

            {/* Pulse animation */}
            <style>{`
                @keyframes pulse {
                    0% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.05); opacity: 0.9; }
                    100% { transform: scale(1); opacity: 1; }
                }
            `}</style>
        </div>
    )
}

export default StartScreen
