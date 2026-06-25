"""SentenceStreamer surfaces the emotion early and flushes complete sentences."""

from __future__ import annotations

from projectbuddy.core.streaming import SentenceStreamer


def test_emotion_appears_before_sentences_flush() -> None:
    s = SentenceStreamer()

    emo, flushed = s.feed('{"emotion":"exci')
    assert emo is None and flushed == ""  # emotion not complete yet

    emo, flushed = s.feed('ted","say":"Hi there! How')
    assert emo == "excited"  # emotion surfaced as soon as it closed
    assert flushed == "Hi there!"  # first complete sentence, mid-stream

    emo, flushed = s.feed(' are you?","remember":[]}')
    assert emo is None  # only surfaced once
    assert flushed.strip() == "How are you?"  # remainder flushed when the value closes
    assert s.say_value() == "Hi there! How are you?"


def test_handles_escaped_quotes_in_say() -> None:
    s = SentenceStreamer()
    _, _ = s.feed('{"emotion":"happy","say":"She said ')
    _, flushed = s.feed('\\"hi\\" to me.","remember":[]}')
    assert s.say_value() == 'She said "hi" to me.'
    assert '"hi"' in flushed
