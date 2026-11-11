import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
})

// Admin API with auth token
export const adminApi = axios.create({
  baseURL: '/api/admin',
  withCredentials: true,
})

adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_token')
      window.location.href = '/admin'
    }
    return Promise.reject(error)
  }
)


export type AdminUser = {
  id: number
  username: string
  role: string
  is_active: boolean
}

export type Direction = {
  id: number
  name: string
  fgos_code: string
  category?: string
  study_years: number
  ege_typical?: string
  sort_order: number
  description?: string
  key_skills_text?: string
  skill_codes: string[]
  image_path?: string
  icon?: string
  examples?: string[]
  avg_salary: number
  employment_rate: number
  is_active: boolean
}

export type Feature = {
  id: number
  code: string
  label: string
  data_type: string
  default_value?: string
  sort_order: number
  is_common: boolean
  is_active: boolean
  description?: string
  examples?: string[]
}

export type SurveyQuestion = {
  id: number | string
  group_code: string
  text: string
  image_url?: string
  feature_code?: string
  question_type: string
  options?: string[]
  threshold?: number | null
  level: number
  sort_order: number
  activation_condition?: { type: string; feature?: string; value?: number } | null
  description?: string
  examples?: string[]
  tags?: string[]
  is_active: boolean
  // Custom form fields
  is_custom?: boolean
  fields?: Array<{
    code: string
    label: string
    field_type: string
    options?: string[]
    required: boolean
  }>
  consent_text?: string
  // EGE subjects
  is_ege_select?: boolean
  is_ege?: boolean
  subjects?: Array<{ code: string; label: string }>
  // Salary
  is_salary?: boolean
}

export type QuestionGroup = {
  id: number
  code: string
  title: string
}

export type CustomField = {
  id?: number
  code: string
  label: string
  field_type: string
  options?: string[]
  required: boolean
  sort_order: number
  is_active: boolean
  description?: string
  examples?: string[]
}

export type MediaFile = {
  path: string
  name: string
  url: string
  kind: 'image' | 'video' | 'audio'
  size: number
}

export type Settings = {
  university_name?: string
  university_url?: string
  abitur_url?: string
  tagline?: string
  primary_color?: string
  primary_alpha?: number
  logo_path?: string
  hero_image_path?: string
  presenter_video_path?: string
  consent_text?: string
  custom_form_position?: string
  contact_email?: string
  support_phone?: string
}

export type TrainRun = {
  id: number
  status: string
  dataset: string | object
  metrics?: {
    top1_accuracy?: number
    top3_accuracy?: number
    top5_accuracy?: number
    macro_precision?: number
    macro_recall?: number
    macro_f1?: number
    macro_auc?: number
    per_direction?: Array<{ label: string; support: number; precision: number; recall: number; f1: number }>
    per_direction_by_f1?: Array<{ label: string; f1: number }>
  }
  error_message?: string
  total_epochs?: number
  current_epoch?: number
  top_directions_by_f1?: Array<{ label: string; f1: number }>
}

export type TrainModel = {
  id: number
  metrics?: { macro_f1?: number }
}

export type DatasetInfo = {
  synthetic: { exists: boolean; rows?: number }
  real: { exists: boolean; rows?: number }
  active_features?: number
  active_directions?: number
}

export type AdminStats = {
  stats: {
    total: number
    completed: number
    in_progress: number
    with_profile: number
    labeled: number
  }
}

export type Recommendation = {
  rank: number
  field: string
  code: string
  image: string
  description: string
  explanation: string
  key_skills: string
  /** Отображаемый процент соответствия: 0-100 (единый формат) */
  probability: number
  /** Сырая (откалиброванная) вероятность модели: 0-1 */
  raw_probability?: number
  match_level?: string
  /** 'ПОДХОДИТ' | 'ЧАСТИЧНО ПОДХОДИТ' | 'НЕ ПОДХОДИТ' */
  verdict?: string
  strengths?: string[]
  weaknesses?: string[]
  advice?: string
  summary?: string
}

export type SurveyProgress = {
  session_id: string
  progress: {
    stage: string
    current: number
    total: number
  }
  question?: SurveyQuestion
  is_ege_select?: boolean
  is_salary?: boolean
}

export type Session = {
  id: number
  status: string
  questions_asked?: string
  source?: string
  chosen_fields?: string[]
  feedback_score?: number
  recommendations?: Array<{ field: string }>
}

export type RecommenderSettings = {
  engine: 'local' | 'api'
  api_provider?: string
  api_key?: string
  api_base_url?: string
  api_model?: string
  system_prompt?: string
}

export type EgeSubject = {
  code: string
  label: string
}

export { api }
