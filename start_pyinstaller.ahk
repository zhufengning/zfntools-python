#NoEnv
#SingleInstance Force
SendMode Input
SetWorkingDir %A_ScriptDir%

; Include the Socket library. Assumes Socket.ahk is in the same directory.
#Include %A_ScriptDir%\Socket.ahk

!Space::
    portFile := A_ScriptDir . "\.port"
    if !FileExist(portFile)
    {
        ; If the .port file doesn't exist, try to run the main application
        Run, ./main.exe, %A_ScriptDir%, Hide
        return
    }

    FileRead, port, %portFile%
    port := Trim(port) ; Trim whitespace

    if port is not number
    {
        MsgBox, 48, Error, Invalid port number found in .port file: %port%
        return
    }

    try
    {
        udp := new SocketUDP()
        udp.Connect(["127.0.0.1", port])
        udp.SendText("wake")
        udp.Disconnect()
    }
    catch e
    {
        MsgBox, 48, Error, Could not send UDP packet.`n`nError: %e%
    }
return