# Manual web requests

Global filter feedback, user clarification 2026-11-14: filter triggers must show
when non-default filters apply, even with their popovers closed. Use FilterButton
for switch groups (active count and primary tint) and the shared primary tint on
ProtocolSelect for selected protocols. All protocols is the inactive default.
Reserve the count slot so enabling filters never changes trigger dimensions.
Disabled controls do not indicate active filters for a view they do not filter.

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
Pagination page-jump forms use a nonmodal Popover, not a modal DropdownMenu.
The modal menu locked the body scroll, shifting content and displacing the sticky
header. On 2026-11-09 live checks confirmed unchanged header coordinates, content
position and scroll position when opening the nonmodal page chooser. Session
selection uses a bounded searchable dropdown displaying timestamps, keeping Zeek
UIDs in the records table; the default session-record page size is 20.

Finding details open in the shared Modal component rather than an inline card.
Do not scroll the page to show details. On 2026-11-09 desktop checks confirmed
unchanged page scroll after closing and focus restored to the Details button;
the mobile dialog stayed within the viewport with internal table scrolling.
Finding status menus also use nonmodal DropdownMenu to avoid scroll locking.
The dashboard replaces severity with row checkboxes; selection is cleared when
changing page/page size or archiving. Bulk status updates use one transaction,
reject unavailable/archived findings without partial changes, and cap at 500 IDs.
The Zeek traffic browser has no selection or stored-record reanalysis action.
On 2026-11-09 the unused POST analysis-session route and stored-analysis branch
were removed; sensor ingestion still uses the shared analysis service. Historical
stored-session metadata remains readable. Traffic Details use the shared Modal,
showing the Zeek UID and the existing DNS/HTTP/TLS context rather than expanding
a table row. Live desktop/mobile checks covered TLS and DNS records.
All-data has Traffic records and Analysis sessions views. Its Filters popover
contains Alerts only and Hide current data switches. Alerts only means traffic
with AI findings (deduplicated through linked/direct evidence), or sessions with
new_alerts_detected > 0. The archived_only API flag filters rows and totals on the server,
and overrides include_archived when true. Reset page offsets and selected session
when changing that scope. Successful archive/restore operations clear resource
caches so navigating between routes does not reuse pre-archive membership.
On 2026-11-14 the separate AllAlerts table was removed. TrafficHeaders/TrafficCells
now share traffic columns between the traffic browser and dashboard findings;
the latter additionally keeps selection, classifier score and review status.
Protocol options come from stored records, with multi-selection; All clears
individual choices and choosing an individual protocol clears All. Protocols
apply to traffic, not the session history. The all-data result region reserves
viewport space to prevent empty results clamping scroll and moving controls.
The dashboard findings table reuses ProtocolSelect for active findings. Its
server-side protocol filter covers direct and linked evidence and filters both
rows and totals. Changing protocols resets pagination and selected findings;
overview metrics remain global. Live checks covered UDP with zero results,
combined TCP/UDP, All, unchanged control positions and the mobile dropdown.

After adding/removing frontend dependencies with Vite already running, verify the
development page as well as the production build. On 2026-11-09 a blank root and
a 404 for the prebundled Radix popover dependency were resolved by restarting only
Vite with `npm run dev -- --force`, then reloading after optimization completed.
Live verification confirmed the dashboard rendered again. Do not diagnose this
specific dependency-cache failure as an authentication or backend problem.

Zeek still captures traffic and systemd services still start at boot. Backend
startup configuration/migrations and per-request authentication remain intact.

Evidence: user instruction and the frontend resource/auth hooks. Recheck the
current implementation before describing which actions issue requests.
