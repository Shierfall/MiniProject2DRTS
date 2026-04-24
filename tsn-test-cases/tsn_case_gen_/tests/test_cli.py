from typer.testing import CliRunner
from tsn_case_gen_.cli.__main__ import app

runner = CliRunner()

def test_help():
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert "TSN test case generator" in result.output
    assert "generate" in result.output
    assert "validate" in result.output
    assert "info" in result.output

def test_version():
    result = runner.invoke(app, ['version'])
    assert result.exit_code == 0
    assert "tsn-case-gen version" in result.output

#def test_generate_stub(): runs with --config
#    result = runner.invoke(app, ['generate', '--config', 'foo.json', '--out', 'bar'])
#    assert result.exit_code == 0
#    assert "Generating test cases from:" in result.output
#    assert "TODO: Implement generation logic." in result.output

#def test_validate_stub():
#    result = runner.invoke(app, ['validate', '--schema', 'foo.schema.json', '--data', 'bar.json'])
#    assert result.exit_code == 0
#    assert "Validating:" in result.output
#    assert "TODO: Implement validation logic." in result.output

def test_info():
    result = runner.invoke(app, ['info'])
    assert result.exit_code == 0
    assert "TSN test case generator & utilities" in result.output
    assert "Supported formats" in result.output
    assert "Shell completion" in result.output
