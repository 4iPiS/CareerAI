/* CareerAI Admin — Shared Utilities */

/* --- Безопасное экранирование --- */
export const esc = (s: any): string => String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

/* --- yearsLabel (русский склонение) --- */
export function yearsLabel(n: number): string {
    n = Number(n) || 0;
    const mod10 = n % 10, mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) return n + ' год';
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return n + ' года';
    return n + ' лет';
}

/* --- datasetLabel --- */
export function datasetLabel(dataset: any, isFinetune?: boolean): string {
    if (dataset == null) return '—';
    if (typeof dataset === 'string') {
        if (isFinetune) return 'fine-tuning';
        if (dataset === 'all') return 'синтетика + реальные';
        if (dataset === 'real_only') return 'только реальные';
        if (dataset === 'synthetic') return 'только синтетика';
        if (dataset === 'finetune') return 'дообучение (реальные)';
        return dataset;
    }
    if (typeof dataset === 'object') {
        const parts: string[] = [];
        if (dataset.synthetic || dataset.use_synthetic) parts.push('синтетика');
        if (dataset.real || dataset.use_real) parts.push('реал.');
        if (parts.length) return parts.join(' + ');
        return JSON.stringify(dataset);
    }
    return String(dataset);
}

/* --- QTYPE_LABELS --- */
export const QTYPE_LABELS: Record<string, string> = {
    rating_1_5: 'Оценка 1–5',
    salary: 'Зарплата',
    choice_single: 'Выбор одного',
    choice_multi: 'Выбор нескольких',
    text_input: 'Текст',
    number_input: 'Число',
};

/* --- qActivationText --- */
export function qActivationText(cond: any): string {
    if (!cond) return 'всегда';
    if (cond.type === 'interest_ge') {
        return `если интерес к «${esc(cond.feature || '?')}» ≥ ${esc(cond.value)}`;
    }
    if (cond.type === 'any_interest_ge') {
        return `если интерес к одному из [${(cond.features || []).map(esc).join(', ')}] ≥ ${esc(cond.value)}`;
    }
    return esc(JSON.stringify(cond));
}

/* --- OptionsManager React hook --- */
import { useState, useRef, useCallback } from 'react';

export function useOptionsManager(initialOptions: string[] = []) {
    const [options, setOptions] = useState<string[]>(initialOptions);
    const onChangeRef = useRef<(() => void) | null>(null);

    const setOnChange = (fn: () => void) => { onChangeRef.current = fn; };

    const addOption = useCallback((value = '') => {
        setOptions(prev => [...prev, value]);
        if (onChangeRef.current) onChangeRef.current();
    }, []);

    const removeOption = useCallback((index: number) => {
        setOptions(prev => prev.filter((_, i) => i !== index));
        if (onChangeRef.current) onChangeRef.current();
    }, []);

    const updateOption = useCallback((index: number, value: string) => {
        setOptions(prev => prev.map((v, i) => i === index ? value : v));
        if (onChangeRef.current) onChangeRef.current();
    }, []);

    const clearOptions = useCallback(() => {
        setOptions([]);
        if (onChangeRef.current) onChangeRef.current();
    }, []);

    const getOptions = useCallback(() => options.filter(o => o.trim()), [options]);

    return { options, addOption, removeOption, updateOption, clearOptions, getOptions, setOnChange };
}

/* --- Media Picker --- */
export interface MediaFile {
    path: string;
    url: string;
    name: string;
    kind: 'image' | 'video' | 'audio';
    size: number;
}

export async function fetchMediaFiles(kind?: string): Promise<MediaFile[]> {
    try {
        const resp = await fetch('/api/admin/media' + (kind ? `?kind=${kind}` : ''), {
            credentials: 'include',
        });
        if (!resp.ok) return [];
        const data = await resp.json();
        let files = data.files || [];
        if (kind) files = files.filter((f: MediaFile) => f.kind === kind);
        return files;
    } catch {
        return [];
    }
}
