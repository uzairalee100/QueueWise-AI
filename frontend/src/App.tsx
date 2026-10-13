import { Routes, Route } from 'react-router-dom'
import { LanguageProvider } from './context/LanguageContext'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { KioskPage } from './pages/KioskPage'
import { TrackTokenPage } from './pages/TrackTokenPage'
import { StaffDashboardPage } from './pages/StaffDashboardPage'
import { SimulationLabPage } from './pages/SimulationLabPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { AgentPage } from './pages/AgentPage'

function App() {
  return (
    <LanguageProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/kiosk" element={<KioskPage />} />
          <Route path="/services" element={<KioskPage />} />
          <Route path="/track" element={<TrackTokenPage />} />
          <Route path="/track/:publicId" element={<TrackTokenPage />} />
          <Route path="/token/:publicId" element={<TrackTokenPage />} />
          <Route path="/staff" element={<StaffDashboardPage />} />
          <Route path="/dashboard" element={<StaffDashboardPage />} />
          <Route path="/simulation" element={<SimulationLabPage />} />
          <Route path="/sim" element={<SimulationLabPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/agent" element={<AgentPage />} />
          <Route path="/ai" element={<AgentPage />} />
          <Route path="/advisor" element={<AgentPage />} />
        </Route>
      </Routes>
    </LanguageProvider>
  )
}

export default App
