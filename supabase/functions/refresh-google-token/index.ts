// Supabase Edge Function: Google Access Token 갱신
// Deno runtime

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

Deno.serve(async (req) => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    // 환경변수에서 설정 읽기
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const googleClientId = Deno.env.get('GOOGLE_CLIENT_ID')!;
    const googleClientSecret = Deno.env.get('GOOGLE_CLIENT_SECRET')!;

    // JWT에서 유저 인증
    const authHeader = req.headers.get('Authorization');
    if (!authHeader) {
      return new Response(
        JSON.stringify({ error: 'Missing authorization header' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // 유저 확인을 위한 Supabase 클라이언트 (유저 JWT 사용)
    const supabaseUser = createClient(supabaseUrl, Deno.env.get('SUPABASE_ANON_KEY')!, {
      global: { headers: { Authorization: authHeader } },
    });

    const { data: { user }, error: userError } = await supabaseUser.auth.getUser();
    if (userError || !user) {
      return new Response(
        JSON.stringify({ error: 'Invalid token' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Service role 클라이언트로 DB 접근 (RLS 우회)
    const supabaseAdmin = createClient(supabaseUrl, supabaseServiceKey);

    // refresh_token 조회
    const { data: tokenRow, error: dbError } = await supabaseAdmin
      .from('user_google_tokens')
      .select('refresh_token')
      .eq('user_id', user.id)
      .single();

    if (dbError || !tokenRow?.refresh_token) {
      return new Response(
        JSON.stringify({ error: 'No refresh token found. Please re-login.' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // Google에 토큰 갱신 요청
    const googleRes = await fetch(GOOGLE_TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: googleClientId,
        client_secret: googleClientSecret,
        refresh_token: tokenRow.refresh_token,
        grant_type: 'refresh_token',
      }),
    });

    if (!googleRes.ok) {
      const errBody = await googleRes.text();
      console.error('Google token refresh failed:', errBody);
      return new Response(
        JSON.stringify({ error: 'Google token refresh failed', details: errBody }),
        { status: 502, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    const googleData = await googleRes.json() as {
      access_token: string;
      expires_in: number;
      token_type: string;
    };

    // DB 업데이트
    const tokenExpiresAt = new Date(Date.now() + googleData.expires_in * 1000).toISOString();

    const { error: updateError } = await supabaseAdmin
      .from('user_google_tokens')
      .update({
        access_token: googleData.access_token,
        token_expires_at: tokenExpiresAt,
      })
      .eq('user_id', user.id);

    if (updateError) {
      console.error('Failed to update tokens in DB:', updateError);
      // 토큰은 갱신되었으므로 일단 반환
    }

    return new Response(
      JSON.stringify({ access_token: googleData.access_token }),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      },
    );
  } catch (err) {
    console.error('Unexpected error:', err);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    );
  }
});
