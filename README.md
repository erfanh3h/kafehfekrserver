# Cafe Fekr — REST API Server (`kafehfekrserver`)

The **REST API, authentication, social community, player economy, and match discovery service** for **Cafe Fekr (کافه فکر)**. It manages user registration via SMS OTP (IPPanel), profile personalization, 20 collectible avatar frames, friend networks, clan governance and friendly challenges, direct messaging, in-game notifications, **live spectatable match discovery**, real-time bridging to the Socket.IO game backend, store transactions (CafeBazaar & Myket), global leaderboards, automated MongoDB backups, and administrative operations.

---

## 1. High-Level Summary

| Property | Value |
|---|---|
| **Primary Stack** | Python 3.12, `FastAPI`, `uvicorn`, `pymongo`, `passlib`, `python-jose`, `ippanel`, `requests` |
| **Default Port** | `5001` (`PORT=5001`, `HOST=0.0.0.0`) |
| **Protocol** | HTTP / HTTPS (RESTful JSON / Form Data) |
| **Authentication** | Bearer JWT (HS256) with Device ID verification |
| **SMS Gateway** | IPPanel API (Pattern: `ccnmmdqhf3hb0h7`, Originator: `+983000505`) with bot account bypass |
| **Database** | MongoDB (`KafehFekrDB`) |
| **Realtime Bridge** | `RealtimeBridge` (Async HTTP-to-Socket.IO webhook events to port 5000) |
| **Mounted Routers** | `auth`, `user`, `social`, `clans`, `messages`, `notifications`, `spectator`, `general`, `admin` |
| **Static Assets** | 20 Avatar Frame PNGs mounted at `/static/avatar_frames/` |

---

## 2. Directory Structure

```
kafehfekrserver/
├── main.py                     # Entry point: FastAPI app, router mounting, backup timer
├── Dockerfile                  # Container definition (Python 3.12-slim, non-root user)
├── requirements.txt            # Python dependencies (fastapi, pymongo, ippanel, etc.)
├── .dockerignore / .gitignore   # Ignored files
├── Backup/                     # Persistent local database backup storage
├── static/                     # Static media assets
│   └── avatar_frames/          # 20 Collectible avatar frame overlays (1.png .. 20.png)
│
├── Commons/                    # Utility functions and shared constants
│   ├── app_consts.py           # Application-wide constants (admin_token)
│   └── static_functions.py     # Phone sanitization, bot phone recognition, password helpers
│
├── Entities/                   # Business logic and external service integrations
│   ├── Api_Services/           # Business handlers for auth, user queries, games admin
│   │   ├── auth.py             # User lookup, user creation, profile completion, realtime sync
│   │   ├── game.py             # Game history inspection and admin cleanup
│   │   ├── user.py             # Profile data, avatar frames, coin balance, leaderboards, IAP
│   │   ├── __init__.py         # Token extractor, get_current_user dependency, app config
│   │   └── social/             # Social subsystem business logic
│   │       ├── clans.py        # Clan creation, directory, roster, friendly challenges lifecycle
│   │       ├── friends.py      # Friend requests, accept/reject, suggestions, blocks
│   │       ├── invitations.py  # Match and lobby invitation routing
│   │       ├── leaderboards.py # Global, game-specific, and clan leaderboards
│   │       ├── messages.py     # Direct messaging & clan chat management
│   │       ├── moderation.py   # Player blocking and reporting
│   │       ├── notifications.py# Notification listing and preferences
│   │       ├── profiles.py     # Public player profile inspection & cosmetic updates
│   │       ├── realtime_bridge.py # HTTP webhook bridge to Socket.IO backend on port 5000
│   │       ├── security.py     # Social input validation and rate limiting
│   │       └── spectator.py    # Live games discovery, query filters, and privacy enforcement
│   ├── Database/               # MongoDB collections and automated backup logic
│   │   ├── backup.py           # Hourly automated DB backup scheduler
│   │   ├── config_collection.py# System configuration (versioning, queue toggles)
│   │   ├── game_history_collection.py      # Individual round records
│   │   ├── game_play_history_collection.py # Match series records
│   │   ├── purchases_collection.py         # IAP transaction history
│   │   ├── users_collection.py             # User profile, wallet, session, privacy, profile_frame
│   │   ├── user_history_collection.py      # Aggregated per-game user stats
│   │   ├── __init__.py         # Database connection and collection initialization
│   │   └── social/             # Social collections
│   │       ├── clans_collection.py         # Clans, memberships, join requests, challenges
│   │       ├── clan_messages_collection.py # Clan chat logs
│   │       ├── direct_messages_collection.py # Private player-to-player DMs
│   │       ├── friends_collection.py       # Friendships, requests, blocks
│   │       ├── invitations_collection.py   # Match invitations
│   │       ├── notifications_collection.py # System & player notification events
│   │       ├── presence_collection.py      # Real-time presence records
│   │       └── reports_collection.py       # Moderation tickets
│   ├── Games/                  # Shared game types enum (25 games)
│   │   └── game_types.py
│   ├── Network_Exeptions/      # Standardized HTTP error responses (401, 403, 422)
│   └── Security/               # Token creation, verification, and SMS OTP panel
│       ├── sms_panel.py        # OTP generation, delivery, memory store, expiration cleanup
│       └── __init__.py         # JWT token issuance and dependency extractors
│
└── Routers/                    # FastAPI route modules
    ├── admin_router.py         # Administrative endpoints (/admin/*)
    ├── auth_router.py          # Authentication and login endpoints (/enter, /code, /complete-data)
    ├── clan_router.py          # Clan governance, roster, and challenges (/clans/*)
    ├── general_router.py       # Configuration, leaderboard, store, and reward endpoints
    ├── messaging_router.py     # Direct messages and clan chat history (/messages/*)
    ├── notification_router.py  # In-game notification management (/notifications/*)
    ├── social_router.py        # Friends, profile customization, blocks, reports (/social/*)
    ├── spectator_router.py     # Live games discovery & match summaries (/spectator/*)
    └── user_router.py          # User profile, avatar frames, match history, cosmetic endpoints
```

