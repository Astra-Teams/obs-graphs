"""Agent responsible for enhancing cross-references between vault articles."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

from src.nodes.base import BaseAgent
from src.prompts import render_prompt
from src.state import AgentResult, FileAction, FileChange


@dataclass(frozen=True)
class _NoteProfile:
    """Lightweight representation of a markdown note used for linking."""

    relative_path: str
    link_target: str
    title: str
    keywords: Set[str]
    existing_links: Set[str]
    content: str


class CrossReferenceAgent(BaseAgent):
    """
    Agent that scans markdown files and adds contextual cross references.

    The agent uses lightweight keyword matching heuristics and optional
    `link_suggestions` provided in the execution context to determine where new
    links should be added. When new links are discovered, they are appended to a
    "Related" section in the corresponding markdown file.
    """

    _STOP_WORDS = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "into",
        "your",
        "about",
        "when",
        "where",
        "which",
        "will",
        "have",
        "using",
        "guide",
        "introduction",
        "overview",
        "topic",
        "note",
    }
    _MIN_SHARED_KEYWORDS = 2

    def execute(self, vault_path: Path, context: dict) -> AgentResult:
        if not self.validate_input(context):
            raise ValueError(
                "Invalid execution context provided to CrossReferenceAgent"
            )

        note_profiles = self._collect_note_profiles(vault_path)
        if not note_profiles:
            return AgentResult(
                success=True,
                changes=[],
                message="No markdown files found for cross-referencing.",
                metadata={"notes_processed": 0, "links_added": 0},
            )

        link_plan = self._build_link_plan(note_profiles, context)

        changes: List[FileChange] = []
        total_links_added = 0

        for profile in note_profiles:
            pending_links = link_plan.get(profile.relative_path, set())
            if not pending_links:
                continue

            new_content, added_links = self._apply_links(profile, pending_links)
            if added_links == 0 or new_content == profile.content:
                continue

            total_links_added += added_links
            changes.append(
                FileChange(
                    path=profile.relative_path,
                    action=FileAction.UPDATE,
                    content=new_content,
                )
            )

        message = (
            "Added cross-references to notes."
            if changes
            else "No new cross-references needed."
        )

        metadata = {
            "notes_processed": len(note_profiles),
            "notes_updated": len(changes),
            "links_added": total_links_added,
        }

        return AgentResult(
            success=True, changes=changes, message=message, metadata=metadata
        )

    def validate_input(self, context: dict) -> bool:
        if not isinstance(context, dict):
            return False

        suggestions = context.get("link_suggestions")
        if suggestions is None:
            return True
        if not isinstance(suggestions, dict):
            return False

        for key, value in suggestions.items():
            if not isinstance(key, str):
                return False
            if not isinstance(value, (list, tuple, set)):
                return False
            if any(not isinstance(item, str) for item in value):
                return False
        return True

    def get_name(self) -> str:
        return "Cross Reference Agent"

    def _collect_note_profiles(self, vault_path: Path) -> List[_NoteProfile]:
        profiles: List[_NoteProfile] = []
        for path in sorted(vault_path.rglob("*.md")):
            if not path.is_file():
                continue

            relative_path = path.relative_to(vault_path).as_posix()
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue

            title = self._extract_title(path.stem, content)
            keywords = self._extract_keywords(content)
            existing_links = self._extract_existing_links(content)
            link_target = self._normalise_link_target(relative_path)

            profiles.append(
                _NoteProfile(
                    relative_path=relative_path,
                    link_target=link_target,
                    title=title,
                    keywords=keywords,
                    existing_links=existing_links,
                    content=content,
                )
            )
        return profiles

    def _build_link_plan(
        self, note_profiles: Sequence[_NoteProfile], context: dict
    ) -> Dict[str, Set[Tuple[str, str]]]:
        plan: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)
        profile_by_target = {profile.link_target: profile for profile in note_profiles}
        profile_by_path = {profile.relative_path: profile for profile in note_profiles}

        # Context-supplied suggestions take precedence.
        context_suggestions = context.get("link_suggestions", {})
        for raw_source, raw_targets in context_suggestions.items():
            source_path = self._resolve_to_relative(raw_source, profile_by_path)
            if source_path is None:
                continue
            for raw_target in raw_targets:
                normalised_target = self._normalise_link_target(raw_target)
                target_profile = profile_by_target.get(normalised_target)
                if target_profile is None:
                    continue
                if normalised_target in profile_by_path[source_path].existing_links:
                    continue
                plan[source_path].add(
                    (target_profile.link_target, target_profile.title)
                )

        # Derive suggestions using keyword overlap heuristics.
        for i, source_profile in enumerate(note_profiles):
            for candidate_profile in note_profiles[i + 1 :]:
                shared_keywords = source_profile.keywords & candidate_profile.keywords
                if len(shared_keywords) < self._MIN_SHARED_KEYWORDS:
                    continue

                if candidate_profile.link_target not in source_profile.existing_links:
                    plan[source_profile.relative_path].add(
                        (candidate_profile.link_target, candidate_profile.title)
                    )
                if source_profile.link_target not in candidate_profile.existing_links:
                    plan[candidate_profile.relative_path].add(
                        (source_profile.link_target, source_profile.title)
                    )

        return plan

    def _apply_links(
        self, profile: _NoteProfile, pending_links: Set[Tuple[str, str]]
    ) -> Tuple[str, int]:
        if not pending_links:
            return profile.content, 0

        lines = profile.content.splitlines()
        related_header_index = None
        for idx, line in enumerate(lines):
            if line.strip().lower().startswith("## related"):
                related_header_index = idx
                break

        if related_header_index is None:
            # Append a Related section to the end of the document.
            if lines and lines[-1].strip():
                lines.append("")
            lines.append("## Related")
            lines.append("")
            related_header_index = len(lines) - 2

        # Collect existing entries within the related section.
        existing_entries: Set[str] = set()
        insertion_index = related_header_index + 1
        while insertion_index < len(lines) and not lines[insertion_index].startswith(
            "## "
        ):
            line = lines[insertion_index].strip()
            link_match = re.search(r"\[\[([^\]]+)\]\]", line)
            if link_match:
                existing_entries.add(self._normalise_link_target(link_match.group(1)))
            insertion_index += 1

        new_lines: List[str] = []
        added_links = 0
        for link_target, title in sorted(pending_links):
            if link_target in existing_entries:
                continue
            formatted_link = self._format_link(link_target, title)
            new_lines.append(f"- {formatted_link}")
            existing_entries.add(link_target)
            added_links += 1

        if not new_lines:
            return profile.content, 0

        lines[insertion_index:insertion_index] = new_lines + [""]
        return "\n".join(lines).rstrip() + "\n", added_links

    def _extract_title(self, default: str, content: str) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("# ")
        return default.replace("-", " ").replace("_", " ").title()

    def _extract_keywords(self, content: str) -> Set[str]:
        keyword_source: List[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                keyword_source.append(stripped.lstrip("# "))
        keyword_source_text = " ".join(keyword_source).lower()
        tokens = re.findall(r"[a-z0-9']+", keyword_source_text)
        keywords = {
            token
            for token in tokens
            if len(token) > 2 and token not in self._STOP_WORDS
        }
        return keywords

    def _extract_existing_links(self, content: str) -> Set[str]:
        links = set()
        for match in re.findall(r"\[\[([^\]]+)\]\]", content):
            links.add(self._normalise_link_target(match))
        return links

    def _normalise_link_target(self, value: str) -> str:
        value = value.strip().replace("\\", "/")
        if value.lower().endswith(".md"):
            value = value[:-3]
        if "|" in value:
            value = value.split("|", 1)[0]
        return value

    def _resolve_to_relative(
        self, reference: str, profiles_by_path: Dict[str, _NoteProfile]
    ) -> str | None:
        reference = reference.strip().replace("\\", "/")
        if reference in profiles_by_path:
            return reference
        if (
            reference.lower().endswith(".md")
            and reference[:-3] + ".md" in profiles_by_path
        ):
            return reference[:-3] + ".md"
        for relative_path in profiles_by_path:
            if relative_path.endswith(reference):
                return relative_path
            if relative_path.endswith(reference + ".md"):
                return relative_path
        return None

    def _format_link(self, target: str, title: str) -> str:
        display_name = title.strip() or target.split("/")[-1]
        normalized_display = display_name.lower().replace(" ", "-")
        final_segment = target.split("/")[-1].lower()
        if normalized_display == final_segment:
            return f"[[{target}]]"
        return f"[[{target}|{display_name}]]"
