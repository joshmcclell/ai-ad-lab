# TikTok API setup

## 1. Register an app
1. Go to <https://developers.tiktok.com> → log in with your TikTok account.
2. **Manage apps → Connect an app.** Fill in name, description, category.
3. Add products:
   - **Login Kit** (OAuth)
   - **Content Posting API** (uploading/publishing)
   - **Display API** (analytics, optional for `tracking_report.py`)
4. Copy your **Client key** and **Client secret** into `.env`.
5. Add the Redirect URI exactly as in `.env` (`http://localhost:8080/callback`
   works for local auth).

## 2. Request scopes
Under your app's scopes, request:
| Scope | Used for |
|-------|----------|
| `user.info.basic` | identify the account |
| `video.upload` | inbox/draft upload (no audit needed) |
| `video.publish` | Direct Post (needs audit for public) |
| `video.list` | analytics in `tracking_report.py` |

## 3. Authorize your account
```bash
python scripts/auth_tiktok.py
```
This opens TikTok, you approve, and tokens are saved to `tokens.json`
(gitignored). Access tokens last 24h and auto-refresh; the refresh token
lasts ~1 year.

## 4. Unaudited vs audited — what you can do
| | Unaudited app | After audit |
|---|---|---|
| Inbox/draft upload (`video.upload`) | ✅ | ✅ |
| Direct Post visibility | `SELF_ONLY` only | public/friends/private |
| Users who can post | ≤ 5 / 24h | per your approved quota |
| Per-token rate limit | 6 req/min | 6 req/min |

### Getting audited (for public Direct Post)
Submit your app for review in the developer portal. You'll typically need:
a clear use-case description, a demo video of the integration, a privacy
policy URL, and compliance with the
[content-sharing guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines).
Review takes days to weeks. **For a single personal account, inbox mode often
makes audit unnecessary** — you finish the post in the app.

## 5. Key endpoints (already wired in `pipeline/tiktok_publish.py`)
- `POST /v2/post/publish/creator_info/query/` — required before Direct Post
- `POST /v2/post/publish/video/init/` — Direct Post init
- `POST /v2/post/publish/inbox/video/init/` — inbox/draft init
- `PUT <upload_url>` — upload the file bytes (single chunk < 64MB)
- `POST /v2/post/publish/status/fetch/` — poll publish status
- `POST /v2/video/list/` — analytics (Display API)

Base host: `https://open.tiktokapis.com`.
