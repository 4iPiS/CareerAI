$root = "C:\Users\Администратор\Desktop\Новая папка (2)\CareerAI"
$folders = @("node_modules", "frontend\node_modules", "app")
foreach ($f in $folders) {
    $path = Join-Path $root $f
    if (Test-Path $path) {
        $items = Get-ChildItem $path -Recurse -File -ErrorAction SilentlyContinue
        $sum = ($items | Measure-Object -Property Length -Sum).Sum
        Write-Host "$f : $([math]::Round($sum/1MB, 1)) MB"
    } else {
        Write-Host "$f : not found"
    }
}
