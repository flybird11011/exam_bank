import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ImportPage } from "./pages/ImportPage";
import { PracticePage } from "./pages/PracticePage";
import { ReviewPage } from "./pages/ReviewPage";
import { WrongQuestionPage } from "./pages/WrongQuestionPage";
import { SearchPage } from "./pages/SearchPage";

const NAV_ITEMS = [
  { label: "试卷导入", path: "/" },
  { label: "题目审核", path: "/review" },
  { label: "练习", path: "/practice" },
  { label: "错题回顾", path: "/wrong-questions" },
  { label: "题库检索", path: "/search" },
] as const;

export function App() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Layout navItems={NAV_ITEMS} activePath={location.pathname} onNavigate={(path) => navigate(path)}>
      <Routes>
        <Route path="/" element={<ImportPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/practice" element={<PracticePage />} />
        <Route path="/wrong-questions" element={<WrongQuestionPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
