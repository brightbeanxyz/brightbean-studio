# Design App

This directory contains the existing UI, kept intact in layout and visual structure, but rewired to the new runtime:

- Netlify for hosting and the API function
- Supabase Auth for login
- Supabase Postgres for data

## Commands

```powershell
npm install
npm run dev
npm run lint
npm run build
```

## Notes

- OAuth connect flows are triggered from the app UI and handled by `netlify/functions/api.ts`
- Publishing, comments, and media workflows are intentionally disabled in this read-only build
- The UI stays in place; those disabled actions now surface `Dang phat trien`
