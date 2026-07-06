import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { WebSocketProvider } from "@/context/WebSocketContext";
import LoginPage from "@/pages/LoginPage";
import MainApp from "@/pages/MainApp";
import SetupProfilePage from "@/pages/SetupProfilePage";
import { needsProfileSetup } from "@/utils/auth";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (needsProfileSetup(user)) return <Navigate to="/setup-profile" replace />;
  return <>{children}</>;
}

function SetupRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!needsProfileSetup(user)) return <Navigate to="/" replace />;
  return <SetupProfilePage />;
}

function LoginRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen">Loading...</div>;
  if (!user) return <LoginPage />;
  if (needsProfileSetup(user)) return <Navigate to="/setup-profile" replace />;
  return <Navigate to="/" replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/setup-profile" element={<SetupRoute />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <WebSocketProvider>
              <MainApp />
            </WebSocketProvider>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
