"""Fluent SSML builder for pyagentvox.

Provides a chainable API for constructing SSML documents with support for
prosody, emphasis, breaks, phonemes, and Azure express-as emotion styles.

Usage:
    ssml = (
        SSMLBuilder()
        .voice('en-US-AriaNeural')
        .say('Hello!')
        .emotion('cheerful')
        .say("I'm so happy to see you!")
        .pause(500)
        .say('How are you today?')
        .build()
    )
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from enum import Enum

from pyagentvox.constants import EmotionStyle

__all__ = ['SSMLBuilder']


class _NodeType(Enum):
    """Types of SSML nodes in the builder tree."""

    TEXT = 'text'
    BREAK = 'break'
    EMPHASIS = 'emphasis'
    PROSODY = 'prosody'
    EXPRESS_AS = 'express-as'
    PHONEME = 'phoneme'
    SAY_AS = 'say-as'
    SUB = 'sub'


@dataclass
class _SSMLNode:
    """Internal representation of an SSML element."""

    node_type: _NodeType
    text: str = ''
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[_SSMLNode] = field(default_factory=list)


class SSMLBuilder:
    """Fluent builder for constructing SSML documents.

    Supports chaining calls to build complex SSML with emotions, prosody,
    breaks, emphasis, and more. The built SSML is compatible with both
    Edge and Azure TTS backends.

    Example:
        ssml = (
            SSMLBuilder()
            .voice('en-US-AriaNeural')
            .say('Hello')
            .emotion('cheerful')
            .say('Great to see you!')
            .build()
        )
    """

    def __init__(self) -> None:
        self._voice_name: str = ''
        self._lang: str = 'en-US'
        self._nodes: list[_SSMLNode] = []
        self._current_prosody: dict[str, str] | None = None
        self._current_emotion: str | None = None
        self._current_emotion_degree: float | None = None

    def voice(self, name: str) -> SSMLBuilder:
        """Set the voice for synthesis.

        Args:
            name: Voice short name (e.g., 'en-US-AriaNeural').

        Returns:
            Self for chaining.
        """
        self._voice_name = name
        # Infer language from voice name
        parts = name.split('-')
        if len(parts) >= 2:
            self._lang = f'{parts[0]}-{parts[1]}'
        return self

    def lang(self, language: str) -> SSMLBuilder:
        """Set the language/locale.

        Args:
            language: Language code (e.g., 'en-US').

        Returns:
            Self for chaining.
        """
        self._lang = language
        return self

    def say(self, text: str) -> SSMLBuilder:
        """Add text to be spoken.

        If an emotion or prosody context is active, the text is wrapped
        in the appropriate SSML elements.

        Args:
            text: The text to speak.

        Returns:
            Self for chaining.
        """
        node = _SSMLNode(node_type=_NodeType.TEXT, text=text)

        # Wrap in prosody if active
        if self._current_prosody:
            node = _SSMLNode(
                node_type=_NodeType.PROSODY,
                attrs=dict(self._current_prosody),
                children=[node],
            )

        # Wrap in express-as if active
        if self._current_emotion:
            attrs = {'style': self._current_emotion}
            if self._current_emotion_degree is not None:
                attrs['styledegree'] = f'{self._current_emotion_degree:.1f}'
            node = _SSMLNode(
                node_type=_NodeType.EXPRESS_AS,
                attrs=attrs,
                children=[node] if node.node_type != _NodeType.TEXT else [],
                text=node.text if node.node_type == _NodeType.TEXT else '',
            )
            # If the inner node was prosody-wrapped, put it as child
            if node.text == '' and not node.children:
                node.children = [_SSMLNode(
                    node_type=_NodeType.PROSODY,
                    attrs=dict(self._current_prosody or {}),
                    children=[_SSMLNode(node_type=_NodeType.TEXT, text=text)],
                )]

        self._nodes.append(node)
        return self

    def emotion(self, style: str, degree: float | None = None) -> SSMLBuilder:
        """Set the emotion style for subsequent text.

        Uses Azure's mstts:express-as element. On the free Edge tier,
        the SSML builder still includes these tags but the backend
        will auto-downgrade to prosody approximations.

        Args:
            style: Emotion style name (e.g., 'cheerful', 'sad').
            degree: Style intensity from 0.01 to 2.0 (default None = 1.0).

        Returns:
            Self for chaining.
        """
        self._current_emotion = style
        self._current_emotion_degree = degree
        return self

    def no_emotion(self) -> SSMLBuilder:
        """Clear the current emotion context.

        Returns:
            Self for chaining.
        """
        self._current_emotion = None
        self._current_emotion_degree = None
        return self

    def express_as(self, style: str, degree: float | None = None) -> SSMLBuilder:
        """Alias for emotion(). Sets the express-as style.

        Args:
            style: Emotion style name.
            degree: Style intensity from 0.01 to 2.0.

        Returns:
            Self for chaining.
        """
        return self.emotion(style, degree)

    def prosody(
        self,
        rate: str | None = None,
        pitch: str | None = None,
        volume: str | None = None,
    ) -> SSMLBuilder:
        """Set prosody parameters for subsequent text.

        Args:
            rate: Speaking rate (e.g., 'fast', 'slow', '+20%', '1.2').
            pitch: Voice pitch (e.g., 'high', 'low', '+10Hz', '+5%').
            volume: Volume level (e.g., 'loud', 'soft', '+20%', '90').

        Returns:
            Self for chaining.
        """
        prosody: dict[str, str] = {}
        if rate is not None:
            prosody['rate'] = rate
        if pitch is not None:
            prosody['pitch'] = pitch
        if volume is not None:
            prosody['volume'] = volume
        self._current_prosody = prosody if prosody else None
        return self

    def no_prosody(self) -> SSMLBuilder:
        """Clear the current prosody context.

        Returns:
            Self for chaining.
        """
        self._current_prosody = None
        return self

    def pause(self, ms: int) -> SSMLBuilder:
        """Insert a break/pause.

        Args:
            ms: Pause duration in milliseconds.

        Returns:
            Self for chaining.
        """
        self._nodes.append(_SSMLNode(
            node_type=_NodeType.BREAK,
            attrs={'time': f'{ms}ms'},
        ))
        return self

    def emphasis(self, text: str, level: str = 'moderate') -> SSMLBuilder:
        """Add emphasized text.

        Args:
            text: Text to emphasize.
            level: Emphasis level — 'strong', 'moderate', 'reduced', or 'none'.

        Returns:
            Self for chaining.
        """
        self._nodes.append(_SSMLNode(
            node_type=_NodeType.EMPHASIS,
            text=text,
            attrs={'level': level},
        ))
        return self

    def phoneme(self, text: str, ph: str, alphabet: str = 'ipa') -> SSMLBuilder:
        """Add text with explicit pronunciation.

        Args:
            text: The display text.
            ph: Phonetic pronunciation string.
            alphabet: Phonetic alphabet — 'ipa' or 'x-sampa'.

        Returns:
            Self for chaining.
        """
        self._nodes.append(_SSMLNode(
            node_type=_NodeType.PHONEME,
            text=text,
            attrs={'alphabet': alphabet, 'ph': ph},
        ))
        return self

    def say_as(self, text: str, interpret_as: str, format: str | None = None) -> SSMLBuilder:
        """Control how text is interpreted (numbers, dates, etc.).

        Args:
            text: The text to interpret.
            interpret_as: Interpretation type — 'cardinal', 'ordinal', 'date', 'time', etc.
            format: Optional format hint (e.g., 'mdy' for dates).

        Returns:
            Self for chaining.
        """
        attrs = {'interpret-as': interpret_as}
        if format is not None:
            attrs['format'] = format
        self._nodes.append(_SSMLNode(
            node_type=_NodeType.SAY_AS,
            text=text,
            attrs=attrs,
        ))
        return self

    def sub(self, text: str, alias: str) -> SSMLBuilder:
        """Substitute text with a spoken alias.

        Args:
            text: The display text.
            alias: What to actually speak.

        Returns:
            Self for chaining.
        """
        self._nodes.append(_SSMLNode(
            node_type=_NodeType.SUB,
            text=text,
            attrs={'alias': alias},
        ))
        return self

    def build(self, include_express_as: bool = True) -> str:
        """Build the final SSML string.

        Args:
            include_express_as: If True, include mstts:express-as elements.
                Set to False to strip emotion tags (used for Edge downgrade).

        Returns:
            Complete SSML document string.
        """
        parts: list[str] = []

        # SSML header
        parts.append('<speak version="1.0"')
        parts.append(' xmlns="http://www.w3.org/2001/10/synthesis"')
        parts.append(' xmlns:mstts="http://www.w3.org/2001/mstts"')
        parts.append(f' xml:lang="{html.escape(self._lang)}">')

        # Voice wrapper
        if self._voice_name:
            parts.append(f'<voice name="{html.escape(self._voice_name)}">')

        # Render nodes
        for node in self._nodes:
            parts.append(self._render_node(node, include_express_as))

        # Close voice
        if self._voice_name:
            parts.append('</voice>')

        parts.append('</speak>')
        return ''.join(parts)

    def build_for_edge(self) -> str:
        """Build SSML optimized for the free Edge endpoint.

        Strips express-as tags since Edge doesn't support them,
        and converts emotion hints to prosody approximations.

        Returns:
            Edge-compatible SSML document string.
        """
        return self.build(include_express_as=False)

    def _render_node(self, node: _SSMLNode, include_express_as: bool) -> str:
        """Render a single SSML node to string.

        Args:
            node: The node to render.
            include_express_as: Whether to include express-as elements.

        Returns:
            SSML string fragment.
        """
        match node.node_type:
            case _NodeType.TEXT:
                return html.escape(node.text)

            case _NodeType.BREAK:
                time_attr = node.attrs.get('time', '500ms')
                return f'<break time="{html.escape(time_attr)}"/>'

            case _NodeType.EMPHASIS:
                level = node.attrs.get('level', 'moderate')
                return f'<emphasis level="{html.escape(level)}">{html.escape(node.text)}</emphasis>'

            case _NodeType.PROSODY:
                attrs_str = ' '.join(
                    f'{k}="{html.escape(v)}"' for k, v in node.attrs.items()
                )
                inner = ''.join(self._render_node(c, include_express_as) for c in node.children)
                return f'<prosody {attrs_str}>{inner}</prosody>'

            case _NodeType.EXPRESS_AS:
                if include_express_as:
                    style = node.attrs.get('style', '')
                    degree = node.attrs.get('styledegree', '')
                    attrs_str = f'style="{html.escape(style)}"'
                    if degree:
                        attrs_str += f' styledegree="{html.escape(degree)}"'
                    inner = node.text if node.text else ''.join(
                        self._render_node(c, include_express_as) for c in node.children
                    )
                    if node.text:
                        inner = html.escape(inner)
                    return f'<mstts:express-as {attrs_str}>{inner}</mstts:express-as>'
                else:
                    # Downgrade: render children without express-as wrapper
                    if node.text:
                        return html.escape(node.text)
                    return ''.join(
                        self._render_node(c, include_express_as) for c in node.children
                    )

            case _NodeType.PHONEME:
                alphabet = node.attrs.get('alphabet', 'ipa')
                ph = node.attrs.get('ph', '')
                return (
                    f'<phoneme alphabet="{html.escape(alphabet)}" ph="{html.escape(ph)}">'
                    f'{html.escape(node.text)}</phoneme>'
                )

            case _NodeType.SAY_AS:
                attrs_str = ' '.join(
                    f'{k}="{html.escape(v)}"' for k, v in node.attrs.items()
                )
                return f'<say-as {attrs_str}>{html.escape(node.text)}</say-as>'

            case _NodeType.SUB:
                alias = node.attrs.get('alias', '')
                return f'<sub alias="{html.escape(alias)}">{html.escape(node.text)}</sub>'

            case _:
                return ''
