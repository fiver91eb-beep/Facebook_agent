from app.processing.filters import classify_content, looks_sports_related


def test_sports_keyword_filter():
    assert looks_sports_related('Pakistan cricket team wins', '')


def test_unrelated_content_is_filtered():
    assert not looks_sports_related('New phone launch', 'Latest smartphone review')


def test_video_link_is_classified():
    assert classify_content({'link': 'https://example.com/highlight.mp4'}) == 'video'
