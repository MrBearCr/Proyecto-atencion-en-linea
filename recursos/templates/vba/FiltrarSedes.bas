Attribute VB_Name = "FiltrarSedes"
Option Explicit

Private Const HOJA As String = "Alertas de Stock"
Private Const FILA_ENCABEZADO As Long = 8
Private Const COL_INICIO_SEDES As Long = 5 ' Columna E

' Botones rápidos
Public Sub MostrarCabudare()
    MostrarSede "03"
End Sub

Public Sub MostrarGuanare()
    MostrarSede "04"
End Sub

Public Sub MostrarBarinas()
    MostrarSede "01"
End Sub

Public Sub MostrarTodos()
    MostrarSede ""
End Sub

' Oculta/visualiza columnas por sede según prefijo de código de depósito
' prefijo = "03" Cabudare, "04" Guanare, "01" Barinas, "" = todas
Public Sub MostrarSede(ByVal prefijo As String)
    On Error GoTo salir
    Dim ws As Worksheet: Set ws = ThisWorkbook.Worksheets(HOJA)
    Dim lastCol As Long
    Dim col As Long
    Dim hdr As String
    Dim cod As String

    Application.ScreenUpdating = False
    Application.EnableEvents = False

    ' Determinar última columna usada en la fila de encabezados
    lastCol = ws.Cells(FILA_ENCABEZADO, ws.Columns.Count).End(xlToLeft).Column

    ' Mostrar columnas fijas
    ws.Range(ws.Columns(1), ws.Columns(COL_INICIO_SEDES - 1)).EntireColumn.Hidden = False

    ' Mostrar u ocultar columnas de sedes
    For col = COL_INICIO_SEDES To lastCol
        hdr = CStr(ws.Cells(FILA_ENCABEZADO, col).Value)
        cod = Left$(Trim$(hdr), 4) ' Encabezado típico: "0301 - Nombre"
        If Len(prefijo) = 0 Then
            ws.Columns(col).Hidden = False
        Else
            If Left$(cod, 2) = prefijo Then
                ws.Columns(col).Hidden = False
            Else
                ws.Columns(col).Hidden = True
            End If
        End If
    Next col

salir:
    Application.EnableEvents = True
    Application.ScreenUpdating = True
End Sub
