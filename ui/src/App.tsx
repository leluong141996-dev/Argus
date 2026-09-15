import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { NewRun } from "./pages/NewRun";
import { History } from "./pages/History";
import { Follow } from "./pages/Follow";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<NewRun />} />
        <Route path="/runs" element={<History />} />
        <Route path="/runs/:id" element={<Follow />} />
      </Routes>
    </Layout>
  );
}
