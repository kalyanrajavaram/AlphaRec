"""
Task Detector Module - Detect user task types from behavior patterns.

Key insight: Application sequences and browsing patterns reveal the user's current task.

Examples:
  CODING: VS Code -> Terminal -> Chrome (Stack Overflow) -> VS Code
  WRITING: Notion -> Chrome (research) -> Notion -> Grammarly
  DESIGN: Figma -> Chrome (Dribbble) -> Figma

This module:
1. Extracts app switching sequences
2. Detects recurring patterns (N-gram analysis)
3. Classifies browsing by task type (URL/title analysis)
4. Combines signals into task probability distribution
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# The 7 task types
TASK_TYPES = ["coding", "research", "writing", "design", "communication", "data", "productivity"]


# ============================================================================
# APP TO TASK MAPPINGS
# ============================================================================

APP_TASK_MAPPINGS = {
    "coding": {
        "apps": [
            "visual studio code", "vs code", "code", "cursor", "pycharm", "intellij",
            "intellij idea", "webstorm", "android studio", "xcode", "sublime text",
            "atom", "vim", "neovim", "emacs", "terminal", "iterm2", "iterm",
            "warp", "hyper", "kitty", "alacritty", "datagrip", "goland", "rider",
            "clion", "rubymine", "phpstorm"
        ],
        "bundle_ids": [
            "com.microsoft.VSCode", "com.todesktop.230313mzl4w4u92",
            "com.apple.Terminal", "com.googlecode.iterm2"
        ],
        "title_patterns": [
            r"\.py$", r"\.js$", r"\.ts$", r"\.jsx$", r"\.tsx$", r"\.java$",
            r"\.swift$", r"\.go$", r"\.rs$", r"\.cpp$", r"\.c$", r"\.h$",
            r"\.rb$", r"\.php$", r"\.html$", r"\.css$", r"\.scss$", r"\.vue$",
            r"\.kt$", r"\.scala$", r"\.sh$", r"\.bash$", r"\.zsh$",
            r"debug", r"error", r"exception", r"traceback"
        ]
    },
    "writing": {
        "apps": [
            "microsoft word", "word", "google docs", "pages", "notion",
            "obsidian", "bear", "ulysses", "ia writer", "typora", "scrivener",
            "drafts", "byword", "marked", "textedit", "notes"
        ],
        "bundle_ids": [
            "com.microsoft.Word", "com.apple.Pages", "notion.id"
        ],
        "title_patterns": [
            r"document", r"\.docx?$", r"\.md$", r"\.txt$", r"draft",
            r"essay", r"article", r"blog", r"post", r"chapter"
        ]
    },
    "design": {
        "apps": [
            "figma", "sketch", "adobe photoshop", "photoshop", "adobe illustrator",
            "illustrator", "adobe xd", "canva", "affinity designer", "affinity photo",
            "pixelmator", "pixelmator pro", "procreate", "invision", "framer",
            "principle", "zeplin", "abstract"
        ],
        "bundle_ids": [
            "com.figma.Desktop", "com.bohemiancoding.sketch3"
        ],
        "title_patterns": [
            r"\.psd$", r"\.ai$", r"\.sketch$", r"\.fig$", r"\.xd$",
            r"design", r"mockup", r"prototype", r"wireframe", r"layout"
        ]
    },
    "communication": {
        "apps": [
            "slack", "microsoft teams", "teams", "discord", "zoom",
            "mail", "outlook", "gmail", "messages", "imessage", "telegram",
            "whatsapp", "signal", "facetime", "webex", "google meet",
            "skype", "loom"
        ],
        "bundle_ids": [
            "com.tinyspeck.slackmacgap", "com.microsoft.teams",
            "com.apple.mail", "us.zoom.xos"
        ],
        "title_patterns": [
            r"inbox", r"compose", r"reply", r"meeting", r"call",
            r"chat", r"message", r"dm", r"channel"
        ]
    },
    "data": {
        "apps": [
            "microsoft excel", "excel", "google sheets", "numbers",
            "tableau", "power bi", "datagrip", "dbeaver", "postico",
            "sequel pro", "tableplus", "pgadmin", "mongodb compass",
            "jupyter", "rstudio", "spss", "stata"
        ],
        "bundle_ids": [
            "com.microsoft.Excel", "com.apple.iWork.Numbers"
        ],
        "title_patterns": [
            r"\.xlsx?$", r"\.csv$", r"\.json$", r"\.sql$",
            r"spreadsheet", r"dashboard", r"report", r"query", r"database"
        ]
    },
    "productivity": {
        "apps": [
            "todoist", "things", "things 3", "ticktick", "omnifocus",
            "asana", "monday", "trello", "linear", "clickup", "basecamp",
            "calendar", "fantastical", "busycal", "reminders", "evernote",
            "onenote", "apple notes", "1password", "bitwarden"
        ],
        "bundle_ids": [
            "com.culturedcode.ThingsMac", "com.todoist.mac.Todoist"
        ],
        "title_patterns": [
            r"task", r"todo", r"reminder", r"calendar", r"schedule",
            r"project", r"sprint", r"kanban", r"board"
        ]
    },
    "research": {
        # Research is mainly detected through browsing, not apps
        "apps": [],
        "bundle_ids": [],
        "title_patterns": [
            r"search", r"results", r"wikipedia", r"research"
        ]
    }
}


# ============================================================================
# DOMAIN TO TASK MAPPINGS
# ============================================================================

DOMAIN_TASK_MAPPINGS = {
    "coding": {
        "domains": [
            "github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com",
            "stackexchange.com", "docs.python.org", "developer.mozilla.org",
            "npmjs.com", "pypi.org", "crates.io", "pkg.go.dev", "rubygems.org",
            "nuget.org", "codesandbox.io", "repl.it", "codepen.io", "jsfiddle.net",
            "leetcode.com", "hackerrank.com", "codewars.com", "exercism.org",
            "docs.rs", "devdocs.io", "hackernews.com", "dev.to"
        ],
        "url_patterns": [
            r"/issues/", r"/pull/", r"/commit/", r"/blob/", r"/tree/",
            r"api\.", r"docs\.", r"/documentation/", r"/reference/",
            r"/questions/\d+", r"/a/\d+"  # Stack Overflow patterns
        ]
    },
    "research": {
        "domains": [
            "scholar.google.com", "arxiv.org", "researchgate.net", "academia.edu",
            "jstor.org", "pubmed.ncbi.nlm.nih.gov", "nature.com", "sciencedirect.com",
            "wikipedia.org", "britannica.com", "wolframalpha.com", "quora.com",
            "reddit.com", "news.ycombinator.com"
        ],
        "url_patterns": [
            r"/search\?", r"/wiki/", r"/article/", r"/paper/",
            r"q=", r"query="
        ]
    },
    "writing": {
        "domains": [
            "docs.google.com", "medium.com", "substack.com", "wordpress.com",
            "blogger.com", "ghost.io", "notion.so", "grammarly.com",
            "hemingwayapp.com", "prowritingaid.com"
        ],
        "url_patterns": [
            r"/document/d/", r"/edit", r"/draft", r"/new", r"/compose",
            r"/write", r"/editor"
        ]
    },
    "design": {
        "domains": [
            "figma.com", "canva.com", "dribbble.com", "behance.net",
            "unsplash.com", "pexels.com", "coolors.co", "fonts.google.com",
            "fontawesome.com", "iconify.design", "flaticon.com", "pinterest.com",
            "awwwards.com", "siteinspire.com"
        ],
        "url_patterns": [
            r"/design/", r"/prototype/", r"/file/", r"/colors?/",
            r"/fonts?/", r"/icons?/"
        ]
    },
    "communication": {
        "domains": [
            "mail.google.com", "outlook.office.com", "outlook.live.com",
            "slack.com", "teams.microsoft.com", "zoom.us", "meet.google.com",
            "discord.com", "linkedin.com", "twitter.com", "x.com"
        ],
        "url_patterns": [
            r"/inbox", r"/messages", r"/chat", r"/meeting", r"/call",
            r"/dm", r"/channel"
        ]
    },
    "data": {
        "domains": [
            "docs.google.com/spreadsheets", "airtable.com", "tableau.com",
            "looker.com", "metabase.com", "kaggle.com", "databricks.com",
            "snowflake.com", "amplitude.com", "mixpanel.com"
        ],
        "url_patterns": [
            r"/dashboard", r"/chart", r"/analytics", r"/report",
            r"/spreadsheet", r"/dataset"
        ]
    },
    "productivity": {
        "domains": [
            "notion.so", "todoist.com", "asana.com", "monday.com",
            "trello.com", "linear.app", "clickup.com", "calendar.google.com",
            "basecamp.com", "coda.io", "airtable.com"
        ],
        "url_patterns": [
            r"/board", r"/task", r"/project", r"/calendar", r"/sprint",
            r"/backlog", r"/kanban"
        ]
    }
}


# ============================================================================
# TITLE KEYWORDS FOR TASK INFERENCE
# ============================================================================

TITLE_KEYWORDS = {
    "coding": [
        "error", "debug", "function", "class", "api", "bug", "fix",
        "implement", "refactor", "test", "deploy", "build", "compile",
        "syntax", "runtime", "exception", "stack trace", "npm", "pip",
        "git", "commit", "merge", "branch", "pull request"
    ],
    "research": [
        "how to", "what is", "why does", "tutorial", "guide", "learn",
        "introduction", "overview", "explained", "understanding", "best practices",
        "comparison", "vs", "review", "analysis"
    ],
    "writing": [
        "draft", "document", "article", "blog", "post", "essay",
        "chapter", "outline", "edit", "revise", "proofread", "grammar"
    ],
    "design": [
        "design", "mockup", "wireframe", "prototype", "ui", "ux",
        "layout", "color", "font", "icon", "logo", "brand", "style"
    ],
    "communication": [
        "email", "message", "reply", "meeting", "call", "schedule",
        "invite", "agenda", "discussion", "feedback", "review"
    ],
    "data": [
        "data", "chart", "graph", "table", "spreadsheet", "dashboard",
        "report", "metric", "kpi", "analysis", "visualization", "sql", "query"
    ],
    "productivity": [
        "task", "todo", "reminder", "deadline", "project", "plan",
        "goal", "milestone", "progress", "status", "priority"
    ]
}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class AppSwitchEvent:
    """A single app switch with context."""
    app_name: str
    bundle_id: str
    window_title: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: int
    inferred_task: Optional[str] = None
    task_confidence: float = 0.0

    def __repr__(self):
        return f"App({self.app_name[:20]}, {self.duration_seconds}s, {self.inferred_task})"


@dataclass
class AppSequencePattern:
    """A detected recurring pattern of app switches."""
    sequence: List[str]  # Normalized app names
    occurrences: int
    total_duration: int  # Total seconds across all occurrences
    avg_duration: float
    task_distribution: Dict[str, float]  # Probability over task types
    examples: List[Tuple[datetime, List[AppSwitchEvent]]] = field(default_factory=list)

    def __repr__(self):
        seq_str = " -> ".join(self.sequence)
        return f"Pattern({seq_str}, {self.occurrences}x)"


@dataclass
class PageContext:
    """Context extracted from a webpage visit."""
    url: str
    domain: str
    title: str
    task_type: str
    task_confidence: float
    duration_seconds: int
    active_duration_seconds: int
    visit_time: Optional[datetime] = None
    keywords: List[str] = field(default_factory=list)

    def __repr__(self):
        return f"Page({self.domain[:20]}, {self.task_type}, {self.duration_seconds}s)"


@dataclass
class TaskInference:
    """Task inference for a time window."""
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    task_distribution: Dict[str, float]  # {coding: 0.7, research: 0.2, ...}
    dominant_task: str
    confidence: float
    contributing_signals: List[str]
    app_patterns: List[AppSequencePattern] = field(default_factory=list)
    page_contexts: List[PageContext] = field(default_factory=list)


@dataclass
class TaskDetectionResult:
    """Full result from task detection analysis."""
    overall_distribution: Dict[str, float]
    dominant_task: str
    confidence: float
    detected_patterns: List[AppSequencePattern]
    page_summary: Dict[str, int]  # Task type -> count of pages
    time_breakdown: Dict[str, int]  # Task type -> seconds spent
    app_events: List[AppSwitchEvent]
    contributing_signals: List[str]


# ============================================================================
# TASK DETECTOR CLASS
# ============================================================================

class TaskDetector:
    """
    Detects user task types from application usage and browsing behavior.

    Pipeline:
    1. Extract app switch events from application_usage
    2. Detect recurring app sequences (N-grams)
    3. Classify pages by task type (URL + title analysis)
    4. Combine signals with time weighting
    5. Output probability distribution over 7 task types
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        task_config = config.get("task_detection", {})

        # Pattern detection settings
        pattern_config = task_config.get("patterns", {})
        self.min_occurrences = pattern_config.get("min_occurrences", 3)
        self.max_ngram_size = pattern_config.get("max_ngram_size", 4)
        self.max_gap_seconds = pattern_config.get("max_gap_seconds", 60)

        # Signal weights
        weights = task_config.get("signal_weights", {})
        self.weight_app_duration = weights.get("app_duration", 0.40)
        self.weight_page_context = weights.get("page_context", 0.35)
        self.weight_patterns = weights.get("patterns", 0.15)
        self.weight_window_titles = weights.get("window_titles", 0.10)

    def _parse_timestamp(self, ts: str) -> Optional[datetime]:
        """Parse timestamp string to datetime."""
        if not ts:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]

        ts_clean = ts.replace("+00:00", "").replace("Z", "")

        for fmt in formats:
            fmt_clean = fmt.replace("Z", "")
            try:
                return datetime.strptime(ts_clean, fmt_clean)
            except ValueError:
                continue
        return None

    def _normalize_app_name(self, app_name: str) -> str:
        """Normalize app name for pattern matching."""
        if not app_name:
            return "unknown"

        name = app_name.lower().strip()

        # Common normalizations
        normalizations = {
            "google chrome": "chrome",
            "safari": "safari",
            "firefox": "firefox",
            "visual studio code": "vscode",
            "vs code": "vscode",
            "code": "vscode",
            "microsoft word": "word",
            "microsoft excel": "excel",
            "microsoft teams": "teams",
            "iterm2": "terminal",
            "iterm": "terminal",
            "warp": "terminal",
            "hyper": "terminal",
        }

        return normalizations.get(name, name)

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url:
            return ""

        try:
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
            else:
                domain = url.split("/")[0]
            return domain.lower()
        except:
            return ""

    def _infer_app_task(self, event: AppSwitchEvent) -> str:
        """Infer task type from an app switch event."""
        app_lower = event.app_name.lower() if event.app_name else ""
        bundle_lower = event.bundle_id.lower() if event.bundle_id else ""
        title_lower = event.window_title.lower() if event.window_title else ""

        scores = {task: 0.0 for task in TASK_TYPES}

        for task, mapping in APP_TASK_MAPPINGS.items():
            # Check app name
            for app in mapping.get("apps", []):
                if app in app_lower:
                    scores[task] += 10.0
                    break

            # Check bundle ID
            for bundle in mapping.get("bundle_ids", []):
                if bundle.lower() in bundle_lower:
                    scores[task] += 8.0
                    break

            # Check window title patterns
            for pattern in mapping.get("title_patterns", []):
                if re.search(pattern, title_lower, re.I):
                    scores[task] += 5.0
                    break

        # If browser, need to check further (could be any task)
        browser_names = ["chrome", "safari", "firefox", "arc", "brave", "edge"]
        is_browser = any(b in app_lower for b in browser_names)

        if is_browser:
            # Browsers are ambiguous - reduce confidence and mark as research by default
            scores["research"] += 3.0

        # Find best task
        best_task = max(scores.items(), key=lambda x: x[1])

        if best_task[1] > 0:
            event.inferred_task = best_task[0]
            event.task_confidence = min(best_task[1] / 15.0, 1.0)
        else:
            event.inferred_task = "productivity"  # Default
            event.task_confidence = 0.3

        return event.inferred_task

    def _infer_task_from_title(self, title: str) -> Optional[str]:
        """Infer task from window title using keywords."""
        if not title:
            return None

        title_lower = title.lower()
        scores = {task: 0 for task in TASK_TYPES}

        for task, keywords in TITLE_KEYWORDS.items():
            for kw in keywords:
                if kw in title_lower:
                    scores[task] += 1

        best = max(scores.items(), key=lambda x: x[1])
        return best[0] if best[1] > 0 else None

    def extract_app_events(self, user_data: Dict[str, Any]) -> List[AppSwitchEvent]:
        """Extract app switch events from user data."""
        events = []

        for entry in user_data.get("application_usage", []):
            start_time = self._parse_timestamp(entry.get("start_time", ""))
            end_time = self._parse_timestamp(entry.get("end_time", ""))
            duration = entry.get("duration_seconds", 0) or 0

            if not start_time:
                continue

            event = AppSwitchEvent(
                app_name=entry.get("app_name", ""),
                bundle_id=entry.get("app_bundle_id", ""),
                window_title=entry.get("window_title", ""),
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration
            )

            # Infer task for this event
            self._infer_app_task(event)
            events.append(event)

        # Sort by start time
        events.sort(key=lambda e: e.start_time)

        return events

    def detect_patterns(self, events: List[AppSwitchEvent]) -> List[AppSequencePattern]:
        """
        Detect recurring app switching patterns using N-gram analysis.

        Algorithm:
        1. Normalize app names
        2. Extract N-grams of size 2, 3, 4
        3. Count occurrences with time constraints
        4. Filter by minimum occurrences
        5. Calculate task distribution for each pattern
        """
        if len(events) < 2:
            return []

        # Build timeline of normalized apps
        timeline = []
        for event in events:
            timeline.append({
                "app": self._normalize_app_name(event.app_name),
                "task": event.inferred_task or "productivity",
                "time": event.start_time,
                "duration": event.duration_seconds,
                "event": event
            })

        # Extract N-grams with time constraints
        pattern_instances = defaultdict(list)

        for n in range(2, self.max_ngram_size + 1):
            for i in range(len(timeline) - n + 1):
                window = timeline[i:i + n]

                # Check time gap constraint between consecutive apps
                valid_gaps = True
                for j in range(n - 1):
                    gap = (window[j + 1]["time"] - window[j]["time"]).total_seconds()
                    # Subtract duration of previous app
                    actual_gap = gap - window[j]["duration"]
                    if actual_gap > self.max_gap_seconds:
                        valid_gaps = False
                        break

                if not valid_gaps:
                    continue

                # Create pattern key (tuple of app names)
                pattern_key = tuple(w["app"] for w in window)

                # Skip if all same app (not interesting)
                if len(set(pattern_key)) == 1:
                    continue

                pattern_instances[pattern_key].append({
                    "timestamp": window[0]["time"],
                    "events": [w["event"] for w in window],
                    "tasks": [w["task"] for w in window],
                    "total_duration": sum(w["duration"] for w in window)
                })

        # Filter by minimum occurrences and build patterns
        patterns = []

        for pattern_key, instances in pattern_instances.items():
            if len(instances) < self.min_occurrences:
                continue

            # Calculate task distribution
            task_counts = defaultdict(int)
            total_duration = 0

            for instance in instances:
                for task in instance["tasks"]:
                    task_counts[task] += 1
                total_duration += instance["total_duration"]

            total_tasks = sum(task_counts.values())
            task_distribution = {
                task: count / total_tasks
                for task, count in task_counts.items()
            }

            patterns.append(AppSequencePattern(
                sequence=list(pattern_key),
                occurrences=len(instances),
                total_duration=total_duration,
                avg_duration=total_duration / len(instances),
                task_distribution=task_distribution,
                examples=[(inst["timestamp"], inst["events"]) for inst in instances[:3]]
            ))

        # Sort by occurrence count (descending)
        patterns.sort(key=lambda p: (p.occurrences, len(p.sequence)), reverse=True)

        # Remove subsumed patterns (e.g., A->B subsumed by A->B->C if same occurrences)
        return self._filter_subsumed_patterns(patterns)

    def _filter_subsumed_patterns(self, patterns: List[AppSequencePattern]) -> List[AppSequencePattern]:
        """Remove patterns that are subsumed by longer patterns."""
        if not patterns:
            return []

        filtered = []
        pattern_seqs = set()

        for pattern in patterns:
            seq_tuple = tuple(pattern.sequence)

            # Check if this pattern is a subsequence of an already kept longer pattern
            is_subsumed = False
            for kept_seq in pattern_seqs:
                if len(kept_seq) > len(seq_tuple):
                    # Check if seq_tuple is a contiguous subsequence
                    kept_str = "|||".join(kept_seq)
                    check_str = "|||".join(seq_tuple)
                    if check_str in kept_str:
                        is_subsumed = True
                        break

            if not is_subsumed:
                filtered.append(pattern)
                pattern_seqs.add(seq_tuple)

        return filtered

    def classify_pages(self, user_data: Dict[str, Any]) -> List[PageContext]:
        """Classify each page visit by task type using URL and title analysis."""
        contexts = []

        for entry in user_data.get("browsing_history", []):
            url = entry.get("url", "")
            title = entry.get("title", "")
            domain = self._extract_domain(url)
            duration = entry.get("duration_seconds", 0) or 0
            active = entry.get("active_duration_seconds", 0) or 0
            visit_time = self._parse_timestamp(entry.get("visit_time", ""))

            scores = {task: 0.0 for task in TASK_TYPES}

            # 1. Exact domain matching (highest weight)
            for task, mapping in DOMAIN_TASK_MAPPINGS.items():
                for dom in mapping.get("domains", []):
                    if dom in url.lower():
                        scores[task] += 10.0
                        break

                # URL pattern matching
                for pattern in mapping.get("url_patterns", []):
                    if re.search(pattern, url, re.I):
                        scores[task] += 5.0
                        break

            # 2. Title keyword matching
            title_lower = title.lower()
            for task, keywords in TITLE_KEYWORDS.items():
                matches = sum(1 for kw in keywords if kw in title_lower)
                scores[task] += matches * 2.0

            # 3. Special handling for Stack Overflow (very strong coding signal)
            if "stackoverflow.com/questions" in url.lower():
                scores["coding"] += 8.0

            # 4. Special handling for Google Docs
            if "docs.google.com/document" in url.lower():
                scores["writing"] += 8.0
            elif "docs.google.com/spreadsheets" in url.lower():
                scores["data"] += 8.0

            # Normalize scores
            total = sum(scores.values())
            if total > 0:
                scores = {k: v / total for k, v in scores.items()}
            else:
                # Default: research (browsing)
                scores["research"] = 1.0

            # Find dominant task
            dominant = max(scores.items(), key=lambda x: x[1])

            # Extract keywords from title
            keywords = [kw for task, kws in TITLE_KEYWORDS.items()
                        for kw in kws if kw in title_lower]

            contexts.append(PageContext(
                url=url,
                domain=domain,
                title=title,
                task_type=dominant[0],
                task_confidence=dominant[1],
                duration_seconds=duration,
                active_duration_seconds=active,
                visit_time=visit_time,
                keywords=keywords[:5]
            ))

        return contexts

    def infer_task_distribution(
        self,
        app_events: List[AppSwitchEvent],
        page_contexts: List[PageContext],
        patterns: List[AppSequencePattern]
    ) -> TaskDetectionResult:
        """
        Combine all signals into final task probability distribution.

        Weighting:
        - App duration: 40%
        - Page context: 35%
        - Detected patterns: 15%
        - Window titles: 10%
        """
        task_scores = {task: 0.0 for task in TASK_TYPES}
        total_weight = 0.0
        contributing_signals = []
        time_breakdown = {task: 0 for task in TASK_TYPES}

        # 1. App duration contribution
        app_task_time = defaultdict(int)
        for event in app_events:
            task = event.inferred_task or "productivity"
            app_task_time[task] += event.duration_seconds
            time_breakdown[task] += event.duration_seconds

        total_app_time = sum(app_task_time.values())
        if total_app_time > 0:
            for task, duration in app_task_time.items():
                task_scores[task] += (duration / total_app_time) * self.weight_app_duration
            total_weight += self.weight_app_duration
            contributing_signals.append(f"App usage: {total_app_time}s total")

        # 2. Page context contribution (weighted by active time)
        page_task_time = defaultdict(float)
        page_counts = defaultdict(int)
        for ctx in page_contexts:
            time_weight = ctx.active_duration_seconds or ctx.duration_seconds or 1
            page_task_time[ctx.task_type] += time_weight * ctx.task_confidence
            page_counts[ctx.task_type] += 1

        total_page_time = sum(page_task_time.values())
        if total_page_time > 0:
            for task, weighted_time in page_task_time.items():
                task_scores[task] += (weighted_time / total_page_time) * self.weight_page_context
            total_weight += self.weight_page_context
            contributing_signals.append(f"Page visits: {len(page_contexts)} pages")

        # 3. Pattern contribution
        if patterns:
            pattern_task_weights = defaultdict(float)
            for pattern in patterns:
                importance = pattern.occurrences * len(pattern.sequence)
                for task, prob in pattern.task_distribution.items():
                    pattern_task_weights[task] += prob * importance

            total_pattern_weight = sum(pattern_task_weights.values())
            if total_pattern_weight > 0:
                for task, weight in pattern_task_weights.items():
                    task_scores[task] += (weight / total_pattern_weight) * self.weight_patterns
                total_weight += self.weight_patterns
                contributing_signals.append(f"Patterns: {len(patterns)} recurring sequences")

        # 4. Window title hints
        title_task_hints = defaultdict(float)
        for event in app_events:
            title_task = self._infer_task_from_title(event.window_title)
            if title_task:
                title_task_hints[title_task] += 1

        if title_task_hints:
            total_hints = sum(title_task_hints.values())
            for task, count in title_task_hints.items():
                task_scores[task] += (count / total_hints) * self.weight_window_titles
            total_weight += self.weight_window_titles
            contributing_signals.append(f"Window titles: {int(total_hints)} hints")

        # Normalize final distribution
        if total_weight > 0:
            task_distribution = {
                task: score / total_weight
                for task, score in task_scores.items()
            }
        else:
            # Default uniform
            task_distribution = {task: 1.0 / 7 for task in TASK_TYPES}

        # Find dominant task
        dominant = max(task_distribution.items(), key=lambda x: x[1])

        return TaskDetectionResult(
            overall_distribution=task_distribution,
            dominant_task=dominant[0],
            confidence=dominant[1],
            detected_patterns=patterns,
            page_summary=dict(page_counts),
            time_breakdown=time_breakdown,
            app_events=app_events,
            contributing_signals=contributing_signals
        )

    def detect(self, user_data: Dict[str, Any]) -> TaskDetectionResult:
        """
        Main entry point: detect tasks from user data.

        Returns comprehensive TaskDetectionResult with:
        - Task probability distribution
        - Detected app sequence patterns
        - Page classification summary
        - Time breakdown by task
        """
        logger.info("Extracting app events...")
        app_events = self.extract_app_events(user_data)
        logger.info(f"Found {len(app_events)} app events")

        logger.info("Detecting app sequence patterns...")
        patterns = self.detect_patterns(app_events)
        logger.info(f"Found {len(patterns)} recurring patterns")

        logger.info("Classifying page visits...")
        page_contexts = self.classify_pages(user_data)
        logger.info(f"Classified {len(page_contexts)} pages")

        logger.info("Computing task distribution...")
        result = self.infer_task_distribution(app_events, page_contexts, patterns)

        return result

    def result_to_text(self, result: TaskDetectionResult) -> str:
        """Convert result to text for display/LLM consumption."""
        lines = [
            "TASK DETECTION ANALYSIS",
            "=" * 50,
            "",
            f"Dominant Task: {result.dominant_task.upper()} ({result.confidence:.0%} confidence)",
            "",
            "Task Distribution:",
        ]

        # Sort by probability
        sorted_tasks = sorted(result.overall_distribution.items(),
                              key=lambda x: x[1], reverse=True)

        for task, prob in sorted_tasks:
            bar = "=" * int(prob * 30)
            lines.append(f"  {task:15} [{bar:30}] {prob:.0%}")

        # Time breakdown
        if any(result.time_breakdown.values()):
            lines.append("")
            lines.append("Time Spent by Task:")
            for task, seconds in sorted(result.time_breakdown.items(),
                                         key=lambda x: x[1], reverse=True):
                if seconds > 0:
                    minutes = seconds / 60
                    lines.append(f"  {task:15} {minutes:.1f} min")

        # Detected patterns
        if result.detected_patterns:
            lines.append("")
            lines.append(f"Recurring Patterns ({len(result.detected_patterns)} found):")
            for pattern in result.detected_patterns[:5]:
                seq_str = " -> ".join(pattern.sequence)
                task_str = max(pattern.task_distribution.items(), key=lambda x: x[1])[0]
                lines.append(f"  {seq_str}")
                lines.append(f"    {pattern.occurrences}x occurrences, suggests {task_str}")

        # Contributing signals
        if result.contributing_signals:
            lines.append("")
            lines.append("Contributing Signals:")
            for signal in result.contributing_signals:
                lines.append(f"  - {signal}")

        return "\n".join(lines)
