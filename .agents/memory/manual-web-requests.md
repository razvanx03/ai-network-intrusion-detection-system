# Manual web requests

Loading orb sizing, 2026-11-07: use the largest native thinking-orbs size (64 px)
for page loading. Do not enlarge its canvas through CSS scaling; the user observed
blurred rendering at 2x. Keep the page indicator centered with its text below.

User clarification, 2026-11-06: automatic session restoration and initial page
loading are required. Independent periodic data/history polling remains disabled.

Dashboard and connections load automatically when their routes mount. The
separate sensor-availability card and its unused main-API probe were subsequently
removed at the user's request. The collector health endpoint remains for setup
verification. On 2026-11-07 the user authorized a compact Ubuntu status indicator:
one initial availability probe, a manual refresh, and one silent probe every minute
after the preceding check completes. A later explicit request on the same date
authorizes a follow-up fetch-and-analyze whenever the agent is available, including
the initial/manual check. Schedule the next minute after the whole cycle completes.
The probe itself reads no logs; only a successful availability result triggers the
analysis. Sample mode and failed/unknown host states do not trigger it. A shared
layout coordinator coalesces manual/automatic sensor analysis and invalidates
mounted data resources after success or partial failure. Background refresh retains
visible data; failed background analysis is shown separately from agent status.
Stop the timer on logout/unmount. Other tabs/processes are guarded by the backend's
single-running-session constraint. Status alone does not verify Zeek capture.
If HTTP fails, a bounded ICMP probe distinguishes agent-only unavailability from
Ubuntu/network unreachability; unavailable probe tools/permissions return unknown.
Never label missing ICMP/HTTP replies as proof that the VM is powered off. Windows
uses .NET Ping via a hidden, time-bounded PowerShell process to avoid localized
ping output and Uvicorn reload-loop async subprocess limitations.
Remote sensor auth errors must not become a 401 that logs out the dashboard user.
Startup checks the real HttpOnly cookie against the server and
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
