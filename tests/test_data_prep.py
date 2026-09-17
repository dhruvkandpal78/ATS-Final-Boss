import pytest
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.data_prep.cleaner import normalize_text
from src.data_prep.injector import inject_type_a, inject_type_b, inject_type_c

def test_clean_text():
    raw_text = "This is a\n\n\nresume\twith multiple   spaces and special \u2022 characters!"
    cleaned = normalize_text(raw_text)
    assert "  " not in cleaned
    assert "\t" not in cleaned
    assert "\u2022" not in cleaned
    assert cleaned.strip() == cleaned

def test_inject_type_a():
    text = "Experienced software developer."
    poisoned, _ = inject_type_a(text, num_keywords=10)
    
    assert len(poisoned) > len(text)
    assert "Skills:" in poisoned or "Additional Technical Skills:" in poisoned or len(poisoned) > len(text)

def test_inject_type_b():
    text = "Software engineer resume."
    poisoned, _ = inject_type_b(text, num_keywords=10)
    
    assert "[HIDDEN_TEXT_START]" in poisoned
    assert "[HIDDEN_TEXT_END]" in poisoned

def test_inject_type_c():
    text = "I am a web developer. I have built many cool projects. I love programming in Python. This is my resume."
    poisoned, _ = inject_type_c(text, num_insertions=2)
    
    assert len(poisoned.split(". ")) > len(text.split(". "))
