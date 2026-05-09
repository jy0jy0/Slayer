import { useEffect, useRef } from 'react';
import { supabase } from '../supabaseClient.ts';
import { upsertTokens } from '../services/tokenService.ts';

const API_BASE = '/api/v1';

/**
 * 로그인 시 provider_token/provider_refresh_token을 캡처하여 DB에 저장한다.
 * SIGNED_IN 이벤트에서만 provider_token에 접근 가능하므로
 * onAuthStateChange 콜백 내부에서 바로 캡처해야 한다.
 *
 * 두 곳에 저장:
 * 1. Supabase user_google_tokens 테이블 (프론트엔드 직접 접근용)
 * 2. 백엔드 public.users 테이블 (Gmail poller 등 서버사이드 API 호출용)
 *    - public.users 레코드가 없으면 자동 생성
 */
export function useGoogleTokens() {
  const captured = useRef(false);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event !== 'SIGNED_IN' || !session || captured.current) return;

        const providerToken = session.provider_token;
        const providerRefreshToken = session.provider_refresh_token;

        if (!providerToken) return;

        captured.current = true;

        // 1) Supabase user_google_tokens 테이블에 저장
        try {
          await upsertTokens(
            session.user.id,
            providerToken,
            providerRefreshToken ?? null,
            3600,
            'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar',
          );
        } catch (err) {
          console.error('Failed to save Google tokens to Supabase:', err);
        }

        // 2) 백엔드 public.users 테이블에 저장 (Gmail poller용)
        //    public.users 레코드가 없으면 자동 생성
        try {
          const meta = session.user.user_metadata ?? {};
          // Google ID: user_metadata.provider_id → identities[].identity_data.sub → fallback
          const googleIdentity = session.user.identities?.find(i => i.provider === 'google');
          const googleId = (
            meta.provider_id ||
            meta.sub ||
            googleIdentity?.identity_data?.sub ||
            ''
          ) as string;
          const name = (meta.full_name || meta.name || session.user.email || '') as string;

          const res = await fetch(`${API_BASE}/auth/google-token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: session.user.id,
              access_token: providerToken,
              refresh_token: providerRefreshToken ?? null,
              email: session.user.email,
              name,
              google_id: googleId,
              supabase_refresh_token: session.refresh_token,
            }),
          });
          if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            console.error('Failed to sync tokens to backend users table:', body);
          } else {
            const data = await res.json();
            console.log('Backend user sync:', data.created ? 'created new user' : 'updated existing user');
          }
        } catch (err) {
          console.error('Failed to sync tokens to backend:', err);
        }
      },
    );

    return () => subscription.unsubscribe();
  }, []);
}
