# 🚀 Guía de Despliegue en Render

Esta guía te ayudará a desplegar tu bot de Telegram en Render.

## 📋 Requisitos Previos

1. Cuenta en [Render.com](https://render.com)
2. Repositorio Git (GitHub, GitLab, etc.) con tu código
3. Token de Telegram Bot (obtener de [@BotFather](https://t.me/BotFather))
4. IDs de usuarios administradores de Telegram

## 🔧 Configuración en Render

### Paso 1: Crear un Nuevo Servicio (IMPORTANTE: Background Worker)

**⚠️ IMPORTANTE**: Para bots de Telegram que usan polling, debes crear un **Background Worker**, NO un Web Service.

1. Ve a tu dashboard de Render
2. Haz clic en **"New +"** → **"Background Worker"** (NO "Web Service")
3. Conecta tu repositorio Git
4. Configura los siguientes parámetros:
   - **Name**: `conta-bot` (o el nombre que prefieras)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`

**¿Por qué Background Worker?**
- Los bots de Telegram con polling no necesitan escuchar en un puerto HTTP
- Los Web Services en Render requieren que escuches en un puerto, lo cual no es necesario para bots
- Los Background Workers son perfectos para procesos de larga duración como bots

### Paso 2: Configurar Variables de Entorno

En la sección **"Environment"** de tu servicio en Render, agrega las siguientes variables de entorno:

#### Variables Requeridas:

```
TELEGRAM_BOT_TOKEN=tu_token_de_telegram_aqui
ADMIN_USER_IDS=1470695759,1231441482,1121022493,6397876923
```

**Nota**: Reemplaza los valores con tus propios datos:
- `TELEGRAM_BOT_TOKEN`: Tu token del bot de Telegram
- `ADMIN_USER_IDS`: Lista de IDs de usuarios separados por comas (sin espacios)

#### Variables Opcionales:

```
OPENAI_API_KEY=tu_api_key_de_openai_aqui
```

Solo necesitas esta si quieres usar las funciones de IA avanzada.

### Paso 3: Configurar el Servicio

1. **Auto-Deploy**: Activa "Auto-Deploy" si quieres que se despliegue automáticamente en cada push
2. **Instance Type**: El plan gratuito es suficiente para empezar
3. **Health Check**: No es necesario para Background Workers (solo para Web Services)

### Paso 4: Desplegar

1. Haz clic en **"Create Background Worker"**
2. Render comenzará a construir y desplegar tu aplicación
3. Revisa los logs para verificar que todo funciona correctamente

### ⚠️ Si ya creaste un Web Service por error

Si ya creaste un Web Service y recibes el error "Port scan timeout reached", tienes dos opciones:

**Opción A (Recomendada)**: Eliminar el Web Service y crear un Background Worker
1. Elimina el Web Service actual
2. Sigue los pasos anteriores para crear un Background Worker

**Opción B**: Convertir el Web Service en Background Worker
1. Ve a la configuración del servicio
2. Cambia el tipo de servicio a "Background Worker" (si está disponible)
3. O simplemente crea un nuevo Background Worker y elimina el Web Service

## 🔍 Verificación

Una vez desplegado, verifica en los logs que veas:

```
Bot iniciado correctamente. Presiona CTRL+C para detenerlo.
🤖 Chatbot de IA activado - Los usuarios pueden escribir en lenguaje natural
```

Si ves el error:
```
RuntimeError: TELEGRAM_BOT_TOKEN no está configurado...
```

Significa que las variables de entorno no están configuradas correctamente. Verifica:
1. Que las variables estén escritas exactamente como se muestra arriba
2. Que no haya espacios extra en los valores
3. Que hayas guardado los cambios en Render

## 📝 Notas Importantes

- **NO subas `config_secret.py` a Git**: Este archivo está en `.gitignore` por seguridad
- **Usa siempre variables de entorno en producción**: Es más seguro que archivos de configuración
- **El bot se ejecuta continuamente**: Render mantendrá el servicio activo 24/7
- **Logs**: Puedes ver los logs en tiempo real desde el dashboard de Render

## 🐛 Solución de Problemas

### Error: "Port scan timeout reached, no open ports detected"

**Causa**: Creaste un Web Service en lugar de un Background Worker.

**Solución**:
1. Elimina el Web Service actual
2. Crea un nuevo **Background Worker** (no Web Service)
3. Usa la misma configuración pero selecciona "Background Worker" en lugar de "Web Service"
4. Los Background Workers no requieren escuchar en un puerto, perfecto para bots con polling

### Error: "TELEGRAM_BOT_TOKEN no está configurado"

**Solución**: 
1. Ve a la sección "Environment" de tu servicio en Render
2. Verifica que `TELEGRAM_BOT_TOKEN` esté configurada
3. Asegúrate de que el valor no tenga comillas adicionales
4. Reinicia el servicio después de agregar/modificar variables

### Error de conexión con la API de Telegram

Si ves errores como:
```
File ".../telegram/request/_baserequest.py", line 375, in _request_wrapper
    raise exception
```

**Posibles causas y soluciones**:

1. **Token inválido o expirado**:
   - Verifica que el token en las variables de entorno sea correcto
   - Obtén un nuevo token de [@BotFather](https://t.me/BotFather) si es necesario
   - Asegúrate de que no haya espacios extra en el token

2. **Problemas de red temporales**:
   - El bot maneja automáticamente errores de red y reintenta
   - Si persiste, espera unos minutos y revisa los logs nuevamente
   - Render puede tener problemas de conectividad ocasionales

3. **Otro bot usando el mismo token**:
   - Solo un bot puede usar un token a la vez
   - Si tienes el bot corriendo localmente, deténlo antes de desplegar en Render
   - Verifica que no tengas múltiples instancias del bot corriendo

4. **Bot bloqueado o deshabilitado**:
   - Verifica en [@BotFather](https://t.me/BotFather) que el bot esté activo
   - Asegúrate de que el bot no haya sido bloqueado por usuarios

**Qué hacer**:
- Revisa los logs completos en Render para ver el tipo específico de error
- El bot ahora tiene mejor manejo de errores y debería recuperarse automáticamente
- Si el error persiste, reinicia el servicio en Render

### El bot no responde

**Solución**:
1. Revisa los logs en Render para ver errores
2. Verifica que el token de Telegram sea válido
3. Asegúrate de que tu bot esté activo en Telegram
4. Verifica que el servicio esté corriendo (no en estado "stopped")

### Error de importación

**Solución**:
1. Verifica que `requirements.txt` tenga todas las dependencias
2. Revisa los logs de build para ver qué paquetes fallan al instalar
3. Asegúrate de que la versión de Python sea compatible (Python 3.10+)

## 🔐 Seguridad

- Nunca compartas tus tokens o API keys
- Usa variables de entorno en lugar de archivos de configuración en producción
- Mantén `config_secret.py` en `.gitignore`
- Revisa regularmente los logs para detectar actividad sospechosa

