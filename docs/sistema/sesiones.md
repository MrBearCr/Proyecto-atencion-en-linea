# Gestión de Sesiones

## Proceso de Autenticación y Gestión de Sesiones

El siguiente diagrama muestra el flujo completo de autenticación, incluyendo inicio de sesión, renovación de tokens y cierre de sesión:

![Diagrama de Autenticación](../../recursos/autenticacion_diagrama.png)

## Configuración

El sistema implementa el siguiente enfoque para gestión de sesiones:

1. **Duración de Sesión**: 30 minutos de inactividad por defecto
2. **Renovación Automática**: En cada interacción significativa del usuario
3. **Almacenamiento**: Tokens JWT (JSON Web Tokens, tokens web JSON) para API (Interfaz de Programación de Aplicaciones), cookies seguras para interfaz web

## Implementación

```csharp
// Configuración de servicios para gestión de sesiones
public void ConfigureServices(IServiceCollection services)
{
    services.AddAuthentication(options =>
    {
        options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
        options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
    })
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = Configuration["JWT:Issuer"],
            ValidAudience = Configuration["JWT:Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(
                Encoding.UTF8.GetBytes(Configuration["JWT:SecretKey"]))
        };
    });
    
    services.AddSession(options =>
    {
        options.IdleTimeout = TimeSpan.FromMinutes(30);
        options.Cookie.HttpOnly = true;
        options.Cookie.IsEssential = true;
        options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    });
}
```

## Seguridad Adicional

- **Bloqueo por Intentos Fallidos**: Implementación de mecanismo que bloquea temporalmente una cuenta después de varios intentos fallidos de autenticación
- **Captcha**: Sistema para prevenir ataques automatizados de fuerza bruta, requiriendo validación humana
- **Detección de Sesiones Concurrentes**: Monitoreo y gestión de múltiples sesiones activas para una misma cuenta de usuario

