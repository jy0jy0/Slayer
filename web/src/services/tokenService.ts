import { supabase } from '../supabaseClient.ts';
import type { GoogleTokenRow } from '../types/google.ts';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string;
console.log('tokenService: SUPABASE_URL loaded:', SUPABASE_URL); // DEBUG LOG

export async function upsertTokens(
  userId: string,
  accessToken: string,
  refreshToken: string | null,
  expiresIn: number,
  scopes: string,
): Promise<void> {
  const tokenExpiresAt = new Date(Date.now() + expiresIn * 1000).toISOString();

  const row: Partial<GoogleTokenRow> = {
    user_id: userId,
    access_token: accessToken,
    token_expires_at: tokenExpiresAt,
    scopes,
  };

  if (refreshToken) {
    row.refresh_token = refreshToken;
  }

  const { error } = await supabase
    .from('user_google_tokens')
    .upsert(row, { onConflict: 'user_id' });

  if (error) {
    console.error('tokenService: Failed to upsert tokens:', error); // DEBUG LOG
    throw error;
  }
  console.log('tokenService: Tokens upserted successfully for userId:', userId); // DEBUG LOG
}

export async function getStoredTokens(userId: string): Promise<GoogleTokenRow | null> {
  console.log('tokenService: Attempting to get stored tokens for userId:', userId); // DEBUG LOG
  const { data, error } = await supabase
    .from('user_google_tokens')
    .select('*')
    .eq('user_id', userId)
    .single();

  if (error) {
    if (error.code === 'PGRST116') {
      console.log('tokenService: No stored tokens found for userId:', userId); // DEBUG LOG
      return null;
    }
    console.error('tokenService: Failed to get tokens:', JSON.stringify(error, null, 2)); // DEBUG LOG
    throw error;
  }
  console.log('tokenService: Stored tokens retrieved:', data); // DEBUG LOG
  return data as GoogleTokenRow;
}

export function isTokenExpired(tokenRow: GoogleTokenRow): boolean {
  const expiresAt = new Date(tokenRow.token_expires_at).getTime();
  const isExpired = Date.now() > expiresAt - 5 * 60 * 1000;
  console.log('tokenService: Token expires at:', tokenRow.token_expires_at, 'Is expired (or expiring soon):', isExpired); // DEBUG LOG
  return isExpired;
}

export async function refreshAccessToken(): Promise<string> {
  console.log('tokenService: Attempting to refresh access token via Edge Function.'); // DEBUG LOG
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    console.error('tokenService: No active session for refreshAccessToken.'); // DEBUG LOG
    throw new Error('No active session');
  }
  console.log('tokenService: Session found for refreshAccessToken, calling Edge Function URL:', `${SUPABASE_URL}/functions/v1/refresh-google-token`); // DEBUG LOG

  const response = await fetch(
    `${SUPABASE_URL}/functions/v1/refresh-google-token`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${session.access_token}`,
        'Content-Type': 'application/json',
      },
    },
  );

  if (!response.ok) {
    const body = await response.text();
    console.error('tokenService: Edge Function call failed. Status:', response.status, 'Body:', body); // DEBUG LOG
    throw new Error(`Token refresh failed: ${body}`);
  }

  const { access_token } = await response.json() as { access_token: string };
  console.log('tokenService: Access token refreshed successfully. New token start:', access_token.substring(0, 10)); // DEBUG LOG
  return access_token;
}

export async function getValidAccessToken(userId: string): Promise<string> {
  console.log('tokenService: getValidAccessToken called for userId:', userId); // DEBUG LOG
  const tokenRow = await getStoredTokens(userId);
  if (!tokenRow) {
    console.error('tokenService: No Google tokens found in DB. User needs to re-login.'); // DEBUG LOG
    throw new Error('No Google tokens found. Please re-login.');
  }

  if (!isTokenExpired(tokenRow)) {
    console.log('tokenService: Stored token is valid and not expired.'); // DEBUG LOG
    return tokenRow.access_token;
  }

  console.log('tokenService: Stored token is expired or expiring soon, attempting refresh.'); // DEBUG LOG
  const newAccessToken = await refreshAccessToken();
  return newAccessToken;
}