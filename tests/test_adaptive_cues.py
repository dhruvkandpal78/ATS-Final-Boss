from src.modules import module_c
from src.core.review_policy import POLICY_VERSION
from scripts.check_adaptive_cues import CASES, run_diagnostic


def test_adaptive_cue_diagnostic_is_lexical_only_and_does_not_initialize_model(monkeypatch):
    def forbidden_model_init(*args, **kwargs):
        raise AssertionError("diagnostic must not initialize a sentence-transformer")

    monkeypatch.setattr(module_c, "SentenceTransformer", forbidden_model_init)
    result = run_diagnostic()

    assert result["scope"] == {"model_inference": False, "lexical_only": True}
    assert len(result["cases"]) == len(CASES)
    assert result["policy_version"] == POLICY_VERSION
    assert result["misses"] == [
        "rank_first_paraphrase", "hire_paraphrase", "mixed_cyrillic_homoglyph",
        "spanish_instruction", "hindi_instruction", "base64_instruction",
        "split_across_sentence",
    ]
    assert result["benign_false_positives"] == []
