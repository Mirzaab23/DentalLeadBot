Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Run setup.ps1 first.' }
$appPort = $null
foreach ($candidatePort in 8501..8510) {
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $candidatePort)
        $listener.Start()
        $appPort = $candidatePort
        break
    } catch {
        continue
    } finally {
        if ($listener) { $listener.Stop() }
    }
}
if (-not $appPort) { throw 'No available local port from 8501 through 8510.' }
Write-Host "Starting ProspectLab at http://localhost:$appPort"
& .\.venv\Scripts\python.exe -m streamlit run app.py --server.address localhost --server.port $appPort
