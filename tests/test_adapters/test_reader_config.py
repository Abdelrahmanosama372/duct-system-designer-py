import pytest

from dsd.adapters.autocad import ReaderConfig


def test_example_yaml():
    config = ReaderConfig.from_yaml("examples/dsd_config.yaml")
    assert config.input_layer == "duct-network"
    assert config.application_name == "DSD"
    assert config.air_terminal_block_names == ("SUPPLY-DIFFUSER", "RETURN-GRILLE")


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(input_layer=""),
        dict(input_layer="input", application_name="OTHER"),
        dict(input_layer="input", air_terminal_block_names="SPR"),
        dict(input_layer="input", air_terminal_block_names=("",)),
    ],
)
def test_invalid_config(kwargs):
    with pytest.raises(ValueError):
        ReaderConfig(**kwargs)


def test_rejects_string_instead_of_block_list():
    with pytest.raises(ValueError):
        ReaderConfig.from_mapping(
            {"autocad": {"input": {"air_terminal_blocks": "SPR"}}}
        )
