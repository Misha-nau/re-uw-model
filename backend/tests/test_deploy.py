from deploy import seed_scenarios


def test_seed_preserves_edits_and_deletions(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "store"
    source.mkdir()
    (source / "sample.json").write_text("{}")
    seed_scenarios(source, destination)
    assert (destination / "sample.json").read_text() == "{}"
    (destination / "sample.json").write_text('{"edited": true}')
    seed_scenarios(source, destination)
    assert (destination / "sample.json").read_text() == '{"edited": true}'
    (destination / "sample.json").unlink()
    seed_scenarios(source, destination)
    assert not (destination / "sample.json").exists()
