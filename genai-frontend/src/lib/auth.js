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
        const result = await signInAnonymously(auth);
        return result.user;
    } catch (error) {
        console.error('Anonymous sign-in error:', error);
        throw new AuthError(
            error.message,
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