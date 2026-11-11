import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { SurveyProvider } from './contexts/SurveyContext'
import StartScreen from './pages/StartScreen'
import SurveyPage from './pages/SurveyPage'
import ResultsPage from './pages/ResultsPage'
import AdminLayout from './pages/admin/AdminLayout'
import AdminLogin from './pages/admin/AdminLogin'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminDirections from './pages/admin/AdminDirections'
import AdminFeatures from './pages/admin/AdminFeatures'
import AdminQuestions from './pages/admin/AdminQuestions'
import AdminSettings from './pages/admin/AdminSettings'
import AdminRecommendations from './pages/admin/AdminRecommendations'
import AdminCustom from './pages/admin/AdminCustom'
import AdminMedia from './pages/admin/AdminMedia'
import AdminUsers from './pages/admin/AdminUsers'
import AdminResponses from './pages/admin/AdminResponses'

const App: React.FC = () => {
  return (
    <SurveyProvider>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<StartScreen />} />
        <Route path="/survey" element={<SurveyPage />} />
        <Route path="/results" element={<ResultsPage />} />

        {/* Admin routes */}
        <Route path="/admin" element={<AdminLogin />} />
        <Route path="/admin/dashboard" element={<AdminLayout><AdminDashboard /></AdminLayout>} />
        <Route path="/admin/directions" element={<AdminLayout><AdminDirections /></AdminLayout>} />
        <Route path="/admin/features" element={<AdminLayout><AdminFeatures /></AdminLayout>} />
        <Route path="/admin/questions" element={<AdminLayout><AdminQuestions /></AdminLayout>} />
        <Route path="/admin/custom" element={<AdminLayout><AdminCustom /></AdminLayout>} />
        <Route path="/admin/media" element={<AdminLayout><AdminMedia /></AdminLayout>} />
        <Route path="/admin/users" element={<AdminLayout><AdminUsers /></AdminLayout>} />
        <Route path="/admin/responses" element={<AdminLayout><AdminResponses /></AdminLayout>} />
        <Route path="/admin/settings" element={<AdminLayout><AdminSettings /></AdminLayout>} />
        <Route path="/admin/recommendations" element={<AdminLayout><AdminRecommendations /></AdminLayout>} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </SurveyProvider>
  )
}

export default App
