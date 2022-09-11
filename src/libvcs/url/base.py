import dataclasses
from collections.abc import Iterator
from re import Pattern
from typing import TYPE_CHECKING, Optional, Protocol

from libvcs._internal.dataclasses import SkipDefaultFieldsReprMixin

if TYPE_CHECKING:
    from _collections_abc import dict_values


class URLProtocol(Protocol):
    """Common interface for VCS URL Parsers."""

    def __init__(self, url: str):
        ...

    def to_url(self) -> str:
        ...

    def is_valid(self, url: str, is_explicit: Optional[bool] = None) -> bool:
        ...


@dataclasses.dataclass(repr=False)
class Matcher(SkipDefaultFieldsReprMixin):
    """Structure for a matcher"""

    label: str
    """Computer readable name / ID"""
    description: str
    """Human readable description"""
    pattern: Pattern[str]
    """Regex pattern"""
    pattern_defaults: dict[str, str] = dataclasses.field(default_factory=dict)
    """Is the match unambiguous with other VCS systems? e.g. git+ prefix"""
    is_explicit: bool = False


@dataclasses.dataclass(repr=False)
class MatcherRegistry(SkipDefaultFieldsReprMixin):
    """Pattern matching and parsing capabilities for URL parsers, e.g. GitURL"""

    _matchers: dict[str, Matcher] = dataclasses.field(default_factory=dict)

    def register(self, cls: Matcher) -> None:
        r"""

        .. currentmodule:: libvcs.url.git

        >>> from dataclasses import dataclass
        >>> from libvcs.url.git import GitURL, GitBaseURL

        :class:`GitBaseURL` - the ``git(1)`` compliant parser - won't accept a pip-style URL:

        >>> GitBaseURL.is_valid(url="git+ssh://git@github.com/tony/AlgoXY.git")
        False

        :class:`GitURL` - the "batteries-included" parser - can do it:

        >>> GitURL.is_valid(url="git+ssh://git@github.com/tony/AlgoXY.git")
        True

        But what if you wanted to do ``github:org/repo``?

        >>> GitURL.is_valid(url="github:org/repo")
        True

        That actually works, but look, it's caught in git's standard SCP regex:

        >>> GitURL(url="github:org/repo")
        GitURL(url=github:org/repo,
           hostname=github,
           path=org/repo,
           matcher=core-git-scp)

        >>> GitURL(url="github:org/repo").to_url()
        'git@github:org/repo'

        Eek. That won't work, :abbr:`can't do much with that one ("git clone git@github:org/repo"
        wouldn't work unless your user's had "insteadOf" set.)`.

        We need something more specific so usable URLs can be generated. What do we do?

        **Extending matching capability:**

        >>> class GitHubPrefix(Matcher):
        ...     label = 'gh-prefix'
        ...     description ='Matches prefixes like github:org/repo'
        ...     pattern = r'^github:(?P<path>.*)$'
        ...     pattern_defaults = {
        ...         'hostname': 'github.com',
        ...         'scheme': 'https'
        ...     }
        ...     # We know it's git, not any other VCS
        ...     is_explicit = True

        >>> @dataclasses.dataclass(repr=False)
        ... class GitHubURL(GitURL):
        ...    matchers: MatcherRegistry = MatcherRegistry(
        ...        _matchers={'github_prefix': GitHubPrefix}
        ...    )

        >>> GitHubURL.is_valid(url='github:vcs-python/libvcs')
        True

        >>> GitHubURL.is_valid(url='github:vcs-python/libvcs', is_explicit=True)
        True

        Notice how ``pattern_defaults`` neatly fills the values for us.

        >>> GitHubURL(url='github:vcs-python/libvcs')
        GitHubURL(url=github:vcs-python/libvcs,
            scheme=https,
            hostname=github.com,
            path=vcs-python/libvcs,
            matcher=gh-prefix)

        >>> GitHubURL(url='github:vcs-python/libvcs').to_url()
        'https://github.com/vcs-python/libvcs'

        >>> GitHubURL.is_valid(url='gitlab:vcs-python/libvcs')
        False

        ``GitHubURL`` sees this as invalid since it only has one matcher,
        ``GitHubPrefix``.

        >>> GitURL.is_valid(url='gitlab:vcs-python/libvcs')
        True

        Same story, getting caught in ``git(1)``'s own liberal scp-style URL:

        >>> GitURL(url='gitlab:vcs-python/libvcs').matcher
        'core-git-scp'

        >>> class GitLabPrefix(Matcher):
        ...     label = 'gl-prefix'
        ...     description ='Matches prefixes like gitlab:org/repo'
        ...     pattern = r'^gitlab:(?P<path>)'
        ...     pattern_defaults = {
        ...         'hostname': 'gitlab.com',
        ...         'scheme': 'https',
        ...         'suffix': '.git'
        ...     }

        Option 1: Create a brand new matcher

        >>> @dataclasses.dataclass(repr=False)
        ... class GitLabURL(GitURL):
        ...     matchers: MatcherRegistry = MatcherRegistry(
        ...         _matchers={'gitlab_prefix': GitLabPrefix}
        ...     )

        >>> GitLabURL.is_valid(url='gitlab:vcs-python/libvcs')
        True

        Option 2 (global, everywhere): Add to the global :class:`GitURL`:

        >>> GitURL.is_valid(url='gitlab:vcs-python/libvcs')
        True

        Are we home free, though? Remember our issue with vague matches.

        >>> GitURL(url='gitlab:vcs-python/libvcs').matcher
        'core-git-scp'

        Register:

        >>> GitURL.matchers.register(GitLabPrefix)

        >>> GitURL.is_valid(url='gitlab:vcs-python/libvcs')
        True

        **Example: git URLs + pip-style git URLs:**

        This is already in :class:`GitURL` via :data:`PIP_DEFAULT_MATCHERS`. For the
        sake of showing how extensibility works, here is a recreation based on
        :class:`GitBaseURL`:

        >>> from libvcs.url.git import GitBaseURL

        >>> from libvcs.url.git import DEFAULT_MATCHERS, PIP_DEFAULT_MATCHERS

        >>> @dataclasses.dataclass(repr=False)
        ... class GitURLWithPip(GitBaseURL):
        ...    matchers: MatcherRegistry = MatcherRegistry(
        ...        _matchers={m.label: m for m in [*DEFAULT_MATCHERS, *PIP_DEFAULT_MATCHERS]}
        ...    )

        >>> GitURLWithPip.is_valid(url="git+ssh://git@github.com/tony/AlgoXY.git")
        True

        >>> GitURLWithPip(url="git+ssh://git@github.com/tony/AlgoXY.git")
        GitURLWithPip(url=git+ssh://git@github.com/tony/AlgoXY.git,
            scheme=git+ssh,
            user=git,
            hostname=github.com,
            path=tony/AlgoXY,
            suffix=.git,
            matcher=pip-url)
        """  # NOQA: E501
        if cls.label not in self._matchers:
            self._matchers[cls.label] = cls

    def unregister(self, label: str) -> None:
        if label in self._matchers:
            del self._matchers[label]

    def __iter__(self) -> Iterator[str]:
        return self._matchers.__iter__()

    def values(
        self,  # https://github.com/python/typing/discussions/1033
    ) -> "dict_values[str, Matcher]":
        return self._matchers.values()