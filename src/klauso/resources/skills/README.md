# Project skills

Each **directory** here is one skill. The harness scans `skills/<name>/SKILL.md` and exposes:

- **`list_skills`** — folder name plus description (from YAML `description:` in front matter, else first body line).
- **`load_skill`** — returns the full `SKILL.md` text for the model to follow.

Add a new skill by creating `skills/<your-skill>/SKILL.md` (Markdown with optional `---` front matter). No restart required beyond what the REPL already loads from disk on each tool call.

To discover **installable** skills from the broader ecosystem (outside this repo), use [skills.sh](https://skills.sh/) and the Skills CLI, for example `npx skills find <keywords>` and `npx skills add <owner/repo@skill>`.
