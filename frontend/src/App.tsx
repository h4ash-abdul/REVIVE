import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import Overview from './pages/Overview'
import Workspace from './pages/Workspace'
import Exceptions from './pages/Exceptions'
import Evidence from './pages/Evidence'

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/queue" element={<Workspace />} />
        <Route path="/queue/:id" element={<Workspace />} />
        <Route path="/case/:id" element={<Navigate to="/queue" replace />} />
        <Route path="/exceptions" element={<Exceptions />} />
        <Route path="/evidence" element={<Evidence />} />
      </Route>
    </Routes>
  )
}

export default App
