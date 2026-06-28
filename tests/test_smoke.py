import pathlib

def test_repository():
    assert pathlib.Path("bot.py").exists()