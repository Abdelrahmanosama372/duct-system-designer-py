import pytest

from dsd.adapters.autocad import WriterConfig


def test_example_yaml():
    assert WriterConfig.from_yaml("examples/dsd_config.yaml").clear_layers == (
        "duct-output",
        "duct-annotations",
    )


@pytest.mark.parametrize("names", ["output", ("",), (123,)])
def test_invalid_layers(names):
    with pytest.raises(ValueError):
        WriterConfig(names)


def test_rejects_string_instead_of_layer_list():
    with pytest.raises(ValueError):
        WriterConfig.from_mapping(
            {"autocad": {"output": {"clear": {"include": "output"}}}}
        )
