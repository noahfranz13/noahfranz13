#!/usr/bin/env python3
"""
Aggregate GitHub commits across personal account and all organizations.
Generates an SVG card for your profile README.
Only counts commits authored by the user.
Also counts total stars on repos contributed to.
"""

import os
import math
import re
from datetime import datetime
from github import Github, Auth


from datetime import datetime, timedelta, timezone


def get_all_commits(github_user, token):
    g = Github(auth=Auth.Token(token))
    user = g.get_user()

    total_commits = 0
    total_stars = 0
    repos_analyzed = 0
    orgs_list = []
    repo_star_map = {}

    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)

    # Get personal repos
    print("📊 Fetching personal repositories...")
    try:
        for repo in user.get_repos(type="owner"):
            if not repo.fork:
                try:
                    commits = repo.get_commits(
                        author=github_user, since=one_year_ago
                    ).totalCount
                    total_commits += commits
                    total_stars += repo.stargazers_count
                    repos_analyzed += 1
                    print(
                        f"  ✓ {repo.name}: {commits} commits, {repo.stargazers_count} ⭐"
                    )
                    if commits > 0:
                        repo_star_map[f"noahfranz13/{repo.name}"] = (
                            repo.stargazers_count
                        )
                except Exception as e:
                    print(f"  ⚠ {repo.name}: Skipped ({str(e)[:50]})")
    except Exception as e:
        print(f"❌ Error fetching personal repos: {e}")

    # Get all organizations
    print("\n🏢 Fetching organizations...")
    try:
        for org in user.get_orgs():
            orgs_list.append(org.login)
            print(f"  Found: {org.login}")
            try:
                for repo in org.get_repos(type="all"):
                    try:
                        commits = repo.get_commits(
                            author=github_user, since=one_year_ago
                        ).totalCount
                        if commits > 0:
                            total_commits += commits
                            total_stars += repo.stargazers_count
                            repos_analyzed += 1
                            print(
                                f"    ✓ {repo.name}: {commits} commits, {repo.stargazers_count} ⭐"
                            )
                            repo_star_map[f"{org.login}/{repo.name}"] = (
                                repo.stargazers_count
                            )
                    except Exception as e:
                        print(f"    ⚠ {repo.name}: Skipped ({str(e)[:50]})")
            except Exception as e:
                print(f"  ⚠ {org.login}: Could not fetch repos ({str(e)[:50]})")
    except Exception as e:
        print(f"❌ Error fetching organizations: {e}")

    g.close()

    return {
        "total_commits": total_commits,
        "total_stars": total_stars,
        "repos_analyzed": repos_analyzed,
        "organizations": orgs_list,
        "repo_star_map": repo_star_map,
        "timestamp": datetime.now().isoformat(),
    }


