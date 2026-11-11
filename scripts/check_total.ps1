$root = "C:\Users\Администратор\Desktop\Новая папка (2)\CareerAI"
$items = Get-ChildItem $root -Recurse -File -ErrorAction SilentlyContinue
$sum = ($items | Measure-Object -Property Length -Sum).Sum
Write-Host "Total project size: $([math]::Round($sum/1GB, 2)) GB"

# Also check node_modules if it exists anywhere
$nm = Get-ChildItem $root -Directory -Filter "node_modules" -ErrorAction SilentlyContinue
if ($nm) {
    foreach ($dir in $nm) {
        $nmItems = Get-ChildItem $dir.FullName -Recurse -File -ErrorAction SilentlyContinue
        $nmSum = ($nmItems | Measure-Object -Property Length -Sum).Sum
        Write-Host "node_modules at $($dir.FullName): $([math]::Round($nmSum/1MB, 1)) MB"
    }
} else {
    Write-Host "No node_modules found"
}
