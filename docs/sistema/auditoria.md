# Sistema de Auditoría

## Eventos Auditados

El sistema registra los siguientes tipos de eventos:

- Inicios y cierres de sesión
- Operaciones CRUD sobre datos de clientes
- Envío de mensajes por WhatsApp
- Cambios en la configuración
- Errores y excepciones del sistema

## Implementación

La auditoría se implementa mediante el patrón de interceptores y aspecto:

```csharp
// Atributo para auditar operaciones
[AttributeUsage(AttributeTargets.Method)]
public class AuditarOperacionAttribute : Attribute, IActionFilter
{
    public void OnActionExecuting(ActionExecutingContext context)
    {
        // Registrar inicio de operación
    }
    
    public void OnActionExecuted(ActionExecutedContext context)
    {
        // Registrar resultado de operación
        var usuario = context.HttpContext.User.Identity.Name;
        var accion = context.ActionDescriptor.DisplayName;
        var ip = context.HttpContext.Connection.RemoteIpAddress.ToString();
        
        // Almacenar log en la base de datos
        var servicioAuditoria = context.HttpContext.RequestServices.GetService<IServicioAuditoria>();
        servicioAuditoria.RegistrarEvento(usuario, accion, ip, context.Result);
    }
}
```

## Consulta y Retención de Logs

- Los logs se retienen por un período de 12 meses
- Existe una interfaz administrativa para consultar y filtrar registros
- Los logs antiguos se archivan automáticamente en almacenamiento secundario

