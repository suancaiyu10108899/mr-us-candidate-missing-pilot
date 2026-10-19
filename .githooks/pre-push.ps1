# PCA pre-push gate (TOOL-002 / CONTRACT-07, rev7).
# Three independent gates: publisher authority, secret scan and remote visibility.
# stdin: <local ref> <local sha> <remote ref> <remote sha> per line.
# argv: $1 = actual push remote NAME, $2 = resolved remote URL (provided by git).
# Project-specific visibility exception; no visibility override is accepted.
# Original publisher and outgoing-secret gates remain in force.

param([string]$RemoteName = '', [string]$RemoteUrl = '')

$ErrorActionPreference = 'Stop'
$issues = @()
function Add-Finding($id, $msg) { $script:issues += "[$id] $msg" }

function Get-ByteSha256([string]$Path) {
    $stream = $null
    $digest = $null
    try {
        $stream = [System.IO.File]::Open(
            $Path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite
        )
        $digest = [System.Security.Cryptography.SHA256]::Create()
        $bytes = $digest.ComputeHash($stream)
        return ([System.BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
    } finally {
        if ($digest) { $digest.Dispose() }
        if ($stream) { $stream.Dispose() }
    }
}

$stream = [Console]::OpenStandardInput()
$reader = New-Object System.IO.StreamReader($stream)
$stdin = $reader.ReadToEnd()
$reader.Dispose()
$lines = @($stdin -split "`r?`n" | Where-Object { $_.Trim() })
if ($lines.Count -eq 0) { exit 0 }

$ghLine = 'gh'
$override = $false
if ($env:PCA_ALLOW_UNVERIFIED_VISIBILITY -or $env:PCA_GH_CMD) {
    Add-Finding 'A17' 'project publication forbids visibility/provider overrides'
}
$debug = ($env:PCA_HOOK_DEBUG -eq '1')
function dbg($msg) { if ($script:debug) { Write-Host "HOOK-DBG: $msg" } }

# Exact project exception; arguments originate from parsed Git URL and live GitHub API.
function Test-ProjectVisibility([string]$Owner, [string]$Repository,
                                [string]$Operation, [string]$Visibility) {
    if ($Owner -ine 'suancaiyu10108899' -or
        $Repository -ine 'mr-us-candidate-missing-pilot') { return $false }
    if ($Operation -ceq 'CREATE_INITIAL_REF') { return $Visibility -ceq 'private' }
    if ($Operation -cin @('UPDATE_FF', 'CREATE_REF')) { return $Visibility -ceq 'public' }
    return $false
}

# ---- Gate 0: exact remote publisher authority ----
# A workspace lease or local ahead state never grants this permission.  One
# invocation may update one existing branch ref, create one absent branch relative
# to a live scope base, or create the one initial branch of an exact empty private
# GitHub repository. The issuer-approved
# target comes from an authority file outside the published Git root; the
# caller's locked target only detects a later shared-HEAD race.
$authorizedOperation = $null
$authorizedScopeBaseSha = $null
$authorizedP1BlobOids = New-Object 'System.Collections.Generic.HashSet[string]'
if ($lines.Count -ne 1) {
    Add-Finding 'A1' "publisher gate rejects multi-ref publication; use one exact grant/ref per push"
} else {
    $publishParts = @($lines[0].Trim() -split '\s+')
    if ($publishParts.Count -ne 4) {
        Add-Finding 'A2' "publisher gate received malformed pre-push input"
    } else {
        $actualTarget = $publishParts[1]
        $actualRemoteRef = $publishParts[2]
        $actualRemoteSha = $publishParts[3]
        $grantId = $env:PCA_PUBLISH_GRANT
        $publisherId = $env:PCA_PUBLISHER_ID
        $lockedTarget = $env:PCA_PUBLISH_TARGET
        $authorityFile = $env:PCA_PUBLISH_AUTHORITY_FILE
        if (-not $authorityFile) { $authorityFile = git config --get pca.publishAuthorityFile 2>$null }
        $controlTool = $env:PCA_CONTROL_TOOL
        if (-not $controlTool) { $controlTool = git config --get pca.controlTool 2>$null }
        if (-not $controlTool) {
            $candidate = Join-Path (git rev-parse --show-toplevel 2>$null) 'tools\pca.py'
            if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { $controlTool = $candidate }
        }
        if (-not $authorityFile) { Add-Finding 'A3' "publisher authority file is not configured" }
        if (-not $controlTool -or -not (Test-Path -LiteralPath $controlTool -PathType Leaf)) {
            Add-Finding 'A4' "publisher control tool is not configured"
        }
        if (-not $grantId) { Add-Finding 'A5' "publisher grant id is required" }
        if (-not $publisherId) { Add-Finding 'A6' "publisher identity is required" }
        if (-not $lockedTarget) { Add-Finding 'A7' "publisher target SHA must be locked before push" }
        if ($RemoteName -eq '' -or $RemoteUrl -eq '') {
            Add-Finding 'A8' "actual remote name/url from Git is required for publisher authority"
        }
        if ($issues.Count -eq 0) {
            $pythonCommand = $env:PCA_PYTHON_COMMAND
            if (-not $pythonCommand) {
                if (Get-Command python -ErrorAction SilentlyContinue) { $pythonCommand = 'python' }
                elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $pythonCommand = 'python3' }
            }
            if (-not $pythonCommand) {
                Add-Finding 'A9' "Python runtime for publisher gate is unavailable"
            } else {
                $hookEntry = Join-Path $PSScriptRoot 'pre-push'
                $hookScript = $PSCommandPath
                $hookEntryHash = $null
                $hookScriptHash = $null
                try {
                    $hookEntryHash = Get-ByteSha256 $hookEntry
                    $hookScriptHash = Get-ByteSha256 $hookScript
                } catch {
                    Add-Finding 'A9' "canonical publisher hook bundle cannot be hashed"
                }
            }
            if ($issues.Count -eq 0 -and $pythonCommand) {
                $publisherArgs = @(
                    $controlTool, 'publisher-check',
                    '--workspace', (git rev-parse --show-toplevel 2>$null),
                    '--authority-file', $authorityFile,
                    '--grant', $grantId,
                    '--publisher', $publisherId,
                    '--target', $actualTarget,
                    '--locked-target', $lockedTarget,
                    '--remote-name', $RemoteName,
                    '--remote-url', $RemoteUrl,
                    '--remote-ref', $actualRemoteRef,
                    '--remote-sha', $actualRemoteSha,
                    '--push-source-ref', $publishParts[0],
                    '--hook-entry-sha256', $hookEntryHash,
                    '--hook-script-sha256', $hookScriptHash
                )
                $publisherOutput = @(& $pythonCommand @publisherArgs 2>&1)
                $publisherRc = $LASTEXITCODE
                $publisherJson = $null
                try { $publisherJson = ($publisherOutput -join "`n") | ConvertFrom-Json } catch { }
                if ($publisherRc -ne 0) {
                    $safeReason = 'PUBLISHER_CHECK_FAILED'
                    if ($publisherJson -and $publisherJson.reason -match '^[A-Z0-9_]+$') { $safeReason = $publisherJson.reason }
                    Add-Finding 'A10' "publisher check blocked: $safeReason"
                } elseif (-not $publisherJson -or $publisherJson.status -ne 'AUTHORIZED' -or $publisherJson.reason -ne 'EXACT_GRANT_MATCH') {
                    Add-Finding 'A11' "publisher check returned an invalid success envelope"
                } elseif ($publisherJson.operation -notin @('UPDATE_FF', 'CREATE_REF', 'CREATE_INITIAL_REF')) {
                    Add-Finding 'A12' "publisher check returned an invalid operation"
                } else {
                    $authorizedOperation = [string]$publisherJson.operation
                    $exceptionValues = @()
                    if ($publisherJson.PSObject.Properties.Name -contains 'secret_scan_p1_blob_oids') {
                        $exceptionValues = @($publisherJson.secret_scan_p1_blob_oids)
                    }
                    foreach ($exceptionOid in $exceptionValues) {
                        $canonicalOid = [string]$exceptionOid
                        if ($canonicalOid -notmatch '^(?:[0-9a-f]{40}|[0-9a-f]{64})$') {
                            Add-Finding 'A16' "publisher check returned an invalid P1 blob exception"
                            break
                        }
                        $null = $authorizedP1BlobOids.Add($canonicalOid)
                    }
                    if ($authorizedOperation -eq 'CREATE_REF') {
                        $scopeBase = [string]$publisherJson.scope_base_sha
                        if ($scopeBase -notmatch '^[0-9a-f]{40}$' -or $scopeBase -match '^0+$') {
                            Add-Finding 'A13' "publisher check returned an invalid create-ref scope base"
                        } else {
                            $authorizedScopeBaseSha = $scopeBase
                        }
                    } elseif ($authorizedOperation -eq 'CREATE_INITIAL_REF' -and $override) {
                        Add-Finding 'A15' "initial-ref publication forbids the visibility override"
                    }
                }
            }
        }
    }
}

if ($issues.Count -gt 0) {
    Write-Host "pre-push gate BLOCKED ($($issues.Count) finding(s)):"
    foreach ($i in $issues) { Write-Host "  $i" }
    Write-Host 'A workspace lease, commit authorship or local ahead state never grants remote publication.'
    exit 1
}

# ---- Gate 1: secret scan over outgoing objects ----
$secretRules = @(
    @{ id = 'R1'; label = 'private key block';      re = '-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----' },
    @{ id = 'R2'; label = 'credential assignment';  re = '(?i)\b(api[_-]?key|apikey|secret|token|password|passwd|authorization)\s*[:=]\s*["'']?[A-Za-z0-9_\-]{16,}(?![A-Za-z0-9_\-]|[^\S\r\n]*\()' },
    @{ id = 'R3'; label = 'cloud API key';          re = '\bsk-[A-Za-z0-9]{20,}\b' },
    @{ id = 'R4'; label = 'GitHub token';           re = '\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}' },
    @{ id = 'R5'; label = 'connection string';      re = '\b(mongodb(\+srv)?|postgres(ql)?|mysql|redis)://[^\s:@]+:[^\s@]+@' },
    @{ id = 'P1'; label = 'absolute personal path'; re = '[A-Za-z]:\\Users\\[\p{L}\p{N}._-]+' }
)

$anyFirstPush = $false
foreach ($line in $lines) {
    $parts = @($line.Trim() -split '\s+')
    if ($parts.Count -lt 4) { continue }
    $localRef, $localSha, $remoteRef, $remoteSha = $parts[0], $parts[1], $parts[2], $parts[3]

    # ref deletion publishes no new objects
    if ($localSha -match '^0+$') { continue }

    if ($remoteSha -match '^0+$') { $firstPush = $true; $anyFirstPush = $true }
    if ($remoteSha -match '^0+$') {
        if ($authorizedOperation -eq 'CREATE_REF' -and $authorizedScopeBaseSha) {
            $range = "$authorizedScopeBaseSha..$localSha"
        } elseif ($authorizedOperation -eq 'CREATE_INITIAL_REF') {
            $range = $localSha
        } else {
            Add-Finding 'A14' "absent remote ref has no validated create-ref scope base"
            $range = $localSha
        }
    } else {
        git cat-file -e "$remoteSha^{commit}" 2>$null
        if ($LASTEXITCODE -eq 0) { $range = "$remoteSha..$localSha" } else { $range = $localSha }
    }

    # Check every path touched by every outgoing commit.  Object enumeration
    # may display only one arbitrary path for a shared blob, so filename policy
    # cannot be derived from `rev-list --objects` display names.  Using the
    # commit diff (not the whole tree) avoids rescanning inherited remote paths.
    $savedErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $commits = @(git --no-replace-objects rev-list $range 2>$null)
        $commitsRc = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedErrorActionPreference
    }
    if ($commitsRc -ne 0) {
        Add-Finding 'E1' "cannot enumerate outgoing commits (fail-closed)"
        continue
    }
    $pathSet = New-Object 'System.Collections.Generic.HashSet[string]'
    $pathEnumerationFailed = $false
    foreach ($commitOid in $commits) {
        $savedErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $rawTreePaths = @(
                git --no-replace-objects diff-tree --root --no-commit-id --name-only --no-renames --diff-filter=ACMRTUXB -r -m -z $commitOid 2>$null
            )
            $treeRc = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $savedErrorActionPreference
        }
        if ($treeRc -ne 0) {
            Add-Finding 'E1' "cannot enumerate outgoing touched paths (fail-closed)"
            $pathEnumerationFailed = $true
            break
        }
        $treePathText = @($rawTreePaths) -join "`n"
        foreach ($treePath in @($treePathText -split ([char]0))) {
            if ($treePath) { $null = $pathSet.Add($treePath) }
        }
    }
    if ($pathEnumerationFailed) { continue }
    foreach ($treePath in $pathSet) {
        if ($treePath -match '(\.pem|\.key|\.p12|\.pfx|\.jks|\.keystore)$|(^|/)(credentials|\.credentials)(\.|$)') {
            Add-Finding 'R6' "credential-looking filename in outgoing commits: $treePath"
        }
    }

    # Content scan every distinct outgoing object OID.  Path policy above is
    # intentionally separate so shared-blob aliases cannot hide a filename.
    $savedErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $objects = @(git --no-replace-objects rev-list --objects --no-object-names $range 2>$null)
        $objectsRc = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedErrorActionPreference
    }
    if ($objectsRc -ne 0) {
        Add-Finding 'E1' "cannot enumerate outgoing objects (fail-closed)"
        continue
    }
    dbg "range=$range objects=$($objects.Count) paths=$($pathSet.Count)"
    foreach ($obj in $objects) {
        $oid = $obj.Trim()
        if ($oid -notmatch '^[0-9a-fA-F]{40,64}$') {
            Add-Finding 'E1' "invalid outgoing object identity (fail-closed)"
            continue
        }
        $savedErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $type = git --no-replace-objects cat-file -t $oid 2>$null
            $typeRc = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $savedErrorActionPreference
        }
        if ($typeRc -ne 0) {
            Add-Finding 'E1' "cannot inspect outgoing object type (fail-closed)"
            continue
        }
        if ($type -ne 'blob') { continue }
        $savedErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $content = git --no-replace-objects cat-file blob $oid 2>$null
            $catRc = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $savedErrorActionPreference
        }
        if ($catRc -ne 0) { Add-Finding 'E1' "cannot read outgoing blob (fail-closed)"; continue }
        if ($null -eq $content) { continue }  # legitimate empty blob: nothing to scan
        $text = @($content) -join "`n"
        $head = $text.Substring(0, [Math]::Min(8192, $text.Length))
        if ($head.IndexOf([char]0) -ge 0) { continue }          # binary: content skipped, filename rule already applied
        if ($text.Length -gt 1048576) { continue }              # large blob: content scan skipped (documented limit)
        foreach ($rule in $secretRules) {
            if ($text -match $rule.re) {
                if ($rule.id -eq 'P1' -and $authorizedP1BlobOids.Contains($oid.ToLowerInvariant())) {
                    dbg "AUTHORIZED P1 blob exception"
                    continue
                }
                dbg "HIT rule $($rule.id)"
                Add-Finding $rule.id "secret pattern ($($rule.label)) in outgoing blob"
            }
        }
    }
}

