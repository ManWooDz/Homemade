import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";
import App from "./App.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Loading from "./pages/auth/Loading.jsx";
import Login from "./pages/auth/Login.jsx";
import Register from "./pages/auth/Register.jsx";
import ResetPasswordEmail from "./pages/auth/ResetPasswordEmail.jsx";
import OtpVerify from "./pages/auth/OtpVerify.jsx";
import ResetPasswordConfirm from "./pages/auth/ResetPasswordConfirm.jsx";

createRoot(document.getElementById("root")).render(
    <StrictMode>
        <BrowserRouter>
            <AuthProvider>
                <Routes>
                    <Route path="/" element={<Loading />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/register" element={<Register />} />
                    <Route path="/reset-password" element={<ResetPasswordEmail />} />
                    <Route path="/reset-password/otp" element={<OtpVerify />} />
                    <Route path="/reset-password/confirm" element={<ResetPasswordConfirm />} />
                    <Route
                        path="/home/*"
                        element={
                            <ProtectedRoute>
                                <App />
                            </ProtectedRoute>
                        }
                    />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </AuthProvider>
        </BrowserRouter>
    </StrictMode>,
);
