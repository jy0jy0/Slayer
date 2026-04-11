import type { Session } from '@supabase/supabase-js';
import { supabase } from '../supabaseClient.ts';
import GmailPanel from './gmail/GmailPanel.tsx';
import CalendarPanel from './calendar/CalendarPanel.tsx';

interface DashboardProps {
  session: Session;
}

export default function Dashboard({ session }: DashboardProps) {
  const user = session.user;
  const meta = user.user_metadata;

  return (
    <div className="dashboard-container">
      <header>
        <div className="logo">Slayer</div>
        <div className="user-profile">
          {meta.avatar_url && (
            <img src={meta.avatar_url as string} alt="avatar" className="avatar" />
          )}
          <span>{(meta.full_name as string) || user.email}</span>
          <button onClick={() => supabase.auth.signOut()}>로그아웃</button>
        </div>
      </header>

      <main>
        <h1>반갑습니다, {(meta.full_name as string) || '사용자'}님!</h1>

        <div className="panels-grid">
          <GmailPanel userId={user.id} />
          <CalendarPanel userId={user.id} />
        </div>
      </main>
    </div>
  );
}
