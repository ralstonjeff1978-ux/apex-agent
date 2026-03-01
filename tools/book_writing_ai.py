"""
BOOK WRITING AI - Creative Writing and Publishing Assistant
=========================================================
AI-powered writing assistant for novels, technical books, and content creation.

Features:
- Story generation and outlining
- Character development tools
- Writing style analysis
- Chapter drafting and editing
- Publishing preparation
- Collaboration tools
"""

import json
import time
import re
import yaml
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import Counter
import random

log = logging.getLogger("book_writing")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"


def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data"))


@dataclass
class Character:
    """Represents a book character"""
    name: str
    age: int
    occupation: str
    personality_traits: List[str]
    backstory: str
    motivation: str
    character_arc: str
    relationships: Dict[str, str]


@dataclass
class Chapter:
    """Represents a chapter in a book"""
    number: int
    title: str
    summary: str
    content: str
    word_count: int
    scenes: List[str]
    pov_character: str


@dataclass
class BookProject:
    """Represents a complete book project"""
    title: str
    genre: str
    description: str
    target_audience: str
    word_target: int
    chapters: List[Chapter]
    characters: List[Character]
    themes: List[str]
    setting: str
    timeline: str
    tone: str
    created_at: float
    last_modified: float
    project_path: str
    status: str
    progress: float


