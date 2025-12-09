import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./index.css";

import LandingPage from "./pages/LandingPage";
import RegisterPage from "./pages/RegisterPage";
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";
import AboutPage from "./pages/AboutPage";
import ContactPage from "./pages/ContactPage";
import SetRoster from "./pages/SetRoster";
import SubscriptionPage from "./pages/SubscriptionPage";
import RosterPage from "./pages/RosterPage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/set-roster" element={<SetRoster />} />
        <Route path="/roster" element={<RosterPage />} />
        <Route path="/subscription" element={<SubscriptionPage />} />
      </Routes>
    </Router>
  );
}

export default App;
