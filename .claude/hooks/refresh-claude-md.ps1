# Hook script to refresh CLAUDE.md contents on each prompt submission
# Output will be added to Claude's context

$projectClaudeMd = Join-Path $PSScriptRoot "..\..\CLAUDE.md"
$globalClaudeMd = "C:\Users\jamea\.claude\CLAUDE.md"

$exitCode = 0

# Refresh project CLAUDE.md
if (Test-Path $projectClaudeMd) {
    Write-Output "<claude-md-refresh>"
    Write-Output "Contents of CLAUDE.md (auto-refreshed on prompt submit):"
    Write-Output ""
    Get-Content $projectClaudeMd -Raw
    Write-Output "</claude-md-refresh>"
} else {
    Write-Error "Project CLAUDE.md not found at $projectClaudeMd"
    $exitCode = 1
}

# Refresh global CLAUDE.md
if (Test-Path $globalClaudeMd) {
    Write-Output "<global-claude-md-refresh>"
    Write-Output "Contents of global CLAUDE.md (auto-refreshed on prompt submit):"
    Write-Output ""
    Get-Content $globalClaudeMd -Raw
    Write-Output "</global-claude-md-refresh>"
} else {
    Write-Error "Global CLAUDE.md not found at $globalClaudeMd"
    $exitCode = 1
}

exit $exitCode
