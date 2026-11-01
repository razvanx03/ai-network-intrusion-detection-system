# Ordinary public HTTPS requests from the Windows VM, with tuple-level evidence.
param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$rows=[System.Collections.Generic.List[object]]::new()
foreach ($round in 1..3) {
    foreach ($site in @('https://example.com/','https://www.python.org/','https://www.wikipedia.org/')) {
        foreach ($attempt in 1..5) {
            $started=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0
            $result=& curl.exe -4 --http1.1 --max-time 20 --silent --show-error --output NUL --write-out '%{json}' $site
            $code=$LASTEXITCODE
            $detail=$result | ConvertFrom-Json
            if (!$detail.local_port -or !$detail.remote_ip) {throw 'HTTPS request has no attributable tuple'}
            $rows.Add([ordered]@{phase='benign_https';round=$round;label=0;proto='tcp';
                source=$detail.local_ip;destination=$detail.remote_ip;source_port=$detail.local_port;
                destination_port=$detail.remote_port;started=$started;
                ended=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0;
                success=($code -eq 0);http_status=$detail.http_code;site=$site})
            Start-Sleep -Milliseconds 100
        }
    }
}
$rows | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath $OutputPath
Write-Output "Completed $($rows.Count) ordinary HTTPS requests"
