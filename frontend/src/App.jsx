import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { PublicLayout, AdminLayout } from './ui.jsx'
import { Landing, VacancyDetail, MyApplications, Login, Register } from './pages/Public.jsx'
import { Dashboard, Vacancies, VacancyBuilder, Applications, CandidateReview, Compare, Users, Categories, Reports, Audit, Settings } from './pages/Admin.jsx'
export default function App() {
  return <BrowserRouter><Routes>
    <Route element={<PublicLayout />}><Route path="/" element={<Landing />} /><Route path="/vacancies/:id" element={<VacancyDetail />} /><Route path="/me" element={<MyApplications />} /></Route>
    <Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} />
    <Route path="/admin" element={<AdminLayout />}><Route index element={<Dashboard />} /><Route path="vacancies" element={<Vacancies />} /><Route path="vacancies/:id" element={<VacancyBuilder />} />
      <Route path="applications" element={<Applications />} /><Route path="applications/:id" element={<CandidateReview />} /><Route path="compare" element={<Compare />} />
      <Route path="users" element={<Users />} /><Route path="categories" element={<Categories />} /><Route path="reports" element={<Reports />} /><Route path="audit" element={<Audit />} /><Route path="settings" element={<Settings />} /></Route>
  </Routes></BrowserRouter>
}
