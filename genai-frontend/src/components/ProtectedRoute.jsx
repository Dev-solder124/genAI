import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import LoadingScreen from './LoadingScreen'; // <-- 1. Import the new component

export default function ProtectedRoute({ children }) {
    const { user, loading } = useAuth();

    if (loading) {
        // 2. Replace the old div with the new component
        return <LoadingScreen text="Authenticating..." />;
    }

    if (!user) {
        return <Navigate to="/login" />;
    }

    return children;
}