import json, sys, urllib.request

# --- Configure these two values ---
HOST = "forrest.hashnode.dev"        # your blog's host
USERNAME = "forrestcaffray"          # your Hashnode username
LIMIT = 24                           # max posts to keep
# ----------------------------------

def post_json(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

items = []

# Try modern GraphQL (preferred)
try:
    data = post_json(
        "https://gql.hashnode.com/",
        {
            "query": """
              query ($host: String!, $first: Int!) {
                publication(host: $host) {
                  posts(first: $first) {
                    edges {
                      node {
                        title
                        slug
                        url
                        publishedAt
                        brief
                        coverImage { url }
                        tags { name }
                      }
                    }
                  }
                }
              }
            """,
            "variables": {"host": HOST, "first": LIMIT},
        },
    )
    edges = (
        ((data.get("data") or {}).get("publication") or {})
        .get("posts", {})
        .get("edges", [])
    )
    for e in edges:
        n = e.get("node") or {}
        url = n.get("url") or f"https://{HOST}/{n.get('slug','')}"
        img = None
        ci = n.get("coverImage")
        if isinstance(ci, dict):
            img = ci.get("url")
        if not img:
            img = n.get("coverImageUrl") or n.get("cover")  # harmless fallback
        items.append(
            {
                "title": (n.get("title") or "").strip(),
                "url": url,
                "date": (n.get("publishedAt") or "").strip(),
                "brief": (n.get("brief") or "").strip(),
                "image": img,
                "tags": [
                    t.get("name", "")
                    for t in (n.get("tags") or [])
                    if t and t.get("name")
                ],
            }
        )
except Exception as e:
    print("GraphQL fetch failed:", e, file=sys.stderr)

# Fallback to legacy API if needed (no images/brief guaranteed)
if not items:
    try:
        data = post_json(
            "https://api.hashnode.com/",
            {
                "query": """
                  query ($username: String!, $page: Int!) {
                    user(username: $username) {
                      publication {
                        posts(page: $page) {
                          title
                          slug
                          dateAdded
                          tags { name }
                        }
                      }
                    }
                  }
                """,
                "variables": {"username": USERNAME, "page": 0},
            },
        )
        posts = (
            ((data.get("data") or {}).get("user") or {})
            .get("publication", {})
            .get("posts", [])
        )
        for p in posts[:LIMIT]:
            url = f"https://{HOST}/{p.get('slug','')}"
            items.append(
                {
                    "title": (p.get("title") or "").strip(),
                    "url": url,
                    "date": (p.get("dateAdded") or "").strip(),
                    "brief": "",
                    "image": None,
                    "tags": [
                        t.get("name", "")
                        for t in (p.get("tags") or [])
                        if t and t.get("name")
                    ],
                }
            )
    except Exception as e:
        print("Legacy API fetch failed:", e, file=sys.stderr)

if not items:
    print("No items fetched from either API.", file=sys.stderr)
    sys.exit(1)

open("posts.json", "w").write(json.dumps(items[:LIMIT], indent=2))
print("Wrote posts.json with", len(items[:LIMIT]), "items")
