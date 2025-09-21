import { initializeApp } from 'firebase/app';
import { getAuth, signInWithPopup, GoogleAuthProvider, signInAnonymously } from 'firebase/auth';

const firebaseConfig = {
    apiKey: "AIzaSyAd8F8yhZ_0U6Z3cYVeWK7UZt7i6D0ewhY",
    authDomain: "genai-bot-kdf.firebaseapp.com",
    projectId: "genai-bot-kdf",
    storageBucket: "genai-bot-kdf.appspot.com",
    messagingSenderId: "922976482476",
    appId: "1:922976482476:web:80f27ef69365e72b90db09"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export const signInWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(auth, provider);
    const idToken = await result.user.getIdToken();
    // In a real app, you'd send this token to your backend to verify and create a session.
    console.log("Google ID Token:", idToken);
    return result.user;
};

export const signInAsGuest = async () => {
    const result = await signInAnonymously(auth);
    const idToken = await result.user.getIdToken();
    // In a real app, you'd send this token to your backend.
    console.log("Guest ID Token:", idToken);
    return result.user;
};

export const signOut = () => {
    return auth.signOut();
};

export const onAuthStateChanged = (callback) => {
    return auth.onAuthStateChanged(callback);
};
