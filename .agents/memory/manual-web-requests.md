# Manual web requests

Loading orb sizing, 2026-11-07: use the largest native thinking-orbs size (64 px)
for page loading. Do not enlarge its canvas through CSS scaling; the user observed
blurred rendering at 2x. Keep the page indicator centered with its text below.

User clarification, 2026-11-06: automatic session restoration and initial page
loading are required. Only periodic background polling remains disabled.

Dashboard and connections load automatically when their routes mount. The
separate sensor-availability card and its unused main-API probe were subsequently
removed at the user's request. The collector health endpoint remains for setup
verification. Startup checks the real HttpOnly cookie against the server and
restores valid sessions without displaying the login form first. Do not add a
Continue existing session button or require Refresh to load a page. Never trust
localStorage for authentication.
Filter, pagination and details requests follow user clicks. Related results may
refresh after the requested operation completes.

Loading must preserve mounted cards, navigation and the previous content's layout
dimensions. Clearing resource data on query changes collapsed the dashboard and
made pagination jump upward (confirmed in the frontend, 2026-11-06). Keep the last
result and replace only pending content with a LoadingRegion; its retained content
is invisible and inert during loading. Do not remount AnalysisSessions to refresh
its history. Live checks confirmed stable scroll positions across dashboard and
session connection pages; mobile pagination stayed within the viewport. Tables
with differently sized rows can still change height when the new result arrives.

Keep session-specific warnings below the session selector: placing skipped-file
warnings above it moved controls whenever a session without warnings was selected.
Outline and selected session buttons must reserve the same border width. The
dashboard opts out of browser scroll anchoring so changes to result sections do
not pull the selector with an anchor farther down the page. Desktop live checks
confirmed identical selector coordinates between populated and empty sessions.

This decision concerns web requests, not Ubuntu capture or service supervision.
Zeek still captures traffic and systemd services still start at boot. Backend
startup configuration/migrations and per-request authentication remain intact.

Evidence: user instruction and the frontend resource/auth hooks. Recheck the
current implementation before describing which actions issue requests.
