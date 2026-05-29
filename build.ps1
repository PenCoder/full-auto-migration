Set-Location -Path $PSScriptRoot

pyinstaller --noconfirm --onefile --windowed `
    --name "MigrationWizard" `
    --add-data "configs;configs" `
    --add-data "src\qt_ui\theme.qss;src\qt_ui" `
    --add-data "src\qt_ui\assets;src\qt_ui\assets" `
    --hidden-import "PySide6.QtSvg" `
    --hidden-import "PySide6.QtPrintSupport" `
    app.py

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host "Output: dist\MigrationWizard.exe" -ForegroundColor Cyan
Pause
