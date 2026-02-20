# Hook script to refresh global CLAUDE.md contents on each prompt submission
# Project CLAUDE.md no longer has injected voice content (voice-context skill handles it)
# Output will be added to Claude's context

$globalClaudeMd = "C:\Users\jamea\.claude\CLAUDE.md"

$exitCode = 0

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
