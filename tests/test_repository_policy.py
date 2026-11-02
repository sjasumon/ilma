import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('repo_policy', Path(__file__).resolve().parents[1]/'ops/check_repo.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def test_public_boundary_rejects_private_exports_and_metadata():
    assert policy.tree_errors({'private-reference/input.csv': b'id\n1'})
    assert policy.tree_errors({'tests/fixtures/sample_export/documents.csv': b'id,local_path\n1,path'})
    assert policy.tree_errors({'.env': b'private'})
    assert policy.tree_errors({'design/error1.png': b'\x89PNG'})
    assert policy.tree_errors({'.env.example': b'META_MODEL_API_KEY=not-empty'})
    assert not policy.tree_errors({'tests/fixtures/sample_export/documents.csv': b'id,url\n1,https://www.ebl.com.bd/'})


def test_review_terms_are_neutral_and_templates_blank():
    for brand in policy.UNAPPROVED_BRANDS:
        assert policy.tree_errors({'example.md': brand.upper().encode()})
    assert not policy.tree_errors({'example.md': b'requires_manual_review', '.env.example': b'META_MODEL_API_KEY=\nDB_PASSWORD=\n'})


def test_identity_transition_preserves_only_existing_history():
    assert policy.identity_allowed('old',policy.LEGACY_AUTHOR,policy.LEGACY_AUTHOR,{'old'})
    assert policy.identity_allowed('new',policy.AUTHOR,policy.AUTHOR,{'old'})
    assert not policy.identity_allowed('new',policy.LEGACY_AUTHOR,policy.AUTHOR,{'old'})
    assert not policy.identity_allowed('new',policy.AUTHOR,policy.LEGACY_AUTHOR,{'old'})
    assert not policy.identity_allowed('old','sjasumon <unknown@example.test>',policy.AUTHOR,{'old'})


def test_short_noreply_identity_only_for_the_listed_published_commits():
    listed=next(iter(policy.LEGACY_NOREPLY_COMMITS))
    assert len(policy.LEGACY_NOREPLY_COMMITS)==15
    assert policy.identity_allowed(listed,policy.LEGACY_NOREPLY_AUTHOR,policy.LEGACY_NOREPLY_AUTHOR,set())
    assert not policy.identity_allowed('0'*40,policy.LEGACY_NOREPLY_AUTHOR,policy.LEGACY_NOREPLY_AUTHOR,set())
    assert not policy.identity_allowed(listed,policy.LEGACY_AUTHOR,policy.LEGACY_AUTHOR,set())
