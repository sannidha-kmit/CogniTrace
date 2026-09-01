$cfgPath = 'C:\Program Files\MongoDB\Server\8.3\bin\mongod.cfg'
$content = Get-Content $cfgPath
$newContent = $content -replace ' authorization: enabled', '# authorization: enabled'
Set-Content $cfgPath $newContent
Restart-Service MongoDB