# ---- Gate 2: remote visibility (actual push target first) ----
$targets = @()
if ($RemoteUrl) {
    $targets += @{ name = $RemoteName; url = $RemoteUrl }
} else {
    # Fallback for manual invocation / older git: replicate git's own push
    # resolution order: branch.pushRemote -> remote.pushDefault -> branch.remote -> origin.
    foreach ($line in $lines) {
        $parts = @($line.Trim() -split '\s+')
        if ($parts.Count -lt 4 -or $parts[1] -match '^0+$') { continue }
        $short = ($parts[0] -replace '^refs/heads/', '')
        $name = git config --get "branch.$short.pushRemote" 2>$null
        if (-not $name) { $name = git config --get 'remote.pushDefault' 2>$null }
        if (-not $name) { $name = git config --get "branch.$short.remote" 2>$null }
        if (-not $name) { $name = 'origin' }
        $url = git remote get-url $name 2>$null
        if ($url) { $targets += @{ name = $name; url = $url } }
    }
}
$targets = @($targets | Sort-Object -Property url -Unique)

foreach ($t in $targets) {
    $remote = $t.name
    $url = $t.url
    if (-not $url) { Add-Finding 'V1' "cannot resolve remote URL for $remote"; continue }
    $isGitHub = $false
    $owner = $null
    $repo = $null
    $parsedUri = $null
    if ([System.Uri]::TryCreate($url, [System.UriKind]::Absolute, [ref]$parsedUri) -and $parsedUri.Host) {
        $scheme = $parsedUri.Scheme.ToLowerInvariant()
        $transportAllowed =
            ($scheme -eq 'https' -and $parsedUri.UserInfo -eq '' -and
                ($parsedUri.IsDefaultPort -or $parsedUri.Port -eq 443)) -or
            ($scheme -eq 'ssh' -and $parsedUri.UserInfo -ceq 'git' -and
                ($parsedUri.IsDefaultPort -or $parsedUri.Port -eq 22))
        $pathMatch = [regex]::Match(
            $parsedUri.AbsolutePath,
            '^/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$',
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
        )
        if (
            $parsedUri.Host -ieq 'github.com' -and
            $transportAllowed -and
            -not $parsedUri.Query -and
            -not $parsedUri.Fragment -and
            $pathMatch.Success
        ) {
            $isGitHub = $true
            $owner = $pathMatch.Groups[1].Value
            $repo = $pathMatch.Groups[2].Value
        }
    }
    if (-not $isGitHub) {
        $scpMatch = [regex]::Match(
            $url,
            '^git@github\.com:([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$',
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
        )
        if ($scpMatch.Success) {
            $isGitHub = $true
            $owner = $scpMatch.Groups[1].Value
            $repo = $scpMatch.Groups[2].Value
        }
    }
    if (-not $isGitHub) {
        if (-not $override) { Add-Finding 'V2' "non-GitHub remote ($remote): visibility unverifiable; project publication is blocked" }
        continue
    }
    if (-not $owner -or -not $repo -or $owner -notmatch '^[A-Za-z0-9-]+$' -or $repo -notmatch '^[A-Za-z0-9_.-]+$') {
        Add-Finding 'V3' "cannot parse GitHub owner/repo from remote URL"
        continue
    }
    $vis = cmd /c "$ghLine api --hostname github.com repos/$owner/$repo --jq .visibility 2>nul"
    if ($LASTEXITCODE -eq 0 -and $vis) {
        if (-not (Test-ProjectVisibility $owner $repo $authorizedOperation $vis)) {
            Add-Finding 'V4' 'repository identity/operation/live visibility is outside the exact project exception'
        }
    } else {
        if (-not $override) { Add-Finding 'V5' "visibility unverifiable for $owner/$repo (gh unavailable/network/not logged in); project publication is blocked" }
    }
}

if ($issues.Count -gt 0) {
    Write-Host "pre-push gate BLOCKED ($($issues.Count) finding(s)):"
    foreach ($i in $issues) { Write-Host "  $i" }
    Write-Host 'Secret values are never printed. This project accepts no visibility/provider override.'
    exit 1
}
exit 0
