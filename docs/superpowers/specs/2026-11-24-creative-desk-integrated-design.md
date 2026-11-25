# Creative Desk inside Fhmny — design for review

**Status:** historical proposal, superseded by [the standalone Desk design](2026-11-25-standalone-desk-design.md) after the owner clarified that only `desk/` is in scope. **Date:** 2026-11-24, updated 2026-11-25.

## Intent and product boundary

Creative Desk is a section of the Fhmny learning platform for teachers to request image designs or video edits, discuss each request with a designer, and review delivery. Admins create multiple designer accounts, choose the designer responsible for each teacher, and set separate image and video limits. The English-course and hoodie projects remain separate websites.

The UI source lives in `desk/frontend` as a React app served under the Fhmny platform's `/desk` path, linked from the existing `client` navigation. A new Python FastAPI service in `desk/backend` owns Desk requests, messages, assignments and counters in its own database. The existing Laravel `server` remains the sole owner of user accounts and login; it issues a short-lived signed Desk access token. It does not store Desk work or media. The attendance app is not involved.

## Approaches considered

1. **Chosen:** a React Desk app on the same platform origin at `/desk`, a separate FastAPI service, and a small identity bridge in Laravel. This meets the owner's Python choice and keeps the experience inside the platform.
2. A Laravel Desk module would make identity simpler but violates the Python backend choice.
3. A standalone Desk website would avoid an identity bridge but violates the new request for an integrated platform experience.

## First release workflow

1. Admin creates designer accounts and teacher access, chooses one primary designer for each teacher, and sets `image_limit` and `video_limit` independently (example: 5 images, 2 videos). Admin may reassign a teacher or an individual request; each action is audited.
2. Teacher opens Desk inside the platform, sees designer name and separate available/reserved/completed counts, and submits an image or video request with title, detailed brief, optional desired date, and any useful HTTPS reference links (Drive, YouTube, TikTok, Facebook, Instagram, or another website). Desk stores URLs and text only.
3. Assigned designer and teacher exchange messages inside that request. Either can ask questions; admin can read and join the conversation. Messages are ordered and attributed. New messages show an unread indicator and timestamp; polling is sufficient for the first release.
4. Admin or assigned designer accepts a request according to admin-configured rules; acceptance atomically reserves one slot of its type. An unaccepted request does not consume a slot. If the limit is exhausted, the request waits for admin action and cannot be accepted.
5. Designer posts progress and a Drive link to a draft, then marks the request **ready for review**. Teacher can ask for revisions on the same request. Each revision is recorded in the request timeline and does not consume another slot.
6. Designer posts the final Drive link. Teacher approves; the reserved image or video slot becomes completed exactly once. Admin can resolve a stalled/disputed request with a logged reason. Teacher, designer and admin see the same completion state.
7. Teacher can cancel before acceptance. After acceptance, cancellation goes to admin, who releases the reserved slot if canceled. Completed requests remain in history.

## Roles and access

| Role | Access |
|---|---|
| Teacher | Own Desk profile, limits, requests, chat, references, review, final Drive links. |
| Designer | Assigned teachers and their requests only; chat, status, draft/final links. Cannot change limits or approve their own work. |
| Admin | Create/disable designers, grant teacher access, assign/reassign, set limits, inspect all requests/chats, resolve cancellation/disputes, view audit. |

Laravel creates, disables and authenticates designer accounts through admin-only endpoints and a new `designer` role. Desk admin screens call those endpoints for account management; FastAPI stores only platform user IDs, teacher profiles, assignments and Desk data. A Laravel endpoint available to authenticated users issues a short-lived token containing platform user ID, role, Fhmny tenant, issuer, audience and expiry. FastAPI validates signature, issuer, audience, tenant and expiry on every request, then applies its own teacher assignment checks. Keep the signing key in environment configuration, separate from the Laravel `APP_KEY`. The Desk frontend obtains and refreshes this token through Laravel before calling FastAPI. Designer navigation is added to the platform `client`; its link opens `/desk`. Desk is initially available to the Fhmny tenant; Masark and public designer signup are outside the first release.

