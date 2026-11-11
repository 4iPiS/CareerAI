/**
 * Utility functions for CareerAI frontend
 * Перенесено из старого vanilla JS фронтенда
 */

/** Ключ для localStorage */
export const PROGRESS_KEY = 'careerai_progress';

/** Сохранение прогресса в localStorage */
export function saveProgress(progress: any) {
    try {
        localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress || {}));
    } catch (e) {
        console.warn('Failed to save progress:', e);
    }
}

/** Восстановление прогресса из localStorage */
export function restoreProgress() {
    try {
        const saved = localStorage.getItem(PROGRESS_KEY);
        return saved ? JSON.parse(saved) : null;
    } catch (e) {
        return null;
    }
}

/** Очистка прогресса из localStorage */
export function clearProgress() {
    try {
        localStorage.removeItem(PROGRESS_KEY);
    } catch (e) {
        console.warn('Failed to clear progress:', e);
    }
}

/** Затемнение цвета */
export function shade(hex: string, percent = -18): string {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const r = Math.min(255, Math.max(0, (num >> 16) + amt));
    const g = Math.min(255, Math.max(0, ((num >> 8) & 0xff) + amt));
    const b = Math.min(255, Math.max(0, (num & 0xff) + amt));
    return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
}

/** Получение URL для медиафайлов */
export function mediaUrl(p: string | undefined | null): string {
    if (!p || typeof p !== 'string' || !p.trim()) return '';
    if (/^https?:\/\//i.test(p) || /^[a-zA-Z]:[\\/]/.test(p) || p.indexOf('\\') !== -1) return '';
    let path = p.trim();
    if (path.indexOf('/media/') !== 0) {
        path = '/media/' + path;
    }
    return path;
}

/** Экранирование HTML */
export function escapeHtml(text: string | number | null | undefined): string {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

/** Получение названия этапа */
export function getStageName(stage: string | undefined): string {
    const names: Record<string, string> = {
        screening: 'Шаг 1/3: Интересы',
        detailed: 'Шаг 2/3: Углублённо',
        personal: 'Шаг 3/3: Личные качества',
        salary: 'Зарплата',
        ege_select: 'Выбор предметов ЕГЭ',
        ege: 'Баллы ЕГЭ',
        custom: 'Анкета',
    };
    return names[stage || ''] || 'Опрос';
}

/** Получение процента прогресса */
export function getProgressPercent(progress: any): number {
    if (progress?.progress?.total && progress?.progress?.current) {
        return (progress.progress.current / progress.progress.total) * 100;
    }
    return 0;
}

/** Валидация email */
export function isValidEmail(email: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
}

/** Валидация телефона */
export function isValidPhone(phone: string): boolean {
    const digits = phone.replace(/[^\d]/g, '');
    return digits.length >= 10 && digits.length <= 15;
}

/** Форматирование числа с разделителями тысяч (ru-RU) */
export function formatNumber(n: number | null | undefined): string {
    if (n == null) return '—';
    return n.toLocaleString('ru-RU');
}

/** Форматирование ISO-даты в читаемый вид */
export function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    } catch {
        return dateStr;
    }
}

/** Метка статуса сессии */
export function sessionStatusLabel(status: string | undefined): string {
    const labels: Record<string, string> = {
        in_progress: 'В процессе',
        completed: 'Завершена',
        abandoned: 'Прервана',
    };
    return labels[status || ''] || status || '—';
}

/** CSS-класс для статуса сессии */
export function sessionStatusColor(status: string | undefined): string {
    switch (status) {
        case 'completed': return 'bg-green-100 text-green-800';
        case 'in_progress': return 'bg-blue-100 text-blue-800';
        case 'abandoned': return 'bg-slate-100 text-slate-600';
        default: return 'bg-slate-100 text-slate-600';
    }
}

/** CSS-класс для статуса тренировки модели */
export function trainStatusColor(status: string | undefined): string {
    switch (status) {
        case 'completed': return 'bg-green-100 text-green-800';
        case 'failed': return 'bg-red-100 text-red-800';
        case 'running': return 'bg-blue-100 text-blue-800';
        case 'pending': return 'bg-amber-100 text-amber-800';
        default: return 'bg-slate-100 text-slate-600';
    }
}

/** Текстовое описание статуса тренировки */
export function trainStatusLabel(status: string | undefined): string {
    const labels: Record<string, string> = {
        completed: 'Завершено',
        failed: 'Ошибка',
        running: 'В процессе',
        pending: 'Ожидает',
    };
    return labels[status || ''] || status || '—';
}
