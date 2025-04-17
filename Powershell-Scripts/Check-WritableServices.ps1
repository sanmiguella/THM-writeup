$basePath = "HKLM:\SYSTEM\CurrentControlSet\Services"
$services = Get-ChildItem -Path $basePath

foreach ($svc in $services) {
    try {
        $acl = Get-Acl -Path $svc.PSPath
        foreach ($ace in $acl.Access) {
            if (
                ($ace.IdentityReference -like "$env:USERDOMAIN\$env:USERNAME" -or
                 $ace.IdentityReference -like "*Server Operators*" -or
                 $ace.IdentityReference -like "*Everyone*") -and
                ($ace.RegistryRights -match "SetValue|FullControl|WriteKey")
            ) {
                Write-Host "[+] Writable Service Registry Key Found: $($svc.PSChildName)" -ForegroundColor Green
                Write-Host "    Path : $($svc.PSPath)"
                Write-Host "    ACL  : $($ace.IdentityReference) - $($ace.RegistryRights)"
                Write-Host ""
            }
        }
    } catch {
        continue
    }
}
