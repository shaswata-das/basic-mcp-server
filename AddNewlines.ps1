# Navigate to your repository root first in PowerShell if you aren't already there.
# cd C:\path\to\your\repo

# Get all files tracked by Git
$gitFiles = git ls-files

foreach ($filePath in $gitFiles) {
    $fullPath = Join-Path -Path $PSScriptRoot -ChildPath $filePath # Or use (Get-Location).Path if not running as a script
    if (-not (Test-Path $fullPath -PathType Leaf)) {
        Write-Host "Skipping (not a file or not found): $fullPath"
        continue
    }

    try {
        # Attempt to detect if it's a binary file by checking for null bytes
        # This is not foolproof but a common heuristic.
        $isBinary = $false
        $bytes = Get-Content -Path $fullPath -Encoding Byte -ReadCount 2048 -TotalCount 2048 -ErrorAction SilentlyContinue
        if ($bytes -contains 0) {
            $isBinary = $true
        }

        if ($isBinary) {
            # Write-Host "Skipping binary file: $fullPath"
            continue
        }

        # Check if file is empty or ends with a newline
        $contentBytes = Get-Content -Path $fullPath -Encoding Byte -Raw -ErrorAction SilentlyContinue
        $endsWithNewline = $false
        if ($contentBytes.Length -gt 0) {
            # LF (10), CR (13)
            if ($contentBytes[-1] -eq 10) { # Ends with LF
                $endsWithNewline = $true
            } elseif ($contentBytes.Length -ge 2 -and $contentBytes[-2] -eq 13 -and $contentBytes[-1] -eq 10) { # Ends with CRLF
                $endsWithNewline = $true
            }
        } elseif ($contentBytes.Length -eq 0) {
            # Empty file, we can add a newline if desired, or treat it as already "ending with a newline" philosophically
            # For this script, let's add a newline to truly empty files.
            $endsWithNewline = $false # Force adding a newline to an empty file
        }


        if (-not $endsWithNewline) {
            # Add a newline. Default PowerShell newline is CRLF on Windows.
            Add-Content -Path $fullPath -Value ([System.Environment]::NewLine) -NoNewline -Encoding UTF8 # Or your file's original encoding
            Write-Host "Added newline to: $fullPath"
        }
    }
    catch {
        Write-Warning "Error processing file $fullPath : $($_.Exception.Message)"
    }
}

Write-Host "Done. Review changes with 'git diff' and then commit."
