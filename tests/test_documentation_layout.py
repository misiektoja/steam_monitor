from collections import Counter
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


# Read prose without fenced code blocks that may contain example headings
def prose(path):
    return re.sub(r"^```.*?^```[^\n]*$", "", path.read_text(encoding="utf-8"), flags=re.MULTILINE | re.DOTALL)


# Prevent one page from declaring the same explicit anchor twice
def test_documentation_anchor_ids_are_unique():
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        explicit = re.findall(r'<a\s+id="([^"]+)"[^>]*>', prose(path))
        repeated = [anchor for anchor, count in Counter(explicit).items() if count > 1]
        assert not repeated, f"{path.name}: repeated explicit anchors: {repeated}"


# Keep one canonical quick-start anchor after the main image on both entry pages
def test_entry_pages_place_the_main_image_before_quick_start():
    for path in (ROOT / "README.md", ROOT / "docs/index.md"):
        text = path.read_text(encoding="utf-8")
        assert '<a id="-quick-install"></a>' not in text
        anchor = '<a id="quick-install-run"></a>'
        assert text.count(anchor) == 1
        if path.name == "README.md":
            # GitHub and PyPI both build this id from the heading, and PyPI reaches no other anchor
            assert "](#-quick-install--run)" in text
        images = [match for match in re.finditer(r'(?:src="|!\[[^\]]*\]\()([^"\s)]+/assets/[^"\s)]+)', text) if match.group(1).endswith(f"/{ROOT.name}.png")]
        assert images, f"{path.name}: no main screenshot"
        assert len(images) == 1, f"{path.name}: repeated main screenshot"
        assert images[0].start() < text.index(anchor) < text.index("## Features")


# Keep the main image and feature summary consistent between the entry pages
def test_entry_pages_share_the_main_image_and_features():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs/index.md").read_text(encoding="utf-8")
    image = r'(?:src="|!\[[^\]]*\]\()([^"\s)]+/assets/[^"\s)]+)'
    readme_image = re.search(image, readme)
    index_image = re.search(image, index)
    assert readme_image is not None and index_image is not None
    assert readme_image.group(1) == index_image.group(1)
    feature_block = r"^## Features\n(.*?)(?=^## |\Z)"
    readme_features = re.search(feature_block, readme, re.MULTILINE | re.DOTALL)
    index_features = re.search(feature_block, index, re.MULTILINE | re.DOTALL)
    assert readme_features is not None and index_features is not None
    # the README pins an anchor above the next section, docs/index.md ends the page there
    readme_block = re.sub(r'\n<a id="[^"]+"></a>\s*\Z', "", readme_features.group(1).strip()).strip()
    assert readme_block == index_features.group(1).strip()


# Keep the badge block identical on both entry pages, since a badge added to one is easy to forget on the other
def test_entry_pages_share_the_badge_block():
    blocks = []
    for path in (ROOT / "README.md", ROOT / "docs/index.md"):
        badges = re.findall(r"^\[!\[[^\]]+\]\([^)]+\)\]\([^)]+\)$", path.read_text(encoding="utf-8"), re.MULTILINE)
        assert len(badges) >= 8, f"{path.name}: expected the full badge block, found {len(badges)}"
        blocks.append(badges)
    assert blocks[0] == blocks[1]


# Every badge links somewhere, the way the sibling monitors render them, so a bare image cannot creep back in
def test_badges_are_linked_the_way_the_sibling_monitors_render_them():
    for path in (ROOT / "README.md", ROOT / "docs/index.md"):
        text = path.read_text(encoding="utf-8")
        header = text[:text.index("\n\n", text.index("shields.io"))]
        assert "<img" not in header and "<p align=" not in header, f"{path.name}: unlinked image badge in the header"


# The Scorecard badge only resolves through the scorecard.dev API, so the retired shields endpoints stay out
def test_the_scorecard_badge_uses_the_endpoint_that_resolves():
    for path in (ROOT / "README.md", ROOT / "docs/index.md"):
        text = path.read_text(encoding="utf-8")
        assert "api.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Fsteam_monitor" in text
        assert "ossf-scorecard" not in text and "securityscorecards.dev" not in text
        # A cache-buster freezes shields on the first score it fetched, so the badge stops tracking the real one
        assert "badge_cache" not in text
