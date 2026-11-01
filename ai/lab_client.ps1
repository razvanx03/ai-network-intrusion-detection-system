# Run only inside the owned Windows lab VM. No configuration is changed.
# Three independent rounds; all labelled load/scan traffic stays on the lab LAN.
param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
$labTarget = '192.168.50.1'
$labSource = '192.168.50.2'
$rows = [System.Collections.Generic.List[object]]::new()
function Exchange([string]$phase, [int]$round, [int]$port, [int]$size, [int]$label) {
    $sock = [System.Net.Sockets.Socket]::new('InterNetwork','Stream','Tcp')
    $sock.Bind([System.Net.IPEndPoint]::new([System.Net.IPAddress]::Parse($labSource),0))
    $localPort = $sock.LocalEndPoint.Port
    $started = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0
    $success = $false
    $bytes = 0
    try {
        $sock.SendTimeout = 3000; $sock.ReceiveTimeout = 3000
        $pending = $sock.BeginConnect($labTarget,$port,$null,$null)
        if (!$pending.AsyncWaitHandle.WaitOne(50)) { throw 'Connect timeout' }
        $sock.EndConnect($pending)
        if ($size -gt 0) {
            $request = [Text.Encoding]::ASCII.GetBytes("GET /$size HTTP/1.1`r`nHost: lab.local`r`nConnection: close`r`n`r`n")
            $null = $sock.Send($request)
            $buffer = [byte[]]::new(65536)
            do { $count = $sock.Receive($buffer); $bytes += $count } while ($count -gt 0)
        }
        $success = $true
    } catch { $failure = $_.Exception.GetType().Name }
    finally { $sock.Dispose() }
    $rows.Add([ordered]@{phase=$phase;round=$round;label=$label;proto='tcp';
        source=$labSource;destination=$labTarget;source_port=$localPort;destination_port=$port;
        started=$started;ended=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0;
        success=$success;received_bytes=$bytes})
}
for ($round=1; $round -le 3; $round++) {
    for ($i=0; $i -lt 60; $i++) {
        Exchange 'benign_http' $round 18080 (@(1024,16384,262144)[$i%3]) 0
        Start-Sleep -Milliseconds (80+($i%5)*40)
    }
    # This is an intentional bounded reconnaissance scenario, not a flood.
    for ($port=21000; $port -lt 21256; $port++) {
        Exchange 'port_scan' $round $port 0 1
        Start-Sleep -Milliseconds 20
    }
    # Single-source HTTP load: not evidence of distributed DoS or an outage.
    for ($i=0; $i -lt 300; $i++) {
        Exchange 'http_load' $round 18080 1024 1
        Start-Sleep -Milliseconds 30
    }
    foreach ($phase in @('benign_udp','udp_burst')) {
        $flows = if ($phase -eq 'benign_udp') {20} else {20}
        $packets = if ($phase -eq 'benign_udp') {1} else {50}
        for ($i=0; $i -lt $flows; $i++) {
            $udp = [System.Net.Sockets.UdpClient]::new([System.Net.IPEndPoint]::new([System.Net.IPAddress]::Parse($labSource),0))
            $udp.Client.ReceiveTimeout=1000
            $localPort=$udp.Client.LocalEndPoint.Port
            $start=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0
            $udp.Connect($labTarget,18081)
            $ok=$true
            $peer=[System.Net.IPEndPoint]::new([System.Net.IPAddress]::Any,0)
            try {
                for ($j=0; $j -lt $packets; $j++) {
                    $payload=[byte[]]::new(128)
                    $null=$udp.Send($payload,$payload.Length)
                    $null=$udp.Receive([ref]$peer)
                    if ($packets -gt 1) {Start-Sleep -Milliseconds 2}
                }
            } catch {$ok=$false}
            $udp.Dispose()
            $rows.Add([ordered]@{phase=$phase;round=$round;label=[int]($phase -eq 'udp_burst');
                proto='udp';source=$labSource;destination=$labTarget;source_port=$localPort;
                destination_port=18081;started=$start;ended=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0;success=$ok})
            if ($packets -eq 1) {Start-Sleep -Milliseconds 80}
        }
    }
    $rows | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath $OutputPath
    Write-Output "Completed round $round with $($rows.Count) labelled attempts"
    Start-Sleep -Seconds 2
}
