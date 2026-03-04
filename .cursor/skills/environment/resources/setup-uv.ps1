# Install uv if not present
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "uv already installed: $(uv --version)"
    exit 0
}
irm https://astral.sh/uv/install.ps1 | iex
Write-Host "Restart your terminal to use uv"
