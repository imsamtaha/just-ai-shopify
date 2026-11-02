$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice('Microsoft Zira Desktop')
$synth.Rate = -1
try {
  Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'video') -Recurse -Filter '*.txt' | ForEach-Object {
    $wavPath = [System.IO.Path]::ChangeExtension($_.FullName, '.wav')
    $synth.SetOutputToWaveFile($wavPath)
    $synth.Speak([System.IO.File]::ReadAllText($_.FullName))
    $synth.SetOutputToNull()
  }
} finally { $synth.Dispose() }
Write-Output 'All 24 narration clips created.'