---

## 3. Comprehensive API Endpoints Reference

### 3.1 Authentication Endpoints (`Routers/auth_router.py`)

| Method | Endpoint | Auth | Parameters | Description |
|---|---|---|---|---|
| `POST` | `/enter` | None | `phone` (Form) | Requests an SMS OTP. If phone is a registered test/bot phone (e.g. `09131234567`, `09000000000`), SMS sending is suppressed and code `1234` is staged in memory. |
| `POST` | `/code` | None | `phone`, `code`, `device_id` (Form) | Validates OTP. Returns existing user document or registers a new user, and returns an HS256 JWT access token. |
| `POST` | `/complete-data` | JWT | `username`, `rep_id` (optional, Form) | Completes profile registration with a chosen display name. If `rep_id` is supplied, credits +30 coins to the referring player. |

---

### 3.2 User & Profile Endpoints (`Routers/user_router.py`)

| Method | Endpoint | Auth | Parameters | Description |
|---|---|---|---|---|
| `GET` | `/my-data` | JWT | `Authorization: <token>` | Returns the authenticated user's complete profile document. |
| `GET` | `/my-history` | JWT | `Authorization: <token>` | Returns user's win/loss/draw records grouped per board game and mode. |
| `GET` | `/my-game-history` | JWT | `Authorization: <token>` | Returns the user's last 50 matches with round-by-round results and opponent details. |
| `GET` | `/user-data/{user_id}` | None | `user_id` (Path) | Returns public profile data and aggregate history of a specific user. |
| `POST` | `/update-image` | JWT | `image` (int, Form) | Updates the player's active avatar icon. |
| `POST` | `/update-avatar-frame` | JWT | `frame_id` (int, Form / JSON) | Equips one of the 20 collectible avatar frames (`1..20`). |
| `POST` | `/update-username` | JWT | `username` (Form) | Changes the player's display username. |
| `POST` | `/check_match_allow` | JWT | `version` (Query) | Verifies whether the client version is permitted to queue into matches. |

---

### 3.3 Live Spectator Discovery Endpoints (`Routers/spectator_router.py` & `social_router.py`)

| Method | Endpoint | Auth | Parameters | Description |
|---|---|---|---|---|
| `GET` | `/spectator/live-games` | JWT | `game_type`, `player_id`, `clan_id`, `visibility` (`all`/`friends`/`clan`), `page`, `limit` | Returns list of currently active watchable matches, respecting mutual blocks and player privacy. |
| `GET` | `/spectator/live-games/{game_id}` | JWT | `game_id` (Path) | Inspects watchability and returns sanitized match summary (game type, current players, spectator count). |
| `GET` | `/social/live-games` | JWT | (Same as above) | Alias under social prefix for Godot client compatibility. |

