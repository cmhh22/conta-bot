# 🚀 Guia de Despliegue en Render

Esta guia te ayudara a desplegar tu bot de Telegram en Render.

## 📋 Requisitos Previos

1. Cuenta en [Render.com](https://render.com)
2. Repositorio Git (GitHub, GitLab, etc.) con tu codigo
3. Token de Telegram Bot (obtener de [@BotFather](https://t.me/BotFather))
4. IDs de usuarios administradores de Telegram

## 🔧 Configuration en Render

### Paso 1: Create un Nuevo Servicio (IMPORTANTE: Background Worker)

**⚠️ IMPORTANTE**: Para bots de Telegram que usan polling, debes create un **Background Worker**, NO un Web Service.

1. Ve a tu dashboard de Render
2. Haz clic en **"New +"** → **"Background Worker"** (NO "Web Service")
3. Conecta tu repositorio Git
4. Configura los siguientes parametros:
   - **Name**: `conta-bot` (o el nombre que prefieras)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`

**Por que Background Worker?**
- Los bots de Telegram con polling no necesitan escuchar en un puerto HTTP
- Los Web Services en Render requieren que escuches en un puerto, lo cual no es necesario para bots
- Los Background Workers son perfectos para procesos de larga duracion como bots

### Paso 2: Configure Variables de Entorno

En la seccion **"Environment"** de tu servicio en Render, agrega las siguientes variables de entorno:

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

### Paso 3: Configure el Servicio

1. **Auto-Deploy**: Activa "Auto-Deploy" si quieres que se despliegue automaticamente en cada push
2. **Instance Type**: El plan gratuito es suficiente para empezar
3. **Health Check**: No es necesario para Background Workers (solo para Web Services)

### Paso 4: Desplegar

1. Haz clic en **"Create Background Worker"**
2. Render comenzara a construir y desplegar tu aplicacion
3. Revisa los logs para verificar que todo funciona correctamente

### ⚠️ Si ya creaste un Web Service por error

Si ya creaste un Web Service y recibes el error "Port scan timeout reached", tienes dos opciones:

**Opcion A (Recomendada)**: Delete el Web Service y create un Background Worker
1. Elimina el Web Service actual
2. Sigue los pasos anteriores para create un Background Worker

**Opcion B**: Convertir el Web Service en Background Worker
1. Ve a la configuration del servicio
2. Cambia el tipo de servicio a "Background Worker" (si esta disponible)
3. O simplemente crea un nuevo Background Worker y elimina el Web Service

## 🔍 Verificacion

Una vez desplegado, verifica en los logs que veas:

```
Bot iniciado correctamente. Presiona CTRL+C para detenerlo.
🤖 Chatbot de IA activado - Los usuarios pueden escribir en lenguaje natural
```

Si ves el error:
```
RuntimeError: TELEGRAM_BOT_TOKEN no esta configurado...
```

Significa que las variables de entorno no estan configuradas correctamente. Verifica:
1. Que las variables esten escritas exactamente como se muestra arriba
2. Que no haya espacios extra en los valores
3. Que hayas guardado los cambios en Render

## 📝 Notas Importantes

- **NO subas `config_secret.py` a Git**: Este archivo esta en `.gitignore` por seguridad
- **Usa siempre variables de entorno en produccion**: Es mas seguro que archivos de configuration
- **El bot se ejecuta continuamente**: Render mantendra el servicio activo 24/7
- **Logs**: Puedes ver los logs en tiempo real desde el dashboard de Render

## 🐛 Solucion de Problemas

### Error: "Port scan timeout reached, no open ports detected"

**Causa**: Creaste un Web Service en lugar de un Background Worker.

**Solucion**:
1. Elimina el Web Service actual
2. Crea un nuevo **Background Worker** (no Web Service)
3. Usa la misma configuration pero select "Background Worker" en lugar de "Web Service"
4. Los Background Workers no requieren escuchar en un puerto, perfecto para bots con polling

### Error: "TELEGRAM_BOT_TOKEN no esta configurado"

**Solucion**: 
1. Ve a la seccion "Environment" de tu servicio en Render
2. Verifica que `TELEGRAM_BOT_TOKEN` este configurada
3. Asegurate de que el valor no tenga comillas adicionales
4. Reinicia el servicio despues de agregar/modificar variables

### Error: conexion con la API de Telegram

Si ves errores como:
```
File ".../telegram/request/_baserequest.py", line 375, in _request_wrapper
    raise exception
```

**Posibles causas y soluciones**:

1. **Token invalid o expirado**:
   - Verifica que el token en las variables de entorno sea correcto
   - Obten un nuevo token de [@BotFather](https://t.me/BotFather) si es necesario
   - Asegurate de que no haya espacios extra en el token

2. **Problemas de red temporales**:
   - El bot maneja automaticamente errores de red y reintenta
   - Si persiste, espera unos minutos y revisa los logs nuevamente
   - Render puede tener problemas de conectividad ocasionales

3. **Otro bot usando el mismo token**:
   - Solo un bot puede usar un token a la vez
   - Si tienes el bot corriendo localmente, detenlo antes de desplegar en Render
   - Verifica que no tengas multiples instancias del bot corriendo

4. **Bot bloqueado o deshabilitado**:
   - Verifica en [@BotFather](https://t.me/BotFather) que el bot este activo
   - Asegurate de que el bot no haya sido bloqueado por usuarios

**Que hacer**:
- Revisa los logs completos en Render para ver el tipo especifico de error
- El bot ahora tiene mejor manejo de errores y deberia recuperarse automaticamente
- Si el error persiste, reinicia el servicio en Render

### El bot no responde

**Solucion**:
1. Revisa los logs en Render para ver errores
2. Verifica que el token de Telegram sea valid
3. Asegurate de que tu bot este activo en Telegram
4. Verifica que el servicio este corriendo (no en estado "stopped")

### Error: importacion

**Solucion**:
1. Verifica que `requirements.txt` tenga todas las dependencias
2. Revisa los logs de build para ver que paquetes fallan al instalar
3. Asegurate de que la version de Python sea compatible (Python 3.10+)

## 🔐 Seguridad

- Nunca compartas tus tokens o API keys
- Usa variables de entorno en lugar de archivos de configuration en produccion
- Manten `config_secret.py` en `.gitignore`
- Revisa regularmente los logs para detectar actividad sospechosa

