import React, { createContext, useContext, useState, useCallback } from 'react'
import { SurveyProgress, Recommendation } from '../api/types'

interface SurveyContextType {
  sessionId: string | null
  progress: SurveyProgress | null
  currentQuestion: any
  recommendations: Recommendation[] | null
  setRecommendations: (recs: Recommendation[]) => void
  setProgress: (progress: SurveyProgress) => void
  setCurrentQuestion: (q: any) => void
  startSurvey: () => void
  nextQuestion: (data: SurveyProgress) => void
  showResults: (recs: Recommendation[]) => void
  reset: () => void
}

const SurveyContext = createContext<SurveyContextType | undefined>(undefined)

export function SurveyProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [progress, setProgressState] = useState<SurveyProgress | null>(null)
  const [currentQuestion, setCurrentQuestionState] = useState<any>(null)
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null)

  const setProgress = useCallback((p: SurveyProgress) => {
    setProgressState(p)
    if (p?.session_id) setSessionId(p.session_id)
  }, [])

  const setCurrentQuestion = useCallback((q: any) => {
    setCurrentQuestionState(q)
  }, [])

  const startSurvey = useCallback(() => {
    setSessionId(null)
    setProgressState(null)
    setCurrentQuestionState(null)
    setRecommendations(null)
  }, [])

  const nextQuestion = useCallback((data: SurveyProgress) => {
    setProgress(data)
    if (data.question) setCurrentQuestion(data.question)
  }, [])

  const showResults = useCallback((recs: Recommendation[]) => {
    setRecommendations(recs)
  }, [])

  const reset = useCallback(() => {
    setSessionId(null)
    setProgressState(null)
    setCurrentQuestionState(null)
    setRecommendations(null)
  }, [])

  return (
    <SurveyContext.Provider value={{
      sessionId, progress, currentQuestion, recommendations,
      setRecommendations: useCallback((recs: Recommendation[]) => setRecommendations(recs), []),
      setProgress, setCurrentQuestion,
      startSurvey, nextQuestion, showResults, reset,
    }}>
      {children}
    </SurveyContext.Provider>
  )
}

export function useSurvey() {
  const ctx = useContext(SurveyContext)
  if (!ctx) throw new Error('useSurvey must be used within SurveyProvider')
  return ctx
}