def generate_svg(stats):
    """Generate an SVG card with stats."""

    commits_str = f"{stats['total_commits']:,}"
    stars_str = f"{stats['total_stars']:,}"
    repos_str = str(stats["repos_analyzed"])

    # Split top_repos into individual lines for separate <text> elements
    sorted_star_map = {
        k: v
        for k, v in sorted(
            stats["repo_star_map"].items(), key=lambda item: item[1], reverse=True
        )
    }

    max_repos_include = 6
    top_repo_names = [
        (reponame, starcount)
        for ii, (reponame, starcount) in enumerate(sorted_star_map.items())
        if starcount >= 1 and ii < max_repos_include
    ]

    col_x = [20, 235]  # x positions for left and right columns

    max_y = 0
    top_repos_svg_list = []
    n_rows = math.ceil(len(top_repo_names) / 2)
    for i, (name, stars) in enumerate(top_repo_names):
        this_y = 192 + (i % n_rows) * 20
        top_repos_svg_list.append(
            f'<text class="value" x="{col_x[i // n_rows] + 10}" y="{this_y}" font-size="12">{name} <tspan fill="#e3b341">({stars} ★)</tspan></text>'
        )
        if this_y > max_y:
            max_y = this_y

    top_repos_svg = "\n  ".join(top_repos_svg_list)

    # SVG dimensions
    width = 500
    height = max_y + 30

    svg = f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
      <style>
        .bg {{ fill: #0d1117; }}
        .title {{ font: bold 20px 'Segoe UI', Arial; fill: #58a6ff; }}
        .label {{ font: 12px 'Segoe UI', Arial; fill: #8b949e; }}
        .value {{ font: bold 14px 'Segoe UI', Arial; fill: #c9d1d9; }}
        .divider {{ stroke: #30363d; stroke-width: 1; }}
        .border {{ stroke: #30363d; stroke-width: 1; fill: none; }}
      </style>

      <!-- Background -->
      <rect class="bg" width="{width}" height="310"/>
      <rect class="border" width="{width}" height="310"/>

      <!-- Title -->
      <text class="title" x="20" y="35">GitHub Stats</text>

      <!-- Divider under title -->
      <line class="divider" x1="20" y1="48" x2="{width - 20}" y2="48"/>

      <!-- Total Commits -->
      <text class="label" x="20" y="72">total commits in past year</text>
      <text class="value" x="20" y="90">{commits_str}</text>

      <!-- Stars Earned -->
      <text class="label" x="20" y="118">stars earned</text>
      <text class="value" x="20" y="136">{stars_str}</text>

      <!-- Repositories -->
      <text class="label" x="240" y="72">repositories contributed to in past year</text>
      <text class="value" x="240" y="90">{repos_str}</text>

      <!-- Organizations -->
      <text class="label" x="240" y="118">organizations</text>
      <text class="value" x="240" y="136">{len(stats["organizations"])}</text>

      <!-- Divider above top repos -->
      <line class="divider" x1="20" y1="155" x2="{width - 20}" y2="155"/>

      <!-- Top Repositories -->
      <text class="label" x="20" y="174">top repositories</text>
      <line class="divider" x1="235" y1="158" x2="235" y2="248" stroke-dasharray="3,3"/>
      {top_repos_svg}

      <!-- Last Updated -->
      <text class="label" x="{width - 20}" y="{height - 10}" font-size="10" text-anchor="end">Updated: {stats["timestamp"][:10]}</text>
    </svg>"""
    return svg


def update_readme(stats, svg_content, readme_path="README.md"):
    """Update README.md with SVG."""

    # Write SVG file
    svg_path = ".github/profile-stats.svg"
    os.makedirs(os.path.dirname(svg_path), exist_ok=True)

    with open(svg_path, "w") as f:
        f.write(svg_content)

    print(f"✅ SVG generated: {svg_path}")

    # Update README
    markdown_section = f"""<!-- GITHUB-STATS:START -->
![GitHub Stats](./.github/profile-stats.svg)
<!-- GITHUB-STATS:END -->"""

    # Read current README
    if os.path.exists(readme_path):
        with open(readme_path, "r") as f:
            content = f.read()
    else:
        content = ""

    # Replace or add stats section
    if "<!-- GITHUB-STATS:START -->" in content:
        pattern = r"<!-- GITHUB-STATS:START -->.*?<!-- GITHUB-STATS:END -->"
        content = re.sub(pattern, markdown_section, content, flags=re.DOTALL)
    else:
        content = markdown_section + "\n\n" + content

    with open(readme_path, "w") as f:
        f.write(content)

    print(f"✅ README.md updated!")


if __name__ == "__main__":
    token = os.getenv("GITHUB_TOKEN")
    username = os.getenv("GITHUB_ACTOR")

    if not token:
        print("❌ GITHUB_TOKEN not set!")
        exit(1)

    if not username:
        print("❌ GITHUB_ACTOR not set!")
        exit(1)

    print(f"👤 Analyzing GitHub stats for: {username}\n")

    stats = get_all_commits(username, token)
    svg = generate_svg(stats)
    update_readme(stats, svg)

    print("\n" + "=" * 50)
    print(f"Total Commits (all repos): {stats['total_commits']:,}")
    print(f"Stars Earned (incl. orgs): {stats['total_stars']:,}")
    print(f"Repositories Analyzed: {stats['repos_analyzed']}")
    print(f"Organizations: {len(stats['organizations'])}")
    print("=" * 50)
