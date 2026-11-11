import React, { useEffect, useState, useRef, useCallback } from 'react'
import { getAdminMedia, uploadMedia, deleteMedia } from '../../api/services'
import { esc } from '../../utils/adminHelpers'

interface MediaFile {
  id?: number
  path: string
  url: string
  name: string
  kind: 'image' | 'video' | 'audio'
  size: number
}

const AdminMedia: React.FC = () => {
  const [files, setFiles] = useState<MediaFile[]>([])
  const [loading, setLoading] = useState(true)
  const [uploadKind, setUploadKind] = useState('image')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadResult, setUploadResult] = useState('')
  const [showPicker, setShowPicker] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadFiles = useCallback(async () => {
    try {
      const res = await getAdminMedia()
      setFiles(res.data.files || [])
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка загрузки медиатеки')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadFiles()
  }, [loadFiles])

  const handleUpload = useCallback(async () => {
    if (!uploadFile) {
      alert('Выберите файл')
      return
    }

    setUploading(true)
    setUploadProgress(0)
    setUploadResult('')

    try {
      const res = await uploadMedia(uploadKind, uploadFile, (e: any) => {
        if (e.total && e.total > 0) {
          setUploadProgress(Math.round((e.loaded * 100) / e.total))
        }
      })
      const path = res.data.path || res.data.file_path || ''
      if (path) {
        setUploadResult(path)
        await loadFiles()
      }
    } catch (e: any) {
      alert('Ошибка загрузки: ' + (e.response?.data?.detail || e.message))
    } finally {
      setUploading(false)
      setUploadProgress(0)
      setUploadFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }, [uploadFile, uploadKind, loadFiles])

  const handleDelete = useCallback(
    async (path: string) => {
      if (!confirm('Удалить файл из хранилища?')) return
      try {
        await deleteMedia(path)
        setFiles((prev) => prev.filter((f) => f.path !== path))
      } catch (e: any) {
        alert('Ошибка удаления: ' + (e.response?.data?.detail || e.message))
      }
    },
    []
  )

  const handlePick = useCallback(
    (_path: string) => {
      setShowPicker(false)
    },
    []
  )

  if (loading) return <div className="text-center py-10">Загрузка...</div>

  return (
    <div className="space-y-6">

      {/* Upload */}
      <div className="bg-white rounded-xl p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-4 text-slate-800">Загрузка файла</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Тип</label>
            <select
              value={uploadKind}
              onChange={(e) => setUploadKind(e.target.value)}
              className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500"
            >
              <option value="image">Изображение</option>
              <option value="video">Видео</option>
              <option value="audio">Аудио</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Файл</label>
            <input
              ref={fileInputRef}
              type="file"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              className="w-full p-2.5 border border-slate-200 rounded-lg outline-none focus:border-indigo-500 text-sm"
            />
          </div>
        </div>

        <button
          onClick={handleUpload}
          disabled={uploading || !uploadFile}
          className="mt-4 px-5 py-2.5 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50 font-medium text-sm"
        >
          {uploading ? 'Загрузка...' : 'Загрузить'}
        </button>

        {/* Progress bar */}
        {uploading && (
          <div className="mt-3">
            <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-indigo-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-1">{uploadProgress}%</p>
          </div>
        )}

        {uploadResult && (
          <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-700 font-mono">{esc(uploadResult)}</p>
            {uploadKind === 'image' && (
              <img
                src={`/media/${uploadResult}`}
                alt="preview"
                className="mt-2 max-w-48 rounded-lg border border-slate-200"
              />
            )}
          </div>
        )}
      </div>

      {/* File list */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="text-lg font-semibold text-slate-800">
            Хранилище ({files.length})
          </h2>
        </div>
        {files.length === 0 ? (
          <p className="p-6 text-sm text-slate-400 text-center">
            Пока нет загруженных файлов.
          </p>
        ) : (
          <div className="divide-y divide-slate-100">
            {files.map((f) => (
              <div
                key={f.path}
                className="flex items-center gap-4 px-5 py-3 hover:bg-slate-50"
              >
                {/* Preview */}
                {f.kind === 'image' && (
                  <img
                    src={`/media/${f.path}`}
                    alt={f.path}
                    className="w-20 h-14 object-cover rounded-lg border border-slate-200 flex-shrink-0"
                  />
                )}
                {f.kind === 'video' && (
                  <video
                    src={`/media/${f.path}`}
                    muted
                    className="w-28 h-14 object-cover rounded-lg border border-slate-200 flex-shrink-0"
                  />
                )}
                {f.kind === 'audio' && (
                  <div className="w-10 h-10 flex items-center justify-center bg-slate-100 rounded-lg text-xl flex-shrink-0">
                    🎵
                  </div>
                )}

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-mono text-slate-700 truncate">
                    {esc(f.path)}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {Math.round((f.size || 0) / 1024)} КБ
                  </p>
                </div>

                {/* Delete */}
                <button
                  onClick={() => handleDelete(f.path)}
                  className="px-3 py-1.5 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg text-sm font-medium flex-shrink-0"
                >
                  Удал.
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info panel */}
      <div className="bg-white rounded-xl p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-2 text-slate-800">Как использовать</h2>
        <p className="text-sm text-slate-500">
          Кнопка «выбрать из хранилища» есть в «Настройках» (логотип, фон, видео) и в
          редакторе направлений (картинка) — путь подставится сам.
        </p>
      </div>

      {/* Media Picker Modal */}
      {showPicker && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowPicker(false)
          }}
        >
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-800">
                Выбор файла из хранилища
              </h3>
              <button
                onClick={() => setShowPicker(false)}
                className="text-slate-400 hover:text-slate-600 text-xl"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5">
              {files.length === 0 ? (
                <p className="text-center text-sm text-slate-400 py-8">
                  Нет файлов для выбора. Сначала загрузите файлы в медиатеку.
                </p>
              ) : (
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                  {files.map((f) => (
                    <button
                      key={f.path}
                      onClick={() => handlePick(f.path)}
                      className="group relative rounded-lg border border-slate-200 hover:border-indigo-400 overflow-hidden transition-colors"
                    >
                      {f.kind === 'image' && (
                        <img
                          src={`/media/${f.path}`}
                          alt={f.path}
                          className="w-full h-24 object-cover"
                        />
                      )}
                      {f.kind === 'video' && (
                        <video
                          src={`/media/${f.path}`}
                          muted
                          className="w-full h-24 object-cover"
                        />
                      )}
                      {f.kind === 'audio' && (
                        <div className="w-full h-24 flex items-center justify-center bg-slate-100 text-3xl">
                          🎵
                        </div>
                      )}
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
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
      )}
    </div>
  )
}

export default AdminMedia
