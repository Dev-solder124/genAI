import React, { createContext, useContext, useState, useEffect } from 'react';
import { getAuth, onAuthStateChanged } from 'firebase/auth';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        console.log('AuthContext: Setting up Firebase auth listener');
        const auth = getAuth();
        
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            console.log('AuthContext: Auth state changed -', user ? 'User logged in' : 'No user');
            setUser(user);
            setLoading(false);
        });

        return () => {
            console.log('AuthContext: Cleaning up auth listener');
            unsubscribe();
        };
    }, []);

    console.log('AuthContext render - loading:', loading, 'user:', !!user);

    return (
        <AuthContext.Provider value={{ user, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};