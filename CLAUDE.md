# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Slayer ("취업 준비의 수호신") is a Korean-language job preparation web application. It provides a dashboard for tracking job applications, interview schedules, and expected interview questions. The project is in early stages with authentication and dashboard scaffolding in place.

## Commands

All commands run from the `web/` directory:

```bash
cd web
npm run dev      # Start Vite dev server
npm run build    # Type-check (tsc -b) then build for production
npm run lint     # ESLint across the project
npm run preview  # Preview production build locally
```

No test framework is configured yet.

## Architecture

- **Frontend**: React 19 + TypeScript, built with Vite
- **Backend**: Supabase (BaaS) — authentication and (future) database
- **Auth**: Google OAuth via Supabase, managed in `App.tsx` with `supabase.auth.onAuthStateChange`
- **Styling**: Plain CSS with dark theme (App.css, index.css)
- **Icons**: lucide-react

### Key Files

- `web/src/supabaseClient.ts` — Single shared Supabase client instance, configured via env vars
- `web/src/App.tsx` — Root component; handles auth state, conditionally renders Login or Dashboard
- `web/src/Login.tsx` — Google OAuth login UI

### Auth Flow

`App.tsx` checks the current Supabase session on mount and subscribes to auth state changes. Unauthenticated users see `Login`, authenticated users see the dashboard.

## Environment Setup

Copy `web/.env.example` to `web/.env` and fill in:
- `VITE_SUPABASE_URL` — Supabase project URL
- `VITE_SUPABASE_ANON_KEY` — Supabase anonymous/public key
