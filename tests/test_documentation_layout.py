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
