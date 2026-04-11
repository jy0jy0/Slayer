import { useState, useEffect, useRef } from 'react';
import { supabase } from './supabaseClient';
import { useGoogleTokens } from './hooks/useGoogleTokens';
import Login from './Login';
import Layout from './components/Layout';
import PasswordReset from './components/PasswordReset';
import type { Session } from '@supabase/supabase-js';
import './App.css';

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [showPasswordReset, setShowPasswordReset] = useState(false);

  // PASSWORD_RECOVERY가 한 번 세팅되면 SIGNED_IN이 나중에 와도 덮어쓰지 않도록 ref로 보호
  const recoveryMode = useRef(false);

  useGoogleTokens();

  useEffect(() => {
    // URL에 recovery 파라미터가 있으면 즉시 복구 모드 활성화 (PKCE 코드 교환 전에 감지)
    const hash = window.location.hash;
    const hashParams = new URLSearchParams(hash.startsWith('#') ? hash.slice(1) : '');
    if (hashParams.get('type') === 'recovery') {
      recoveryMode.current = true;
      setShowPasswordReset(true);
    }

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, newSession) => {
      if (event === 'PASSWORD_RECOVERY') {
        recoveryMode.current = true;
        setSession(newSession);
        setShowPasswordReset(true);
      } else if (event === 'SIGNED_OUT') {
        recoveryMode.current = false;
        setSession(null);
        setShowPasswordReset(false);
      } else if (newSession) {
        setSession(newSession);
        // recoveryMode 중에는 showPasswordReset을 건드리지 않음
        if (!recoveryMode.current) {
          setShowPasswordReset(false);
        }
      } else {
        setSession(null);
        setShowPasswordReset(false);
      }
    });

    const checkSession = async () => {
      try {
        const { data: { session: currentSession } } = await supabase.auth.getSession();
        if (currentSession) setSession(currentSession);
        else setSession(null);
      } finally {
        setLoading(false);
      }
    };

    checkSession();
    return () => { subscription.unsubscribe(); };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <span className="text-3xl animate-pulse">🍀</span>
      </div>
    );
  }

  if (!session) return <Login />;

  if (showPasswordReset) {
    return (
      <PasswordReset
        onDone={() => {
          recoveryMode.current = false;
          setShowPasswordReset(false);
        }}
      />
    );
  }

  return <Layout session={session} />;
}

export default App;
