# Cifrado de Credenciales

## Algoritmos Utilizados

Se utiliza un enfoque multicapa para el cifrado de credenciales:

1. **Hashing de Contraseñas**: BCrypt con factor de costo 12 (algoritmo de cifrado unidireccional utilizado para almacenar contraseñas de forma segura)
2. **Cifrado de Datos Sensibles**: AES-256 en modo CBC (Advanced Encryption Standard, estándar avanzado de cifrado con clave de 256 bits en modo Cipher Block Chaining)
3. **Almacenamiento de Claves**: Protección de datos de Windows (DPAPI - Data Protection API, API de Protección de Datos)

## Implementación

```csharp
// Ejemplo de implementación de cifrado de credenciales
public class GestorCifrado
{
    private readonly byte[] _vectorInicializacion;
    private readonly string _claveGenerada;
    
    public GestorCifrado(IConfiguration config)
    {
        _vectorInicializacion = Convert.FromBase64String(config["Seguridad:VectorInicializacion"]);
        _claveGenerada = ObtenerClaveSegura(config["Seguridad:SemillaClaveAES"]);
    }
    
    public string CifrarDato(string datoSensible)
    {
        // Implementación del cifrado AES
        using (var aes = Aes.Create())
        {
            aes.Key = Encoding.UTF8.GetBytes(_claveGenerada);
            aes.IV = _vectorInicializacion;
            
            // Resto de la implementación...
        }
    }
    
    public string DescifrarDato(string datoCifrado)
    {
        // Implementación del descifrado AES
    }
    
    private string ObtenerClaveSegura(string semilla)
    {
        // Derivación de clave segura usando PBKDF2
    }
}
```

## Almacenamiento de Credenciales

Las credenciales cifradas se almacenan en:

1. Base de datos: Tabla especializada con acceso restringido
2. Configuración: Archivos protegidos en el servidor
3. Memoria: Durante la ejecución de la aplicación