class BookWritingAI:
    def __init__(self, projects_dir: Path = None):
        if projects_dir is None:
            projects_dir = _storage_base() / "book_projects"
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.projects: Dict[str, BookProject] = {}
        self.writing_styles = self._load_writing_styles()
        self.load_projects()

    def _load_writing_styles(self) -> Dict[str, List[str]]:
        """Load predefined writing styles and techniques"""
        return {
            "mystery": [
                "foreshadowing", "red_herrings", "cliffhangers",
                "multiple_pov", "pacing", "atmosphere"
            ],
            "sci-fi": [
                "world_building", "technology_integration", "speculative_elements",
                "scientific_concepts", "future_prediction", "ethical_dilemmas"
            ],
            "fantasy": [
                "magic_system", "world_building", "mythology_creation",
                "quest_structure", "character_transformation", "epic_scale"
            ],
            "romance": [
                "emotional_tension", "relationship_progression", "conflict_resolution",
                "character_chemistry", "setting_as_character", "happy_ending"
            ],
            "thriller": [
                "suspense_building", "plot_twists", "high_stakes",
                "fast_pacing", "ticking_clock", "psychological_depth"
            ],
            "non-fiction": [
                "research_based", "clear_explanation", "practical_examples",
                "structured_format", "citation_support", "actionable_advice"
            ]
        }

    def create_book_project(self, title: str, genre: str, description: str = "",
                            target_audience: str = "general", word_target: int = 50000) -> BookProject:
        """Create a new book project"""
        log.info("Creating book project: %s", title)

        project_path = self.projects_dir / title.lower().replace(" ", "_")
        project_path.mkdir(exist_ok=True)

        project = BookProject(
            title=title,
            genre=genre,
            description=description or f"A {genre} book titled {title}",
            target_audience=target_audience,
            word_target=word_target,
            chapters=[],
            characters=[],
            themes=[],
            setting="",
            timeline="contemporary",
            tone="serious",
            created_at=time.time(),
            last_modified=time.time(),
            project_path=str(project_path),
            status="planning",
            progress=0.0
        )

        self.projects[title] = project
        self._save_project(project)

        log.info("Book project '%s' created", title)
        return project

    def generate_outline(self, project_name: str, num_chapters: int = 10) -> List[Dict]:
        """Generate a chapter-by-chapter outline"""
        if project_name not in self.projects:
            log.error("Project %s not found", project_name)
            return []

        project = self.projects[project_name]
        log.info("Generating outline for %s (%s chapters)", project_name, num_chapters)

        outline_structures = {
            "mystery": [
                "Introduction and Crime", "Investigation Begins", "First Clues",
                "Red Herrings", "Midpoint Revelation", "Second Investigation",
                "Major Plot Twist", "Race Against Time", "Final Confrontation", "Resolution"
            ],
            "sci-fi": [
                "World Introduction", "Inciting Incident", "Technology Exploration",
                "Conflict Arises", "Allies and Enemies", "Midpoint Crisis",
                "Scientific Breakthrough", "Climax", "Resolution", "Future Implications"
            ],
            "fantasy": [
                "Ordinary World", "Call to Adventure", "Meeting Mentors",
                "Crossing Threshold", "Tests and Allies", "Approach to Inmost Cave",
                "Ordeal", "Reward", "The Road Back", "Resurrection and Return"
            ],
            "romance": [
                "Meet Cute", "Initial Attraction", "Complications Arise",
                "Growing Closer", "Major Obstacle", "Separation",
                "Dark Moment", "Grand Gesture", "Reconciliation", "Happy Ending"
            ],
            "thriller": [
                "Normal Life Interrupted", "Threat Revealed", "Investigation Begins",
                "Escalating Danger", "Allies Acquired", "Midpoint Betrayal",
                "Life Threatened", "Countdown", "Final Confrontation", "Aftermath"
            ],
            "non-fiction": [
                "Introduction", "Problem Statement", "Background Research",
                "Core Concepts", "Case Studies", "Practical Applications",
                "Common Mistakes", "Advanced Techniques", "Implementation Guide", "Conclusion"
            ]
        }

        structure = outline_structures.get(project.genre.lower(),
                                           [f"Chapter {i+1}" for i in range(num_chapters)])

        if len(structure) < num_chapters:
            extended = structure[:]
            while len(extended) < num_chapters:
                extended.append(f"Chapter {len(extended)+1}: Continued")
            structure = extended[:num_chapters]
        elif len(structure) > num_chapters:
            structure = structure[:num_chapters]

        outline = []
        words_per_chapter = project.word_target // num_chapters

        for i, chapter_title in enumerate(structure):
            outline.append({
                "chapter": i + 1,
                "title": chapter_title,
                "summary": f"Chapter {i+1} summary for {project.title}",
                "word_target": words_per_chapter,
                "key_events": [f"Event {j+1}" for j in range(3)],
                "characters_involved": [],
                "setting": project.setting or "Primary location"
            })

        log.info("Outline generated with %s chapters", len(outline))
        return outline

    def create_characters(self, project_name: str, num_characters: int = 3) -> List[Character]:
        """Create main characters for the story"""
        if project_name not in self.projects:
            log.error("Project %s not found", project_name)
            return []

        project = self.projects[project_name]
        log.info("Creating %s characters for %s", num_characters, project_name)

        archetypes = {
            "mystery": ["detective", "suspect", "victim", "sidekick", "antagonist"],
            "sci-fi": ["scientist", "alien", "leader", "rebel", "ai_entity"],
            "fantasy": ["hero", "mentor", "companion", "antagonist", "magical_being"],
            "romance": ["protagonist_female", "protagonist_male", "best_friend", "ex", "love_interest"],
            "thriller": ["protagonist", "antagonist", "victim", "investigator", "witness"],
            "non-fiction": ["expert", "case_study_subject", "reader_proxy", "historical_figure"]
        }

        genre_archetypes = archetypes.get(project.genre.lower(),
                                          ["main_character", "supporting_character", "antagonist"])

        first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Cameron", "Skyler"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        occupations = ["detective", "scientist", "teacher", "artist", "doctor", "engineer", "writer", "chef", "athlete", "entrepreneur"]
        personality_traits = ["brave", "curious", "stubborn", "empathetic", "analytical", "creative", "loyal", "ambitious", "wise", "charming"]

        characters = []
        for i in range(min(num_characters, len(genre_archetypes))):
            archetype = genre_archetypes[i] if i < len(genre_archetypes) else "supporting_character"

            character = Character(
                name=f"{random.choice(first_names)} {random.choice(last_names)}",
                age=random.randint(25, 65),
                occupation=random.choice(occupations),
                personality_traits=random.sample(personality_traits, 3),
                backstory=f"A {archetype} with a mysterious past",
                motivation=f"To achieve their goals in the {project.genre} world",
                character_arc="Transforms through challenges and growth",
                relationships={}
            )

            characters.append(character)
            project.characters.append(character)

        self._save_project(project)
        log.info("Created %s characters", len(characters))
        return characters

    def write_chapter_draft(self, project_name: str, chapter_number: int,
                            outline_details: Dict = None) -> Optional[str]:
        """Write a draft of a chapter"""
        if project_name not in self.projects:
            log.error("Project %s not found", project_name)
            return None

        project = self.projects[project_name]

        while len(project.chapters) < chapter_number:
            project.chapters.append(Chapter(
                number=len(project.chapters) + 1,
                title=f"Chapter {len(project.chapters) + 1}",
                summary="",
                content="",
                word_count=0,
                scenes=[],
                pov_character=""
            ))

        log.info("Writing draft for Chapter %s of %s", chapter_number, project_name)

        if outline_details:
            chapter_content = self._generate_chapter_content(project, chapter_number, outline_details)
        else:
            chapter_content = self._generate_basic_chapter(project, chapter_number)

        chapter = project.chapters[chapter_number - 1]
        chapter.content = chapter_content
        chapter.word_count = len(chapter_content.split())

        total_chapters = len(project.chapters)
        completed_chapters = sum(1 for ch in project.chapters if ch.content)
        project.progress = completed_chapters / total_chapters if total_chapters > 0 else 0
        project.last_modified = time.time()

        self._save_project(project)
        log.info("Chapter %s draft written (%s characters)", chapter_number, len(chapter_content))
        return chapter_content

    def _generate_chapter_content(self, project: BookProject, chapter_number: int,
                                  outline_details: Dict) -> str:
        """Generate chapter content based on outline"""
        content_parts = []

        content_parts.append(f"# {outline_details.get('title', f'Chapter {chapter_number}')}\n")
        content_parts.append("The morning sun cast long shadows across the city as ")

        if project.characters:
            pov_char = project.characters[0]
            content_parts.append(f"{pov_char.name} stood at the window, contemplating ")

        conflicts = {
            "mystery": "the mysterious letter that arrived yesterday",
            "sci-fi": "the strange signal from deep space",
            "fantasy": "the ancient prophecy that foretold disaster",
            "romance": "the unexpected arrival of someone from their past",
            "thriller": "the threatening phone call that changed everything",
            "non-fiction": "the groundbreaking research that challenged conventional wisdom"
        }

        conflict = conflicts.get(project.genre.lower(), "an unusual situation")
        content_parts.append(f"{conflict}. ")

        actions = {
            "mystery": "They carefully examined the evidence, searching for clues.",
            "sci-fi": "The team prepared for the journey to the unknown planet.",
            "fantasy": "The hero gathered their companions for the perilous quest.",
            "romance": "Their hearts raced as they faced each other after years apart.",
            "thriller": "Every second counted as they raced against the clock.",
            "non-fiction": "The implications were profound and far-reaching."
        }

        action = actions.get(project.genre.lower(), "Important events unfolded.")
        content_parts.append(f"\n\n{action} ")

        content_parts.append('\n\n"Heading out?" she asked, noticing his packed bag.')
        content_parts.append('\n\n"I have to," he replied. "There\'s no choice."')

        developments = {
            "mystery": "Each clue led to more questions than answers.",
            "sci-fi": "The technology they discovered would change everything.",
            "fantasy": "Ancient powers stirred from their slumber.",
            "romance": "Old feelings resurfaced despite everything.",
            "thriller": "The stakes were higher than anyone imagined.",
            "non-fiction": "The research revealed surprising insights."
        }

        development = developments.get(project.genre.lower(), "The situation grew more complex.")
        content_parts.append(f"\n\n{development} ")
        content_parts.append("As night fell, they knew the real challenge was just beginning.")

        return ''.join(content_parts)

    def _generate_basic_chapter(self, project: BookProject, chapter_number: int) -> str:
        """Generate basic chapter content"""
        return f"""# Chapter {chapter_number}: {project.title} Continues

The story unfolds as our characters face new challenges.

## Scene 1: Morning Reflections

The dawn broke over the landscape, painting everything in golden hues. {project.characters[0].name if project.characters else 'The protagonist'} stood by the window, lost in thought.

"What are we going to do?" asked {project.characters[1].name if len(project.characters) > 1 else 'their companion'}.

## Scene 2: Decision Time

The weight of the decision hung heavy in the air. Every choice had consequences, and the path forward was unclear.

## Scene 3: Moving Forward

Despite the uncertainty, they knew they had to act. The adventure continued, leading them toward an uncertain but exciting future.

---

*End of Chapter {chapter_number}*
"""

    def edit_chapter(self, project_name: str, chapter_number: int,
                     edit_type: str = "grammar") -> str:
        """Edit a chapter for various issues"""
        if project_name not in self.projects:
            return "Project not found"

        project = self.projects[project_name]
        if chapter_number > len(project.chapters):
            return "Chapter not found"

        chapter = project.chapters[chapter_number - 1]
        original_content = chapter.content

        log.info("Editing Chapter %s (%s)", chapter_number, edit_type)

        if edit_type == "grammar":
            edited_content = self._fix_grammar(original_content)
        elif edit_type == "style":
            edited_content = self._improve_style(original_content)
        elif edit_type == "pacing":
            edited_content = self._adjust_pacing(original_content)
        else:
            edited_content = original_content

        chapter.content = edited_content
        chapter.word_count = len(edited_content.split())
        project.last_modified = time.time()

        self._save_project(project)

        changes = len(original_content) - len(edited_content)
        log.info("Chapter edited (%s characters %s)",
                 abs(changes), 'removed' if changes > 0 else 'added' if changes < 0 else 'unchanged')

        return f"Chapter {chapter_number} edited successfully. Changes: {abs(changes)} characters"

    def _fix_grammar(self, content: str) -> str:
        """Fix common grammar issues"""
        fixes = [
            (r'\bi\b', 'I'),
            (r'(\w)\s*\,\s*', r'\1, '),
            (r'(\w)\s*\.\s*', r'\1. '),
            (r'\s+\.', '.'),
            (r'\s+,', ','),
        ]
        for pattern, replacement in fixes:
            content = re.sub(pattern, replacement, content)
        return content

    def _improve_style(self, content: str) -> str:
        """Improve writing style"""
        passive_to_active = [
            (r'was\s+(\w+ed)', r'\1'),
            (r'has been\s+(\w+ed)', r'\1s'),
        ]
        for pattern, replacement in passive_to_active:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        return content

    def _adjust_pacing(self, content: str) -> str:
        """Adjust narrative pacing"""
        paragraphs = content.split('\n\n')
        adjusted_paragraphs = []

        for para in paragraphs:
            if len(para) > 500:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                mid = len(sentences) // 2
                adjusted_paragraphs.append(' '.join(sentences[:mid]))
                adjusted_paragraphs.append(' '.join(sentences[mid:]))
            else:
                adjusted_paragraphs.append(para)

        return '\n\n'.join(adjusted_paragraphs)

    def analyze_writing_style(self, project_name: str) -> Dict:
        """Analyze the writing style of the project"""
        if project_name not in self.projects:
            return {"error": "Project not found"}

        project = self.projects[project_name]
        all_content = ' '.join([ch.content for ch in project.chapters if ch.content])

        if not all_content:
            return {"error": "No content to analyze"}

        words = all_content.split()
        sentences = re.split(r'[.!?]+', all_content)

        analysis = {
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "avg_sentence_length": len(words) / max(len([s for s in sentences if s.strip()]), 1),
            "avg_word_length": sum(len(w) for w in words) / max(len(words), 1),
            "unique_words": len(set(words)),
            "vocabulary_richness": len(set(words)) / max(len(words), 1),
            "paragraphs": all_content.count('\n\n') + 1,
            "genre_consistency": self._check_genre_consistency(project, all_content)
        }

        return analysis

    def _check_genre_consistency(self, project: BookProject, content: str) -> float:
        """Check how consistent the writing is with the chosen genre"""
        genre_elements = self.writing_styles.get(project.genre.lower(), [])
        if not genre_elements:
            return 0.5

        genre_keywords = {
            "mystery": ["clue", "detective", "suspect", "investigate", "mystery", "crime"],
            "sci-fi": ["space", "future", "technology", "alien", "robot", "galaxy"],
            "fantasy": ["magic", "dragon", "kingdom", "wizard", "spell", "quest"],
            "romance": ["love", "heart", "relationship", "kiss", "emotion", "feeling"],
            "thriller": ["danger", "chase", "secret", "threat", "suspense", "race"],
            "non-fiction": ["research", "study", "evidence", "analysis", "findings", "data"]
        }

        keywords = genre_keywords.get(project.genre.lower(), [])
        content_lower = content.lower()
        matches = sum(1 for keyword in keywords if keyword in content_lower)

        return min(matches / len(keywords), 1.0) if keywords else 0.5

    def generate_publishing_package(self, project_name: str, format_type: str = "epub") -> str:
        """Generate a publishing-ready package"""
        if project_name not in self.projects:
            return "Project not found"

        project = self.projects[project_name]
        project_path = Path(project.project_path)

        log.info("Generating %s package for %s", format_type, project_name)

        publish_dir = project_path / "publishing"
        publish_dir.mkdir(exist_ok=True)

        front_matter = self._generate_front_matter(project)

        all_content = [front_matter]
        for chapter in project.chapters:
            if chapter.content:
                all_content.append(f"\n\n{chapter.content}")

        complete_text = ''.join(all_content)

        if format_type.lower() == "epub":
            out_file = publish_dir / f"{project.title.replace(' ', '_')}.epub.txt"
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(complete_text)
            result = f"EPUB package saved to {out_file}"
        elif format_type.lower() == "pdf":
            out_file = publish_dir / f"{project.title.replace(' ', '_')}.pdf.txt"
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(complete_text)
            result = f"PDF package saved to {out_file}"
        else:
            out_file = publish_dir / f"{project.title.replace(' ', '_')}.txt"
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(complete_text)
            result = f"Text package saved to {out_file}"

        project.status = "complete"
        project.last_modified = time.time()
        self._save_project(project)

        log.info("Publishing package generated")
        return result

    def _generate_front_matter(self, project: BookProject) -> str:
        """Generate front matter for the book"""
        toc = '\n'.join([f"Chapter {i+1}: {ch.title}" for i, ch in enumerate(project.chapters)])
        return f"""{project.title.upper()}

{project.description}

by Apex AI Assistant

---

TABLE OF CONTENTS

{toc}

---

"""

    def get_project_status(self, project_name: str) -> Dict:
        """Get detailed status of a project"""
        if project_name not in self.projects:
            return {"error": "Project not found"}

        project = self.projects[project_name]

        total_words = sum(ch.word_count for ch in project.chapters)
        target_words = project.word_target
        completion_percentage = (total_words / target_words * 100) if target_words > 0 else 0

        return {
            "title": project.title,
            "status": project.status,
            "progress": f"{project.progress * 100:.1f}%",
            "words_written": total_words,
            "words_target": target_words,
            "completion_percentage": f"{completion_percentage:.1f}%",
            "chapters_completed": len([ch for ch in project.chapters if ch.content]),
            "total_chapters": len(project.chapters),
            "characters": len(project.characters),
            "themes": project.themes,
            "last_modified": time.ctime(project.last_modified)
        }

    def _save_project(self, project: BookProject):
        """Save project to file"""
        try:
            project_path = Path(project.project_path)
            config_file = project_path / "project.json"

            project_dict = asdict(project)

            project_dict['chapters'] = [asdict(chapter) for chapter in project.chapters]
            project_dict['characters'] = [asdict(character) for character in project.characters]

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(project_dict, f, indent=2, ensure_ascii=False)

        except Exception as e:
            log.error("Failed to save project %s: %s", project.title, e)

    def load_projects(self):
        """Load existing projects from disk"""
        try:
            for project_dir in self.projects_dir.iterdir():
                if project_dir.is_dir():
                    config_file = project_dir / "project.json"
                    if config_file.exists():
                        try:
                            with open(config_file, 'r', encoding='utf-8') as f:
                                project_data = json.load(f)

                            chapters = [Chapter(**cd) for cd in project_data.get('chapters', [])]
                            characters = [Character(**cd) for cd in project_data.get('characters', [])]

                            project = BookProject(
                                title=project_data['title'],
                                genre=project_data['genre'],
                                description=project_data['description'],
                                target_audience=project_data['target_audience'],
                                word_target=project_data['word_target'],
                                chapters=chapters,
                                characters=characters,
                                themes=project_data['themes'],
                                setting=project_data['setting'],
                                timeline=project_data['timeline'],
                                tone=project_data['tone'],
                                created_at=project_data['created_at'],
                                last_modified=project_data['last_modified'],
                                project_path=project_data['project_path'],
                                status=project_data['status'],
                                progress=project_data['progress']
                            )

                            self.projects[project.title] = project
                            log.info("Loaded project: %s", project.title)

                        except Exception as e:
                            log.error("Failed to load project from %s: %s", config_file, e)

        except Exception as e:
            log.error("Failed to scan projects directory: %s", e)


_book_writing_ai = None


def get_book_writing_ai() -> BookWritingAI:
    """Get or create the singleton BookWritingAI instance"""
    global _book_writing_ai
    if _book_writing_ai is None:
        _book_writing_ai = BookWritingAI()
    return _book_writing_ai


def register_tools(registry) -> None:
    """Register book writing tools with the agent registry"""
    writer = get_book_writing_ai()

    registry.register("tools_create_book_project", writer.create_book_project)
    registry.register("tools_generate_outline", writer.generate_outline)
    registry.register("tools_create_characters", writer.create_characters)
    registry.register("tools_write_chapter_draft", writer.write_chapter_draft)
    registry.register("tools_edit_chapter", writer.edit_chapter)
    registry.register("tools_analyze_writing_style", writer.analyze_writing_style)
    registry.register("tools_generate_publishing_package", writer.generate_publishing_package)
    registry.register("tools_get_project_status", writer.get_project_status)
