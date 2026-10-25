# Projects set up before the rename to English

Read when the profile or the state directory is missing under the current names, or a file still uses a Portuguese
name.

- **Profile:** projects set up before the rename may still have `$CHECKOUT/.claude/coordenacao/` (`perfil.md`,
  `sessao.md`) and `$D/perfil/`. Read them when the new ones (`.claude/coordination/profile.md`, `session.md`,
  `$D/profile/`) are missing.
- **State:** if `$D` still has `fila.md`, `fila-arquivo/`, `janela.md` or `handoff/coordenadora.md`, rename them with
  `mv` to `queue.md`, `queue-archive/`, `window.md` and `handoff/coordinator.md` before continuing, and tell the owner
  in one line. The sweep and the tick still read the old names, so nothing expires during the move.
- **Copies made by hand** before the plugin existed (agents, hooks, the skill `coordenar-sessoes`, rules in
  `~/.claude`): `/keel:migrate` removes them so nothing runs twice.
