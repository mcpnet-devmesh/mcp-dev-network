"""Web routes: landing page + admin panel.
ponytail: inline HTML, no template engine needed for 2 pages.
"""

import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "admin123")


@router.get("/", response_class=HTMLResponse)
async def landing():
    """Landing page — explains what this is and how to connect."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MCP Dev Network</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:2rem}
.container{max-width:720px;width:100%}
h1{font-size:2.5rem;background:linear-gradient(135deg,#38bdf8,#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.5rem}
.subtitle{color:#94a3b8;font-size:1.1rem;margin-bottom:2rem}
.card{background:#1e293b;border-radius:12px;padding:1.5rem;margin-bottom:1.5rem;border:1px solid #334155}
.card h2{color:#38bdf8;margin-bottom:.75rem;font-size:1.2rem}
.card p,.card li{color:#cbd5e1;line-height:1.6}
.card ul{padding-left:1.5rem}
code{background:#334155;padding:2px 6px;border-radius:4px;font-size:.9em;color:#38bdf8}
pre{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:1rem;overflow-x:auto;margin:.75rem 0;font-size:.85rem;color:#e2e8f0}
.tools-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.75rem}
.tool{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:.75rem;text-align:center}
.tool strong{color:#818cf8;display:block;margin-bottom:.25rem}
.tool span{color:#94a3b8;font-size:.85rem}
a{color:#38bdf8;text-decoration:none}a:hover{text-decoration:underline}
.badge{display:inline-block;background:#334155;color:#38bdf8;padding:2px 8px;border-radius:4px;font-size:.8rem;margin:2px}
footer{margin-top:2rem;color:#64748b;font-size:.85rem}
</style>
</head>
<body>
<div class="container">
<h1>MCP Dev Network</h1>
<p class="subtitle">A social network for developers, built as an MCP server. Connect your IDE and interact with other devs.</p>

<div class="card">
<h2>🚀 Get Started (2 min)</h2>
<p><strong>1. Create account:</strong></p>
<pre>curl -X POST https://mcp-dev-network-production.up.railway.app/auth/signup \\
  -H "Content-Type: application/json" \\
  -d '{"email":"you@email.com","password":"yourpass"}'</pre>
<p><strong>2. Add to your IDE</strong> (Cursor, Kiro, Antigravity, Claude Desktop):</p>
<pre>{
  "mcpServers": {
    "dev-network": {
      "command": "npx",
      "args": ["-y", "mcp-remote",
        "https://mcp-dev-network-production.up.railway.app/mcp",
        "--header", "Authorization: Bearer YOUR_TOKEN"]
    }
  }
}</pre>
<p><strong>3. Talk to your AI:</strong> "Register my profile with username X and stack [python, rust]"</p>
</div>

<div class="card">
<h2>🛠️ 20 Tools Available</h2>
<div class="tools-grid">
<div class="tool"><strong>register</strong><span>Create profile</span></div>
<div class="tool"><strong>get_profile</strong><span>View any user</span></div>
<div class="tool"><strong>get_my_profile</strong><span>View your profile</span></div>
<div class="tool"><strong>list_users</strong><span>Browse all devs</span></div>
<div class="tool"><strong>search_users</strong><span>Find by stack</span></div>
<div class="tool"><strong>send_message</strong><span>Private E2E msg</span></div>
<div class="tool"><strong>get_messages</strong><span>Read inbox</span></div>
<div class="tool"><strong>create_post</strong><span>Public feed post</span></div>
<div class="tool"><strong>get_feed</strong><span>Read feed</span></div>
<div class="tool"><strong>delete_post</strong><span>Delete your post</span></div>
<div class="tool"><strong>like_post</strong><span>Like a post</span></div>
<div class="tool"><strong>follow</strong><span>Follow a dev</span></div>
<div class="tool"><strong>unfollow</strong><span>Unfollow a dev</span></div>
<div class="tool"><strong>my_following</strong><span>Who you follow</span></div>
<div class="tool"><strong>get_notifications</strong><span>Your alerts</span></div>
<div class="tool"><strong>mark_read</strong><span>Mark as read</span></div>
<div class="tool"><strong>discover</strong><span>Discover devs</span></div>
<div class="tool"><strong>share_resource</strong><span>Share link/snippet</span></div>
<div class="tool"><strong>search_resources</strong><span>Find resources</span></div>
<div class="tool"><strong>report_content</strong><span>Flag bad content</span></div>
</div>
</div>

<div class="card">
<h2>🔒 Security</h2>
<ul>
<li>Messages encrypted with <strong>AES-256-GCM</strong></li>
<li>JWT RS256 authentication</li>
<li>Row-Level Security in PostgreSQL</li>
<li>Rate limiting per user</li>
<li>Prompt injection protection</li>
</ul>
</div>

<div class="card">
<h2>📦 Links</h2>
<p>
<a href="https://github.com/mcpnet-devmesh/mcp-dev-network">GitHub</a> •
<a href="/docs">API Docs</a> •
<a href="/health">Health Check</a>
</p>
</div>

<footer>Built with FastAPI + PostgreSQL + MCP Protocol • Open source MIT</footer>
</div>
</body>
</html>"""


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(secret: str = ""):
    """Simple admin panel — protected by ADMIN_SECRET query param."""
    if secret != ADMIN_SECRET:
        return HTMLResponse("<h1>401 — Add ?secret=YOUR_ADMIN_SECRET</h1>", status_code=401)

    from mcp_dev_network.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                (SELECT COUNT(*) FROM auth_users) as accounts,
                (SELECT COUNT(*) FROM profiles) as profiles,
                (SELECT COUNT(*) FROM posts) as posts,
                (SELECT COUNT(*) FROM messages) as messages,
                (SELECT COUNT(*) FROM resources) as resources,
                (SELECT COUNT(*) FROM reports) as reports
        """)
        users = await conn.fetch("SELECT username, stack, bio, created_at FROM profiles ORDER BY created_at DESC LIMIT 50")
        recent_posts = await conn.fetch("""
            SELECT p.content, p.tags, p.created_at, pr.username
            FROM posts p JOIN profiles pr ON pr.user_id = p.author_id
            ORDER BY p.created_at DESC LIMIT 20
        """)

    users_html = ""
    for u in users:
        stack = ", ".join(u["stack"]) if u["stack"] else "-"
        users_html += f'<tr><td>{u["username"]}</td><td>{stack}</td><td>{u["bio"][:50]}</td><td>{str(u["created_at"])[:16]}</td></tr>'

    posts_html = ""
    for p in recent_posts:
        tags = ", ".join(p["tags"]) if p["tags"] else ""
        posts_html += f'<tr><td>{p["username"]}</td><td>{p["content"][:80]}</td><td>{tags}</td><td>{str(p["created_at"])[:16]}</td></tr>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Admin — MCP Dev Network</title>
<style>
body{{font-family:system-ui;background:#0f172a;color:#e2e8f0;padding:2rem}}
h1{{color:#38bdf8}}h2{{color:#818cf8;margin-top:2rem}}
table{{width:100%;border-collapse:collapse;margin-top:1rem}}
th,td{{text-align:left;padding:.5rem;border-bottom:1px solid #334155}}
th{{color:#38bdf8}}
.stat{{display:inline-block;background:#1e293b;border-radius:8px;padding:1rem 1.5rem;margin:.5rem;text-align:center}}
.stat .num{{font-size:2rem;color:#38bdf8;font-weight:bold}}
.stat .label{{color:#94a3b8;font-size:.85rem}}
</style></head><body>
<h1>🛡️ Admin Panel</h1>
<div>
<div class="stat"><div class="num">{stats['accounts']}</div><div class="label">Accounts</div></div>
<div class="stat"><div class="num">{stats['profiles']}</div><div class="label">Profiles</div></div>
<div class="stat"><div class="num">{stats['posts']}</div><div class="label">Posts</div></div>
<div class="stat"><div class="num">{stats['messages']}</div><div class="label">Messages</div></div>
<div class="stat"><div class="num">{stats['resources']}</div><div class="label">Resources</div></div>
<div class="stat"><div class="num">{stats['reports']}</div><div class="label">Reports</div></div>
</div>

<h2>Users ({stats['profiles']})</h2>
<table><tr><th>Username</th><th>Stack</th><th>Bio</th><th>Joined</th></tr>{users_html}</table>

<h2>Recent Posts</h2>
<table><tr><th>Author</th><th>Content</th><th>Tags</th><th>Date</th></tr>{posts_html}</table>
</body></html>"""
