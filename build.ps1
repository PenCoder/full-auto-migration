# Set the current directory to where the script is located
Set-Location -Path $PSScriptRoot

# Run the PyInstaller command
pyinstaller --noconfirm --onefile --windowed `
    --add-data "configs;configs" `
    --add-data "data;data" `
    --name "WinApp" `
    app.py

Write-Host "Build Complete! Check the 'dist' folder." -ForegroundColor Green
Pause
