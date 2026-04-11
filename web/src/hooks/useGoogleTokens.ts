import { useEffect, useRef } from 'react';
import { supabase } from '../supabaseClient.ts';
import { upsertTokens } from '../services/tokenService.ts';

/**
 * 로그인 시 provider_token/provider_refresh_token을 캡처하여 DB에 저장한다.
 * SIGNED_IN 이벤트에서만 provider_token에 접근 가능하므로
 * onAuthStateChange 콜백 내부에서 바로 캡처해야 한다.
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

        try {
          await upsertTokens(
            session.user.id,
            providerToken,
            providerRefreshToken ?? null,
            3600, // Google access token 기본 1시간
            'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar',
          );
        } catch (err) {
          console.error('Failed to save Google tokens:', err);
        }
      },
    );

    return () => subscription.unsubscribe();
  }, []);
}
