import { useState, useEffect, useCallback } from 'react'; // useCallback 추가
import { supabase } from './supabaseClient';
import { useGoogleTokens } from './hooks/useGoogleTokens';
import Login from './Login';
import Dashboard from './components/Dashboard';
import type { Session } from '@supabase/supabase-js';
import './App.css';

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  console.log('App: Component rendered.');

  // useGoogleTokens 훅은 내부에 useEffect를 가지므로 App 컴포넌트 렌더링 시 호출됨
  useGoogleTokens();
  console.log('App: useGoogleTokens hook called.');

  // Auth 상태 변경을 리스닝하는 useEffect와 getSession()을 분리하여 디버깅
  useEffect(() => {
    console.log('App useEffect: Running initial setup...'); // useEffect 시작 시점 명확히
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, newSession) => {
      console.log('App onAuthStateChange: Event:', _event, 'New Session:', newSession);
      if (newSession) {
        setSession(newSession);
      } else {
        setSession(null); // 세션이 없는 경우 명확히 처리
      }
      // onAuthStateChange는 세션이 변경될 때마다 호출되므로,
      // 최초 로딩 시점을 `getSession`으로 제어하는 것이 일반적
    });

    // 세션 로딩 로직
    const checkSession = async () => {
      console.log('App: checkSession() starting...');
      try {
        const { data: { session: currentSession }, error } = await supabase.auth.getSession();
        if (error) {
          console.error('App: getSession() error:', error);
        } else {
          console.log('App: getSession() successful. Current Session:', currentSession);
          if (currentSession) {
            setSession(currentSession);
          } else {
            setSession(null);
          }
        }
      } catch (e) {
        console.error('App: Caught exception during getSession():', e);
      } finally {
        console.log('App: checkSession() finished. Setting loading to false.');
        setLoading(false);
      }
    };

    checkSession(); // 최초 세션 확인 시작

    return () => {
      console.log('App useEffect: Unsubscribing from auth changes.');
      subscription.unsubscribe();
    };
  }, []); // 빈 의존성 배열로 컴포넌트 마운트 시 한 번만 실행

  console.log('App render: Current loading state:', loading, 'Current session state:', session);

  if (loading) {
    return (
      <div className="loading-container">
        <span className="loading-spinner">🍀</span>
      </div>
    );
  }

  if (!session) {
    return <Login />;
  }

  return <Dashboard session={session} />;
}

export default App;
