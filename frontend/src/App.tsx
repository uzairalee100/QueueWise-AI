import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        {/* Future routes — added per milestone:
          <Route path="/services" element={<ServiceSelection />} />
          <Route path="/token/:publicId" element={<TokenStatus />} />
          <Route path="/staff" element={<StaffDashboard />} />
          <Route path="/staff/counters" element={<CounterManagement />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/simulation" element={<SimulationLab />} />
          <Route path="/assistant" element={<AIAssistant />} />
          <Route path="/settings" element={<Settings />} />
        */}
      </Route>
    </Routes>
  )
}

export default App
