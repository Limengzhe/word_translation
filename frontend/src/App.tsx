import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AppShell from './components/AppShell'
import HomePage from './pages/HomePage'
import DocumentEditorPage from './pages/DocumentEditorPage'
import SkillsPage from './pages/SkillsPage'

export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/doc/:docId" element={<DocumentEditorPage />} />
          <Route path="/skills" element={<SkillsPage />} />
          <Route path="/skills/:skillSetId" element={<SkillsPage />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}
