import React, { useEffect, useState } from 'react'
import { getAdminMedia } from '../../api/services'
import { esc } from '../../utils/adminHelpers'

interface MediaPickerProps {
    /** Тип файлов: 'image' или 'video' */
    kind: string
    /** Заголовок модалки */
    title: string
    /** Колбэк при выборе файла (получает путь вида image/xxx.jpg) */
    onPick: (path: string) => void
    onClose: () => void
}

/**
 * Модалка выбора файла из медиатеки.
 * Аналог openMediaPicker из старой админки (app/admin_ui/static/admin.js).
 */
const MediaPicker: React.FC<MediaPickerProps> = ({ kind, title, onPick, onClose }) => {
    const [files, setFiles] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        getAdminMedia()
            .then((res) => setFiles((res.data.files || []).filter((f: any) => f.kind === kind)))
            .catch(() => setFiles([]))
            .finally(() => setLoading(false))
    }, [kind])

    return (
        <div
            className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
            onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
            <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
                <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl">✕</button>
                </div>
                <div className="flex-1 overflow-y-auto p-5">
                    {loading ? (
                        <p className="text-center text-sm text-slate-400 py-8">Загрузка...</p>
                    ) : files.length === 0 ? (
                        <p className="text-center text-sm text-slate-400 py-8">
                            Нет файлов. Сначала загрузите их в разделе «Медиатека».
                        </p>
                    ) : (
                        <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                            {files.map((f: any) => (
                                <button
                                    key={f.path}
                                    type="button"
                                    onClick={() => { onPick(f.path); onClose() }}
                                    className="group relative rounded-lg border border-slate-200 hover:border-indigo-400 overflow-hidden transition-colors"
                                >
                                    {kind === 'video' ? (
                                        <video src={`/media/${f.path}`} muted className="w-full h-24 object-cover" />
                                    ) : (
                                        <img src={`/media/${f.path}`} alt={f.path} className="w-full h-24 object-cover" />
                                    )}
                                    <div className="absolute bottom-0 inset-x-0 bg-black/60 text-white text-xs p-1 truncate text-center">
                                        {esc(f.path)}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default MediaPicker
