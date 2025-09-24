// Updated auth.js - Add better error handling for anonymous users
import { initializeApp } from 'firebase/app';
import { getAuth, signInWithPopup, GoogleAuthProvider, signInAnonymously, signOut as firebaseSignOut } from 'firebase/auth';

const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    appId: import.meta.env.VITE_FIREBASE_APP_ID
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

class AuthError extends Error {
    constructor(message, code) {
        super(message);
        this.code = code;
    }
}

export const signInWithGoogle = async () => {
    try {
        const provider = new GoogleAuthProvider();
        provider.setCustomParameters({
            prompt: 'select_account'
        });
        const result = await signInWithPopup(auth, provider);
        
        // Wait a bit for token to be ready
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        return result.user;
    } catch (error) {
        console.error('Google sign-in error:', error);
        throw new AuthError(
            error.message,
            error.code || 'auth/google-signin-failed'
        );
    }
};

export const signInAsGuest = async () => {
    try {
        console.log('Starting anonymous sign-in...');
        const result = await signInAnonymously(auth);
        console.log('Anonymous sign-in successful:', result.user.uid);
        
        // Wait for token to be properly generated and cached
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Verify token is available
        const token = await result.user.getIdToken();
        console.log('Token generated successfully for anonymous user');
        
        return result.user;
    } catch (error) {
        console.error('Anonymous sign-in error:', error);
        throw new AuthError(
            `Anonymous sign-in failed: ${error.message}`,
            error.code || 'auth/anonymous-signin-failed'
        );
    }
};

export const signOut = async () => {
    try {
        await firebaseSignOut(auth);
    } catch (error) {
        console.error('Sign-out error:', error);
        throw new AuthError(
            error.message,
            error.code || 'auth/signout-failed'
        );
    }
};

export const refreshToken = async () => {
    const user = auth.currentUser;
    if (!user) throw new AuthError('No user signed in', 'auth/no-user');
    return user.getIdToken(true);
};

// Add a helper function to ensure token is ready
export const ensureTokenReady = async (maxRetries = 3) => {
    const user = auth.currentUser;
    if (!user) throw new AuthError('No user signed in', 'auth/no-user');
    
    for (let i = 0; i < maxRetries; i++) {
        try {
            const token = await user.getIdToken(false);
            if (token && token.length > 0) {
                console.log('Token ready:', token.substring(0, 20) + '...');
                return token;
            }
        } catch (error) {
            console.warn(`Token attempt ${i + 1} failed:`, error);
            if (i === maxRetries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
        }
    }
    
    throw new AuthError('Token not ready after retries', 'auth/token-not-ready');
};