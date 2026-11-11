import { api, adminApi, Direction, Settings, SurveyProgress, AdminUser } from './types'

export { api, adminApi }
export type { Direction, Feature, SurveyQuestion, EgeSubject, CustomField, Recommendation, SurveyProgress, Settings, AdminUser } from './types'

// Public API
export const startSurvey = () => api.post<SurveyProgress>('/start')
export const submitAnswer = (sessionId: string, questionId: number | string, answer: any) =>
  api.post('/answer', { session_id: sessionId, question_id: questionId, answer })
export const submitSurveyData = (sessionId: string, data: Record<string, any>, consent: boolean) =>
  api.post('/survey-data', { session_id: sessionId, data, consent })
export const submitFeedback = (sessionId: string, chosenFields: string[], feedbackScore?: number) =>
  api.post('/feedback', { session_id: sessionId, chosen_fields: chosenFields, feedback_score: feedbackScore })
export const getSettings = () => api.get<{ settings: Settings }>('/settings')
export const getDirections = () => api.get<{ directions: Array<{ name: string; code: string; description?: string }> }>('/directions')

// Admin API
export const adminLogin = (username: string, password: string) =>
  adminApi.post<{ ok: boolean; username: string; role: string; token: string }>('/auth/login', { username, password })
export const adminLogout = () => adminApi.post('/auth/logout')
export const getAdminMe = () => adminApi.get<AdminUser>('/auth/me')
export const getAdminSettings = () => adminApi.get<{ settings: Settings }>('/settings')
export const updateAdminSettings = (data: Partial<Settings>) =>
  adminApi.put('/settings', data)
export const getAdminDirections = () => adminApi.get<{ directions: Direction[] }>('/directions')
export const createDirection = (data: Partial<Direction>) => adminApi.post('/directions', data)
export const updateDirection = (id: number, data: Partial<Direction>) => adminApi.put(`/directions/${id}`, data)
export const deleteDirection = (id: number) => adminApi.delete(`/directions/${id}`)
export const getAdminFeatures = () => adminApi.get<{ features: any[] }>('/features')
export const createFeature = (data: any) => adminApi.post('/features', data)
export const updateFeature = (id: number, data: any) => adminApi.put(`/features/${id}`, data)
export const deleteFeature = (id: number) => adminApi.delete(`/features/${id}`)
export const getAdminQuestions = (group?: string) => adminApi.get<{ questions: any[] }>(group ? `/questions?group=${group}` : '/questions')
export const createQuestion = (data: any) => adminApi.post('/questions', data)
export const updateQuestion = (id: number, data: any) => adminApi.put(`/questions/${id}`, data)
export const deleteQuestion = (id: number) => adminApi.delete(`/questions/${id}`)
export const toggleQuestionActive = (id: number, isActive: boolean) =>
  adminApi.patch(`/questions/${id}/toggle-active`, { is_active: isActive })
export const getQuestionGroups = () => adminApi.get<{ groups: any[] }>('/question-groups')
export const getAdminUsers = () => adminApi.get<{ users: any[] }>('/users')
export const createUser = (data: { username: string; password: string }) => adminApi.post('/users', data)
export const updateUser = (id: number, data: any) => adminApi.put(`/users/${id}`, data)
export const deleteUser = (id: number, password: string) => adminApi.delete(`/users/${id}`, { data: { password } })
export const getAdminStats = () => adminApi.get<{ stats: any }>('/stats')
export const getAdminMedia = () => adminApi.get<{ files: any[] }>('/media')
export const uploadMedia = (kind: string, file: File, onUploadProgress?: (e: any) => void) => {
  const fd = new FormData()
  fd.append('file', file)
  return adminApi.post(`/media/upload/${kind}`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
}
export const deleteMedia = (path: string) => {
  const [kind, ...rest] = path.split('/')
  const filename = rest.join('/')
  return adminApi.delete(`/media/${kind}/${encodeURIComponent(filename)}`)
}
export const getRecommenderSettings = () => adminApi.get<{ settings: any }>('/recommender-settings')
export const updateRecommenderSettings = (data: any) => adminApi.put('/recommender-settings', data)
export const previewPrompt = (profile: Record<string, any>) =>
  adminApi.post('/recommender-preview-prompt', profile)

// Train / Dataset API
export const getTrainStatus = () => adminApi.get<{ runs: any[] }>('/train/status')
export const startTraining = (data: { dataset: string; model_id?: number | null }) =>
  adminApi.post('/train', data)
export const cancelTraining = (runId: number) => adminApi.post(`/train/${runId}/cancel`)
export const getTrainModels = () => adminApi.get<{ models: any[] }>('/train/models')
export const generateDataset = () => adminApi.post('/train/dataset/generate', null, { timeout: 300000 })
export const getDatasetProgress = () => adminApi.get('/train/dataset/progress')
export const getDatasetInfo = () => adminApi.get<{ synthetic: any; real: any; active_features?: number; active_directions?: number }>('/train/dataset')
export const downloadDataset = () => adminApi.get('/train/dataset/download', { responseType: 'blob' })
export const exportDbToCsv = () => adminApi.post('/responses/export-to-disk')
export const uploadRealCsv = (file: File, onUploadProgress?: (e: any) => void) => {
  const fd = new FormData()
  fd.append('file', file)
  return adminApi.post('/train/dataset/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
}

// Custom fields API
export const getCustomFields = () => adminApi.get<{ fields: any[] }>('/custom-fields')
export const createCustomField = (data: any) => adminApi.post('/custom-fields', data)
export const updateCustomField = (id: number, data: any) => adminApi.put(`/custom-fields/${id}`, data)
export const deleteCustomField = (id: number) => adminApi.delete(`/custom-fields/${id}`)

// Sessions / Responses API
export const getSessions = (limit = 50) => adminApi.get<{ sessions: any[] }>(`/sessions?limit=${limit}`)
export const downloadResponsesCsv = () => adminApi.get('/responses.csv', { responseType: 'blob' })

// Recommender metrics
export const getRecommenderMetrics = () => adminApi.get<{ metrics: any }>('/recommender-metrics')
