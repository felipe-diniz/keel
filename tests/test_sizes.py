"""Size caps of what enters the context, and the index of each skill's references."""
import re

import pytest

from conftest import PLUGIN

SKILLS = PLUGIN / "skills"

# bytes. rules.md is reread on every call of every session, and the SessionStart hook output that carries it (with the
# migrate notice) is capped at 10,000 characters. A skill core is loaded whole on every invocation, and after compaction
# only its first 20,000 characters come back. The footer goes into every front's prompt.
CAPS = {
    "rules.md": 9_600,
    "skills/coordinate-sessions/SKILL.md": 12_000,
    "skills/coordinate-sessions/templates/footer.md": 6_000,
    "skills/web-craft/SKILL.md": 6_000,
}
DESCRIPTION_CAP = 520
REFERENCE_CAP = 16_384


def frontmatter(path):
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.S)
    return dict(line.split(": ", 1) for line in match.group(1).splitlines() if ": " in line)


@pytest.mark.parametrize("rel,cap", sorted(CAPS.items()))
def test_file_under_its_cap(rel, cap):
    size = len((PLUGIN / rel).read_bytes())
    assert size <= cap, f"{rel}: {size} B > {cap} B"


@pytest.mark.parametrize("skill", sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md")))
def test_skill_description_is_short(skill):
    description = frontmatter(SKILLS / skill / "SKILL.md")["description"]
    assert len(description) <= DESCRIPTION_CAP, f"{skill}: {len(description)} chars"


@pytest.mark.parametrize("ref", sorted(str(p.relative_to(SKILLS)) for p in SKILLS.glob("*/references/*.md")))
def test_reference_says_when_to_read_it_and_is_capped(ref):
    text = (SKILLS / ref).read_text()
    assert len(text.encode()) <= REFERENCE_CAP, f"{ref}: {len(text.encode())} B"
    first = next(line for line in text.splitlines()[1:] if line.strip())
    assert first.startswith("Read when"), f"{ref}: first line is not 'Read when …'"


@pytest.mark.parametrize("skill", sorted(p.parent.name for p in SKILLS.glob("*/references")))
def test_every_reference_is_indexed_and_every_link_exists(skill):
    core = (SKILLS / skill / "SKILL.md").read_text()
    links = set(re.findall(r"\]\((references/[\w.-]+\.md)\)", core))
    for link in links:
        assert (SKILLS / skill / link).is_file(), f"{skill}: broken link {link}"
    refs = {f"references/{p.name}" for p in (SKILLS / skill / "references").glob("*.md")}
    linked_anywhere = set(links)
    for ref in refs:
        linked_anywhere |= {f"references/{m}" for m in re.findall(r"\(([\w.-]+\.md)\)",
                                                                  (SKILLS / skill / ref).read_text())}
    assert refs <= linked_anywhere, f"{skill}: not indexed {sorted(refs - linked_anywhere)}"