---

### 3.4 Social & Friends Endpoints (`Routers/social_router.py`)

| Method | Endpoint | Auth | Parameters | Description |
|---|---|---|---|---|
| `GET` | `/social/overview` | JWT | Header | Consolidated social dashboard (friends, friend requests, clan data, active game invites, unread counts). |
| `GET` | `/social/friends` | JWT | Header | List of accepted friends with online presence status. |
| `GET` | `/social/friends/requests` | JWT | Header | List of incoming and outgoing pending friend requests. |
| `GET` | `/social/friends/discover` | JWT | `limit` (Query) | Suggested friends based on recently played opponents and mutual connections. |
| `GET` | `/social/players/search` | JWT | `q`, `limit` (Query) | Search players by username or ID (automatically filters bots). |
| `POST` | `/social/friends/request` | JWT | `target_user_id`, `message` (JSON/Form) | Sends a friend request. |
| `POST` | `/social/friends/respond` | JWT | `request_id`, `action` (`accept`/`reject`) | Responds to an incoming friend request. |
| `POST` | `/social/friends/remove` | JWT | `friend_id` (JSON/Form) | Removes a player from friends. |
| `GET` | `/social/profile/{target_id}` | JWT | `target_id` (Path) | Detailed public profile with level, frame, badge, title, clan, and stats. |
| `POST` | `/social/profile/customize` | JWT | `profile_frame`, `profile_title`, `profile_badge`, `status_message`, `privacy` | Updates player cosmetics and social privacy flags (`allow_friend_requests`, `allow_dms`, `show_last_seen`, `show_current_game`, `show_match_history`, `allow_spectators`). |
| `GET` | `/social/leaderboards` | JWT | `board_type`, `game_type`, `clan_id`, `limit` | Leaderboards for `global_score`, `game_score`, and `clan_score`. |
| `GET` | `/social/invitations` | JWT | Header | Lists active incoming game and lobby invitations. |
| `POST` | `/social/invitations/send` | JWT | `to_user_id`, `game_type`, `invite_mode`, `lobby_id`, `lobby_password`, `player_count` | Sends an invitation to an open lobby or direct 1v1 match. |
| `POST` | `/social/invitations/respond`| JWT | `invite_id`, `action` (`accept`/`reject`) | Accepts or rejects a game invitation. |
| `GET` | `/social/blocks` | JWT | Header | Lists players blocked by the user. |
| `POST` | `/social/block` | JWT | `target_user_id`, `reason` | Blocks a player (prevents DMs, invites, matching, and spectating). |
| `POST` | `/social/unblock` | JWT | `target_user_id` | Unblocks a previously blocked player. |
| `POST` | `/social/report` | JWT | `target_user_id`, `reason`, `target_type`, `details` | Submits a player report ticket for moderation. |

---

### 3.5 Clans Endpoints & Friendly Challenges (`Routers/clan_router.py`)

