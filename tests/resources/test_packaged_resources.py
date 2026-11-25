from __future__ import annotations

from importlib.resources import files

from ada_sensei.exams.instructions import InstructionsLoader
from ada_sensei.toolchain.policy import DEFAULT_POLICY_PATH, load_policy


def test_packaged_instructions_are_readable():
    document = InstructionsLoader().load_package("es-CO")
    assert "# Instrucciones del examen" in document.text


def test_packaged_learning_resources_are_readable():
    root = files("ada_sensei.config_data")
    for name in (
        "stages.en.json",
        "stages.es.json",
        "stage-rubrics.en.json",
        "progression-policy.en.json",
    ):
        assert root.joinpath(name).is_file()


def test_packaged_exam_schema_and_toolchain_policy_are_readable():
    schema = files("ada_sensei.exams").joinpath(
        "schemas/exam-definition.schema.json"
    )
    assert schema.is_file()
    assert DEFAULT_POLICY_PATH.is_file()
    assert load_policy().policy_version
