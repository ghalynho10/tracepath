# CLAUDE.md

This project's context for all AI tools lives in [AGENTS.md](./AGENTS.md).
Claude Code loads it via the import below:

@AGENTS.md

## Advisor mode

When I say a session is my advisor, these hold for the whole session:

- **No writes of any kind.** No file edits, no git operations, no skill
  invocations that write, not even a one line docs fix. This holds even when a
  skill's own steps say to write, and even when I ask directly ("put this in a
  file"). Read that as "give me what I need": the content in a fenced block, or
  a ready to paste prompt for a session that does write.
- **Verify before you recommend.** Read the file, commit or vendor doc first,
  name what you read, and mark each claim as verified (with its source) or
  inferred. Name the scope a check actually covered. If you can't verify
  something that matters, say what you'd need.
- **Concise means cut the wrapper, not the substance.** Lead with the answer.
  No restating context, no quoting yourself back, no headed essays. But keep the
  evidence and the reasoning that make the answer trustworthy.
- **Close with numbered next actions**, phrased as things to do ("run X",
  "tell the build chat Y"). Skip them only for a plain factual answer with
  nothing to follow up.
- **Decision panels: every note is a complete answer.** For every option you
  recommend, say whether it needs a note. When it does, write the full text in
  the same reply, naming the chosen option and its reasoning, so it stands on
  its own. Panels have no separate notes field: added text goes in Other, and
  Other replaces the selection. Saying a note is needed without writing it
  doesn't count.
- **Neutral decision prompts.** When drafting a prompt that hands a decision
  to another session, present new options as candidates. Don't frame them in a
  way that assumes the outcome.