| Method | Endpoint | Auth | Parameters | Description |
|---|---|---|---|---|
| `GET` | `/clans/search` | JWT | `q`, `join_type`, `language`, `only_joinable`, `sort_by`, `skip`, `limit` | Clan directory search with sorting and filters. |
| `GET` | `/clans/my` | JWT | Header | Retrieves current user's clan details, member roster, roles, and statistics. |
| `GET` | `/clans/invitations` | JWT | Header | Lists invitations received by the player to join clans. |
| `POST` | `/clans/create` | JWT | `name`, `tag`, `emblem_id`, `description`, `language`, `join_type`, `min_score`, `min_level` | Creates a new clan (free of charge, max 1 created clan per user, Persian/alphanumeric tags `#TAG`). |
| `POST` | `/clans/join` | JWT | `clan_id`, `message` | Instantly joins an open clan or submits a join request to an invite-only clan. |
| `POST` | `/clans/requests/respond` | JWT | `request_id`, `action` (`accept`/`reject`) | Clan leaders/elders approve or reject pending join requests. |
| `POST` | `/clans/invite` | JWT | `target_user_id` | Invites a player to join the clan. |
| `POST` | `/clans/invitations/respond` | JWT | `invite_id`, `action` (`accept`/`reject`) | Player accepts or rejects a clan invitation. |
| `POST` | `/clans/leave` | JWT | Header | Leaves the current clan (automatically reassigns leadership or disbands if last member). |
| `POST` | `/clans/kick` | JWT | `target_user_id` | Kicks a member from the clan (strictly enforces role hierarchy). |
| `POST` | `/clans/role` | JWT | `target_user_id`, `new_role` (`member`/`elder`/`co_leader`) | Promotes or demotes a clan member. |
| `POST` | `/clans/transfer-leadership` | JWT | `new_leader_id` | Transfers clan ownership to another member. |
| `POST` | `/clans/disband` | JWT | Header | Disbands the clan (Leader only). |
| `POST` | `/clans/settings` | JWT | Clan settings dictionary | Updates emblem, description, join type, minimum requirements. |
| `POST` | `/clans/friendly-challenge` | JWT | `game_type`, `player_count` (2–4) | Creates an open friendly challenge inside the clan for any of the 25 games. |
| `POST` | `/clans/friendly-challenge/join` | JWT | `challenge_id` | Joins an active clan challenge. Launches match when full. |
| `POST` | `/clans/friendly-challenge/close`| JWT | `challenge_id` | Cancels or closes an open challenge (creator only). |
| `GET` | `/clans/details/{clan_id}` | JWT | `clan_id` (Path) | Public profile and member list of any clan. |

---

### 3.6 Messaging Endpoints (`Routers/messaging_router.py`)

| Method | Endpoint | Auth | Parameters | Description |
|---|---|---|---|---|
| `GET` | `/messages/conversations` | JWT | `skip`, `limit` (Query) | Lists direct message conversation threads with partner info and unread counters. |
| `GET` | `/messages/direct/{partner_id}` | JWT | `partner_id` (Path), `skip`, `limit` | Retrieves chat message history between the user and a friend. |
| `POST` | `/messages/direct/send` | JWT | `to_user_id`, `text` (JSON/Form) | Sends a direct message (honors privacy settings and blocklists). |
| `POST` | `/messages/direct/read` | JWT | `partner_id` (JSON/Form) | Marks direct messages from a conversation partner as read. |
| `GET` | `/messages/clan` | JWT | `clan_id` (optional), `skip`, `limit` | Retrieves clan chat history. |
| `POST` | `/messages/clan/send` | JWT | `text` (JSON/Form) | Posts a message to the clan chat. |
| `POST` | `/messages/clan/delete` | JWT | `message_id` (JSON/Form) | Deletes a clan message (permitted for author or Clan Leader/Co-Leader). |

---

### 3.7 Notification Endpoints (`Routers/notification_router.py`)

| Method | Endpoint | Auth | Parameters | Description |
|---|---|---|---|---|
| `GET` | `/notifications/list` | JWT | `skip`, `limit`, `unread_only` | Retrieves in-game notifications (friend requests, clan invites, rewards). |
| `POST` | `/notifications/read` | JWT | `notification_id` | Marks a specific notification as read. |
| `POST` | `/notifications/read-all` | JWT | Header | Marks all notifications as read. |
| `POST` | `/notifications/preferences` | JWT | `preferences` (JSON dict) | Updates notification category toggles. |

---

### 3.8 General & Store Endpoints (`Routers/general_router.py`)

| Method | Endpoint | Auth | Parameters | Description |
|---|---|---|---|---|
| `GET` | `/health` | None | None | Service health check (`{"status": "ok", "service": "server"}`). |
| `GET` | `/config` | None | None | Returns version constraints (`allowed_version`, `latest_version`) and queue status (`is_queue_open`). |
| `GET` | `/ranking-by-score` | None | None | Top 25 leaderboard ranked by competitive score (bots excluded). |
| `GET` | `/ranking-by-win` | None | None | Top 25 leaderboard ranked by total ranked victories (bots excluded). |
| `GET` | `/get-free-coin` | JWT | Header | Daily / 8-hour free coin reward chance (randomly awards 4, 8, 12, 16, or 20 coins). |
| `POST` | `/purchase` | JWT | `product_id`, `market_type`, `token` (Form) | Validates CafeBazaar (with automatic OAuth refresh) or Myket purchase tokens and credits coins. |

**In-App Purchase Tier Mapping:**
- Product `1`: +50 coins
- Product `2`: +160 coins
- Product `3`: +330 coins
- Product `4`: +525 coins
- Product `5`: +1100 coins
- Product `6`: +1700 coins

