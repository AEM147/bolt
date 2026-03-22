"""
Bolt AI -- Platform Adapters

Each adapter implements the same interface (transform, publish, validate_credentials)
so the distribution orchestrator can treat all platforms uniformly.

Pre-plan Section 20: "Adding a new platform requires writing one new adapter and nothing else."
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlatformPackage:
    """Output of an adapter's transform() method."""
    platform: str
    video_path: str
    title: str = ""
    caption: str = ""
    description: str = ""
    hashtags: list = field(default_factory=list)
    thumbnail_path: str = ""
    tags: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class PublicationResult:
    """Output of an adapter's publish() method. Never raises."""
    platform: str
    success: bool
    post_url: str = ""
    post_id: str = ""
    error: str = ""
    scheduled_at: str = ""


class PlatformAdapter:
    """
    Base class for platform adapters.

    Every adapter must implement:
      - transform(master_video_path, script, article, config) -> PlatformPackage
      - publish(package, config) -> PublicationResult
      - validate_credentials(config) -> bool
    """

    platform_name: str = "unknown"

    def transform(self, master_video_path: str, script: dict,
                  article: dict, config: dict) -> PlatformPackage:
        """
        Adapt the master video for this platform.
        Returns a PlatformPackage with platform-specific video, metadata, and thumbnail.
        """
        raise NotImplementedError

    def publish(self, package: PlatformPackage, config: dict) -> PublicationResult:
        """
        Post the platform package. Returns success/failure. Never raises.
        """
        raise NotImplementedError

    def validate_credentials(self, config: dict) -> bool:
        """
        Check that API credentials are configured and not placeholders.
        Called at startup, not during posting.
        """
        raise NotImplementedError
