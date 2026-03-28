# העלאת הפרויקט ל-GitHub (מאגר חדש + push)
# הריצי ב-PowerShell:  .\upload-to-github.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

function Test-GhAuth {
    gh auth status 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git לא נמצא ב-PATH. התקיני Git for Windows והפעילי מחדש את הטרמינל."
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) לא נמצא. התקיני: winget install GitHub.cli"
}

if (-not (Test-GhAuth)) {
    Write-Host "נדרשת התחברות ל-GitHub (דפדפן או טוקן)." -ForegroundColor Cyan
    gh auth login -h github.com -p https -w
    if (-not (Test-GhAuth)) {
        Write-Error "ההתחברות נכשלה. הריצי ידנית: gh auth login"
    }
}

$defaultName = "personal_skin"
$name = Read-Host "שם מאגר ב-GitHub (Enter = $defaultName)"
if ([string]::IsNullOrWhiteSpace($name)) { $name = $defaultName }

$branch = (git branch --show-current).Trim()
if ([string]::IsNullOrWhiteSpace($branch)) { $branch = "main" }

$hasRemote = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "קיים remote 'origin'. דוחפת ל-$hasRemote" -ForegroundColor Yellow
    git push -u origin $branch
    Write-Host "סיום." -ForegroundColor Green
    exit 0
}

Write-Host "יוצר מאגר '$name' ודוחף..." -ForegroundColor Cyan
gh repo create $name --public --source=. --remote=origin --push --description "PersonalSkin - Flask skincare routine app"

$user = gh api user --jq .login 2>$null
if ($user) {
    Write-Host "בוצע. הקישור: https://github.com/$user/$name" -ForegroundColor Green
} else {
    Write-Host "בוצע. בדקי את המאגר תחת החשבון שלך ב-GitHub." -ForegroundColor Green
}
