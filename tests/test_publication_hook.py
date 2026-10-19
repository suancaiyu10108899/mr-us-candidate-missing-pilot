"""Exercise the actual PowerShell policy function, not a Python reimplementation."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

SHELL = shutil.which("pwsh") or shutil.which("powershell")
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not SHELL, reason="maintainer PowerShell unavailable; fixture tests still run")
def test_actual_visibility_function_cases():
    script = r'''
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    (Join-Path (Get-Location) '.githooks/pre-push.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw 'hook syntax invalid' }
$fn = $ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Test-ProjectVisibility'}, $true)
if (-not $fn) { throw 'production function missing' }
Invoke-Expression $fn.Extent.Text
$cases = @(
    @('suancaiyu10108899','mr-us-candidate-missing-pilot','CREATE_INITIAL_REF','private'),
    @('suancaiyu10108899','mr-us-candidate-missing-pilot','UPDATE_FF','public'),
    @('suancaiyu10108899','mr-us-candidate-missing-pilot','CREATE_REF','public'),
    @('suancaiyu10108899','mr-us-candidate-missing-pilot','CREATE_INITIAL_REF','public'),
    @('suancaiyu10108899','mr-us-candidate-missing-pilot','UPDATE_FF','private'),
    @('another-owner','mr-us-candidate-missing-pilot','CREATE_REF','public'),
    @('suancaiyu10108899','another-repository','CREATE_INITIAL_REF','private'),
    @('suancaiyu10108899','mr-us-candidate-missing-pilot','DELETE','public'),
    @('suancaiyu10108899','mr-us-candidate-missing-pilot','UPDATE_FF','unknown'),
    @('suancaiyu10108899','mr-us-candidate-missing-pilot','UPDATE_FF','')
)
$results = @($cases | ForEach-Object { Test-ProjectVisibility $_[0] $_[1] $_[2] $_[3] })
ConvertTo-Json -Compress -InputObject $results
'''
    result = subprocess.run([SHELL, "-NoProfile", "-NonInteractive", "-Command", script],
                            cwd=ROOT, text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == [True, True, True, False, False, False, False, False, False, False]


@pytest.mark.skipif(not SHELL, reason="maintainer PowerShell unavailable")
@pytest.mark.parametrize("override", [None, "PCA_ALLOW_UNVERIFIED_VISIBILITY", "PCA_GH_CMD"])
def test_native_hook_without_grant_blocks_before_publication(override):
    import os
    environment = {k: v for k, v in os.environ.items() if not k.startswith("PCA_")}
    if override:
        environment[override] = "synthetic-forbidden-override"
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    line = f"{head} {head} refs/heads/main {'0' * 40}\n"
    result = subprocess.run([SHELL, "-NoProfile", "-NonInteractive", "-File",
                             str(ROOT / ".githooks/pre-push.ps1"), "origin",
                             "https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot.git"],
                            cwd=ROOT, input=line, env=environment, text=True, capture_output=True)
    assert result.returncode != 0
    assert "[A5]" in result.stdout  # No grant; visibility is never treated as authority.
    if override:
        assert "[A17]" in result.stdout
