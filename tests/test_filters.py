from app.processing.filters import classify_content, looks_sports_related


def test_sports_keyword_filter():
    assert looks_sports_related("Pakistan cricket team wins", "")


def test_formula_one_is_sports_related():
    assert looks_sports_related("Formula 1 Grand Prix results", "")


def test_unrelated_content_is_filtered():
    assert not looks_sports_related("New phone launch", "Latest smartphone review")


def test_video_link_is_classified():
    assert classify_content({"link": "https://example.com/highlight.mp4"}) == "video"


def test_non_video_link_defaults_to_article():
    assert classify_content({"link": "https://example.com/match-report"}) == "article"


def test_youtube_video_link_is_classified():
    assert classify_content({"link": "https://www.youtube.com/watch?v=example"}) == "video"
