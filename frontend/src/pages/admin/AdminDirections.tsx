import React, { useEffect, useState, useCallback } from 'react'
import { getAdminDirections, createDirection, updateDirection, deleteDirection, getAdminMedia } from '../../api/services'
import type { Direction } from '../../api/types'
import { esc, yearsLabel } from '../../utils/adminHelpers'

const AdminDirections: React.FC = () => {
    const [directions, setDirections] = useState<Direction[]>([])
    const [loading, setLoading] = useState(true)
    const [showForm, setShowForm] = useState(false)
    const [editing, setEditing] = useState<Direction | null>(null)

    const [name, setName] = useState('')
    const [fgosCode, setFgosCode] = useState('')
    const [category, setCategory] = useState('')
    const [studyYears, setStudyYears] = useState(4)
    const [egeTypical, setEgeTypical] = useState('')
    const [sortOrder, setSortOrder] = useState(0)
    const [description, setDescription] = useState('')
    const [keySkillsText, setKeySkillsText] = useState('')
    const [skillCodes, setSkillCodes] = useState('')
    const [imagePath, setImagePath] = useState('')
    const [avgSalary, setAvgSalary] = useState(0)
    const [employmentRate, setEmploymentRate] = useState(0)
    const [isActive, setIsActive] = useState(true)

    const [showPicker, setShowPicker] = useState(false)
    const [mediaFiles, setMediaFiles] = useState<any[]>([])
    const [pickerLoading, setPickerLoading] = useState(false)

    const load = useCallback(() => {
        setLoading(true)
        getAdminDirections()
            .then((res) => setDirections(res.data.directions || []))
            .catch(() => {})
            .finally(() => setLoading(false))
    }, [])

    useEffect(() => { load() }, [load])

    const resetForm = () => {
        setName('')
        setFgosCode('')
        setCategory('')
        setStudyYears(4)
        setEgeTypical('')
        setSortOrder(0)
        setDescription('')
        setKeySkillsText('')
        setSkillCodes('')
        setImagePath('')
        setAvgSalary(0)
        setEmploymentRate(0)
        setIsActive(true)
        setEditing(null)
    }

    const startEdit = (d: Direction) => {
        setEditing(d)
        setShowForm(true)
        setName(d.name || '')
        setFgosCode(d.fgos_code || '')
        setCategory(d.category || '')
        setStudyYears(d.study_years || 4)
        setEgeTypical(d.ege_typical || '')
        setSortOrder(d.sort_order || 0)
        setDescription(d.description || '')
        setKeySkillsText(d.key_skills_text || '')
        setSkillCodes((d.skill_codes || []).join(', '))
        setImagePath(d.image_path || '')
        setAvgSalary(d.avg_salary || 0)
        setEmploymentRate(d.employment_rate || 0)
        setIsActive(!!d.is_active)
    }

    const handleSave = async () => {
        if (!name.trim()) {
            alert('Введите название направления')
            return
        }
        const payload: any = {
            name: name.trim(),
            fgos_code: fgosCode.trim(),
            category: category.trim(),
            study_years: Number(studyYears) || 4,
            ege_typical: egeTypical.trim(),
            sort_order: Number(sortOrder) || 0,
            description,
            key_skills_text: keySkillsText,
            skill_codes: skillCodes.split(',').map((s) => s.trim()).filter(Boolean),
            image_path: imagePath.trim(),
            avg_salary: Number(avgSalary) || 0,
            employment_rate: Number(employmentRate) || 0,
            is_active: isActive,
        }
        try {
            if (editing) {
                await updateDirection(editing.id, payload)
            } else {
                await createDirection(payload)
            }
            setShowForm(false)
            resetForm()
            load()
        } catch (e: any) {
            alert(e.response?.data?.detail || 'Ошибка сохранения')
        }
    }

    const handleDelete = async (id: number) => {
        if (!confirm('Удалить направление?')) return
        try {
            await deleteDirection(id)
            load()
        } catch (e: any) {
            alert(e.response?.data?.detail || 'Ошибка удаления')
        }
    }

    const openPicker = async () => {
        setShowPicker(true)
        setPickerLoading(true)
        try {
            const res = await getAdminMedia()
            setMediaFiles((res.data.files || []).filter((f: any) => f.kind === 'image'))
        } catch (e: any) {
            alert(e.response?.data?.detail || 'Ошибка загрузки медиатеки')
        } finally {
            setPickerLoading(false)
        }
    }

    if (loading) return <div className="text-center py-10">Загрузка...</div>

    return (
        <div className="space-y-6">
            <div className="flex justify-end">
                <button
                    onClick={() => { resetForm(); setShowForm(true) }}
                    className="px-4 py-2 rounded-lg text-white text-sm font-semibold bg-indigo-500 hover:bg-indigo-600">
                    + Добавить
                </button>
            </div>
            {showForm && (
                <div className="bg-white rounded-xl p-5 shadow-sm space-y-4">
                    <h2 className="text-lg font-semibold text-slate-800">{editing ? 'Редактировать направление' : 'Новое направление'}</h2>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Название</label>
                            <input value={name} onChange={(e) => setName(e.target.value)}
                                className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Код ФГОС</label>
                            <input value={fgosCode} onChange={(e) => setFgosCode(e.target.value)}
                                className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Категория</label>
                            <input value={category} onChange={(e) => setCategory(e.target.value)}
                                className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Срок обучения (лет)</label>
                            <input type="number" value={studyYears} onChange={(e) => setStudyYears(parseInt(e.target.value) || 0)}
                                className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">ЕГЭ (через запятую)</label>
                            <input value={egeTypical} onChange={(e) => setEgeTypical(e.target.value)}
                                className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Сортировка</label>
                            <input type="number" value={sortOrder} onChange={(e) => setSortOrder(parseInt(e.target.value) || 0)}
                                className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Средняя зарплата, ₽</label>
                            <input type="number" value={avgSalary} onChange={(e) => setAvgSalary(parseInt(e.target.value) || 0)}
                                className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Трудоустройство, %</label>
                            <input type="number" value={employmentRate} onChange={(e) => setEmploymentRate(parseInt(e.target.value) || 0)}
                                className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Описание</label>
                        <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
                            className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Ключевые навыки (текст)</label>
                        <textarea value={keySkillsText} onChange={(e) => setKeySkillsText(e.target.value)} rows={3}
                            className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Коды навыков (через запятую)</label>
                        <input value={skillCodes} onChange={(e) => setSkillCodes(e.target.value)}
                            className="w-full p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500" />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Изображение</label>
                        <div className="flex gap-2">
                            <input value={imagePath} onChange={(e) => setImagePath(e.target.value)} readOnly
                                placeholder="image/xxxx.jpg"
                                className="flex-1 p-2 border border-slate-200 rounded-lg outline-none focus:border-indigo-500 bg-slate-50" />
                            <button type="button" onClick={openPicker}
                                className="px-3 py-2 bg-slate-200 hover:bg-slate-300 rounded-lg text-sm font-medium">
                                Выбрать
                            </button>
                        </div>
                        <p className="text-xs text-slate-400 mt-1">Показывается рядом с названием в результатах. Можно не выбирать.</p>
                    </div>

                    <label className="flex items-center gap-2 text-sm text-slate-600">
                        <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)}
                            className="" /> Активно (показывается в рекомендациях)
                    </label>

                    <div className="flex gap-2">
                        <button onClick={handleSave}
                            className="px-4 py-2 rounded-lg text-white text-sm bg-indigo-500 hover:bg-indigo-600">
                            {editing ? 'Сохранить' : 'Создать'}
                        </button>
                        <button onClick={() => { setShowForm(false); resetForm() }}
                            className="px-4 py-2 rounded-lg text-sm bg-slate-200 hover:bg-slate-300">
                            Отмена
                        </button>
                    </div>
                </div>
            )}

            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                <table className="w-full">
                    <thead className="bg-slate-50">
                        <tr>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Название</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Код</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Категория</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Срок</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">ЕГЭ</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600">Активн.</th>
                            <th className="px-4 py-3 text-left text-sm font-semibold text-slate-600"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {directions.map((d) => (
                            <tr key={d.id} className="border-t">
                                <td className="px-4 py-3 text-sm">{esc(d.name)}</td>
                                <td className="px-4 py-3 text-sm">{esc(d.fgos_code)}</td>
                                <td className="px-4 py-3 text-sm text-slate-500">{esc(d.category || '—')}</td>
                                <td className="px-4 py-3 text-sm">{yearsLabel(d.study_years || 4)}</td>
                                <td className="px-4 py-3 text-sm text-slate-500">{esc(d.ege_typical || '—')}</td>
                                <td className="px-4 py-3 text-sm">{d.is_active ? 'да' : 'нет'}</td>
                                <td className="px-4 py-3 text-sm">
                                    <button onClick={() => startEdit(d)}
                                        className="text-indigo-500 hover:text-indigo-700 mr-2">Ред.</button>
                                    <button onClick={() => handleDelete(d.id)}
                                        className="text-red-500 hover:text-red-700">Удал.</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {showPicker && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
                    onClick={(e) => { if (e.target === e.currentTarget) setShowPicker(false) }}>
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
                        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
                            <h3 className="text-lg font-semibold text-slate-800">Выбор изображения</h3>
                            <button onClick={() => setShowPicker(false)} className="text-slate-400 hover:text-slate-600 text-xl">✕</button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-5">
                            {pickerLoading ? (
                                <p className="text-center text-sm text-slate-400 py-8">Загрузка...</p>
                            ) : mediaFiles.length === 0 ? (
                                <p className="text-center text-sm text-slate-400 py-8">Нет изображений. Сначала загрузите файлы в медиатеку.</p>
                            ) : (
                                <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                                    {mediaFiles.map((f: any) => (
                                        <button key={f.path}
                                            onClick={() => { setImagePath(f.path); setShowPicker(false) }}
                                            className="group relative rounded-lg border border-slate-200 hover:border-indigo-400 overflow-hidden transition-colors">
                                            <img src={`/media/${f.path}`} alt={f.path} className="w-full h-24 object-cover" />
                                            <div className="absolute bottom-0 inset-x-0 bg-black/60 text-white text-xs p-1 truncate text-center">{esc(f.path)}</div>
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

export default AdminDirections