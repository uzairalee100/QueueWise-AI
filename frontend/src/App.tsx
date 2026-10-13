import { Routes, Route } from 'react-router-dom'
import { LanguageProvider } from './context/LanguageContext'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { KioskPage } from './pages/KioskPage'
import { TrackTokenPage } from './pages/TrackTokenPage'
import { StaffDashboardPage } from './pages/StaffDashboardPage'

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
        </Route>
      </Routes>
    </LanguageProvider>
  )
}

export default App