## Limits and state

The admin sets two integer totals on each teacher: image and video. Each accepted request reserves exactly one slot matching its type. Approval converts reservation to completion. Revisions cost no additional slot. Available = total − reserved − completed. The admin can increase limits; a decrease cannot go below reserved + completed. No monthly expiry is assumed. Concurrent acceptances and approvals must be transactional and idempotent. Designers cannot mark their own output approved.

States: draft → submitted → needs clarification → accepted/in progress → ready for review → revision requested or approved/completed. Canceled/declined are terminal and release a reservation if one exists. Admin reassignment does not affect the teacher's limits or request history.

## Files, Drive and privacy

No image or video bytes are sent to the learning platform server, the Python Desk service, or either database. The first release stores text messages and URLs in the Python Desk database. Teachers may provide reference URLs from any HTTPS website; designers provide Google Drive URLs for drafts and final delivery. The application validates URL syntax, displays the original domain, and does not fetch arbitrary reference URLs server-side. The assigned designer, teacher and admin can see links for their requests; other designers cannot. The designer manages Drive permissions and confirms the teacher can open the final link. No Drive API integration or file-upload button is part of this release.

## Project layout and ownership

```text
D:/vs2/fhmny/
  client/                    existing React UI; Desk navigation entry
  server/                    existing Laravel auth; designer identity/token bridge
  desk/
    backend/                 Python FastAPI, Desk data model, migrations, tests
    frontend/                React Desk app served at /desk on the platform origin
    docs/                    product rules, API, identity bridge, setup, release
```

The `desk/frontend` build is published under `/desk` on the same origin as the platform. Hosting must route `/desk/*` to that build and preserve `/desk` on refresh; the existing `client` adds a navigation link. Both apps share the existing login through a Laravel endpoint on the platform origin. The Python service may run independently behind a platform reverse proxy at `/api/v1/desk`; this avoids cross-origin token handling. Deployment routing and the exact bridge contract must be verified against the current platform before implementation.

## API and data

FastAPI `/api/v1/desk`: `GET /me`, teacher counts/profile, admin designer list/create/disable and teacher assignment/limits, request create/list/detail/submit/accept/reassign/cancel, message list/create, draft/final link create, ready-for-review, revision, approval, and audit list for admin. List endpoints paginate. All mutations verify role and request ownership/assignment server-side.

Desk database records: platform identities (`platform_user_id`, role snapshot), teacher profile/brand/social links, teacher-designer assignment, per-teacher image/video totals, requests (`teacher`, `designer`, `type`, `status`, `brief`, dates), messages, external links/versions, immutable limit events, and audit events. The signed token is authentication only; Desk authorization reads current assignment and limits from its own database. The token expires quickly; disabled accounts are rejected on renewal through Laravel.

## Acceptance and verification

- Admin can add two designers and assign different teachers to each. Designer A cannot read Designer B's requests or teacher details.
- A teacher with 5 image slots and 2 video slots sees the two counts separately. Five approved image requests leave zero image slots while video slots remain unchanged.
- Designer messages and teacher replies appear in the same request thread; admin can see the conversation. Unread state updates for each party.
- `ready for review` does not count as completed. Approval counts once. A revision keeps the same reserved slot. Cancellation releases it.
- Teacher reference links may point to any HTTPS domain; designer draft/final links point to Google Drive. No media upload occurs through Fhmny's API or the Python service, and no media binary columns or upload endpoints exist in the first release.
- Existing student, educator, and admin flows continue to work. Designers cannot access learning-platform admin or teacher data outside Desk.

## Open product policy for owner review

The draft assumes one primary designer per teacher and one slot per image or video request. A video can vary greatly in scope, so duration/complexity limits and included revisions must be published before selling a package. The initial website can operate with admin-managed scope and manual payments. Prices, service-level commitments, automatic Drive upload, and external marketplace access are outside this release.
