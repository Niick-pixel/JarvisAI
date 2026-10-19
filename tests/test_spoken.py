"""The voice says the words, never the formatting: no emoji names, no asterisks, no URLs."""

from server.voice.spoken import for_speech


def test_emoji_and_markdown_are_not_read_aloud() -> None:
    text = (
        "## Done! 🎉\n\n* **Saved** the note 👍🏽\n"
        "1. See [the docs](https://example.com/x) or https://foo.dev/a\n"
        "Flags 🇺🇸 and ❤️ and a family 👨‍👩‍👧 too.\n```python\nprint('hi')\n```"
    )
    assert for_speech(text) == (
        "Done!\nSaved the note\nSee the docs or a link\nFlags and and a family too.\n"
        "I've put the code on screen."
    )


def test_plain_words_pass_through() -> None:
    assert (
        for_speech("It is 72°F, café open — 3 × 4 = 12.") == "It is 72°F, café open — 3 × 4 = 12."
    )