---

### 3.9 Admin Endpoints (`Routers/admin_router.py`)

Protected via query parameter `token` matching `admin_token` (`akbarjoojehdehebala`):

| Method | Endpoint | Parameters | Description |
|---|---|---|---|
| `GET` | `/admin/unfinished-games` | `token` | Returns count of currently active/unfinished matches. |
| `GET` | `/admin/finished-games` | `token` | Returns count of completed match records. |
| `GET` | `/admin/delete-unfinished-games` | `token` | Deletes stuck matches and resets all users' `open_game_id` fields. |
| `GET` | `/admin/config-let-queue` | `token`, `value`, `hour`, `minute` | Schedules or toggles ranked queue availability. |
| `GET` | `/admin/change-version` | `token`, `allowed`, `latest` | Updates client app version enforcement rules. |
| `GET` | `/admin/users-count` | `token` | Returns total registered user count. |
| `GET` | `/admin/update-coin` | `token`, `user_id`, `value` | Manually sets coin balance for a specific player. |

---

## 4. Realtime Bridge (`Entities/Api_Services/social/realtime_bridge.py`)

To ensure seamless synchronization between REST actions and the realtime Socket.IO backend:
- When a REST call completes (e.g. friend request accepted, clan invitation sent, notification dispatched), `RealtimeBridge` sends an async internal notification to the backend (`http://backend:5000/internal/...` or shared event bus).
- The backend immediately delivers Socket.IO events (`SocialNotification`, `SocialFriendEvent`, `SocialClanEvent`) to connected sockets on the `/social` namespace without client polling.

---

## 5. Database Architecture & Automated Backup

### MongoDB Collections (`KafehFekrDB`)

- **`users`**: Profiles (`phone`, `username`, `coin`, `score`, `xp`, `image`, `device_id`, `open_game_id`, `open_pre_game_id`, `profile_frame`, `profile_title`, `profile_badge`, `status_message`, `privacy` [incl. `allow_spectators`], `created_clan_id`).
- **`user_history`**: Mode performance counters (`win_rank`, `win_classic_rank`, `win_multi_rank`, `rank1_multi_rank`) and game counters (`<game>_win`, `<game>_draw`, `<game>_lose`, `<game>_rank1`).
- **`game_play_history`**: Series-level match summaries (`game_id`, `players`, `series_scores`, `winner_id`, `reward`).
- **`game_history`**: Detailed round-level results within a match series.
- **`purchases`**: In-app purchase verification logs and product IDs.
- **`config`**: Global operational flags (`latest_version`, `allowed_version`, `is_queue_open`).
- **`clans`**: Clan registry (`name`, `tag`, `emblem_id`, `clan_score`, `clan_xp`, `clan_level`, `join_type`, `min_score`, `min_level`).
- **`clan_members`**: Memberships (`clan_id`, `user_id`, `role`, `contribution_score`).
- **`clan_messages`**: Chat logs inside clans.
- **`direct_messages`**: Private player-to-player messaging.
- **`friends`**: Friend connections, pending requests, and block relationships.
- **`invitations`**: Pending game and lobby invitations.
- **`notifications`**: In-game alerts and status updates.
- **`presence`**: Real-time presence states (`online`, `in_game`, `spectating`, `offline`, `last_seen`).
- **`reports`**: Player moderation tickets.

### Automated Backup System (`Entities/Database/backup.py`)
- Background daemon triggers automated backups every 60 minutes.
- Dumps database to the path configured by `BACKUP_DIR` (default `/app/Backups/`).
- Automatically prunes older backups to preserve storage space.

---

## 6. Configuration & Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5001` | Listening port for the REST service |
| `HOST` | `0.0.0.0` | Host interface binding |
| `MONGO_URI` | `mongodb://localhost:27017/` | Connection string to MongoDB |
| `BACKUP_DIR` | `/app/Backups/` | Storage destination directory for MongoDB backups |

---

## 7. Running the Server

### Running with Docker Compose (Recommended)
From the project root:
```bash
docker compose up -d server
```

### Running Locally with Python
```bash
pip install -r requirements.txt
python main.py
```

### Health Check Endpoint
```bash
curl http://localhost:5001/health
# Response: {"status": "ok", "service": "server"}
```
