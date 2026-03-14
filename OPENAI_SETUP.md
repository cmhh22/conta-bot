# Configuración de OpenAI

Este documento explica cómo configurar OpenAI para mejorar la comprensión del lenguaje natural del chatbot.

## 🔑 Cómo Obtener un Token de OpenAI

### Paso 1: Crear una Cuenta en OpenAI

1. Ve a [https://platform.openai.com/](https://platform.openai.com/)
2. Haz clic en **"Sign up"** (Registrarse)
3. Completa el registro con tu email o cuenta de Google/Microsoft

### Paso 2: Agregar Método de Pago

1. Una vez registrado, ve a **"Settings"** → **"Billing"**
2. Agrega un método de pago (tarjeta de crédito)
3. OpenAI requiere método de pago para usar la API (aunque hay créditos gratuitos iniciales)

### Paso 3: Generar API Key

1. Ve a [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Haz clic en **"Create new secret key"**
3. Dale un nombre descriptivo (ej: "ContaBot")
4. **IMPORTANTE**: Copia la clave inmediatamente, solo se muestra una vez
5. Guarda la clave de forma segura

### Paso 4: Configurar en el Bot

Tienes dos opciones:

#### Opción A: Variable de Entorno (Recomendado)

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="tu-api-key-aqui"

# Windows CMD
set OPENAI_API_KEY=tu-api-key-aqui

# Linux/Mac
export OPENAI_API_KEY="tu-api-key-aqui"
```

#### Opción B: Archivo config_secret.py

Agrega la clave a tu archivo `config_secret.py`:

```python
TOKEN = "tu_token_telegram"
ADMIN_USER_IDS = [123456789]

# OpenAI Configuration
OPENAI_API_KEY = "sk-proj-..."  # Tu API key aquí
```

Y actualiza `core/config.py` para leerla:

```python
# En config_secret.py ya está, solo necesitas agregarlo allí
```

## 💰 Costos de OpenAI

- **Modelo usado**: `gpt-4o-mini` (el más económico)
- **Costo aproximado**: ~$0.15 por 1M tokens de entrada, ~$0.60 por 1M tokens de salida
- **Uso típico**: Cada mensaje del usuario consume ~200-500 tokens
- **Estimación**: ~2000-5000 mensajes por $1 USD

### Créditos Gratuitos

OpenAI suele ofrecer créditos gratuitos iniciales ($5-18 USD) para nuevos usuarios, suficientes para probar el sistema.

## ✅ Verificar que Funciona

1. Inicia el bot: `python bot.py`
2. Deberías ver en los logs: `"🤖 OpenAI activado - Usando IA avanzada..."`
3. Prueba escribiendo: "Hola, ¿cuánto dinero hay en las cajas?"
4. El bot debería responder correctamente

## 🔄 Fallback Automático

Si OpenAI no está configurado o falla, el sistema automáticamente usa el **parser de reglas básico** que también funciona bien para la mayoría de casos.

## 🛡️ Seguridad

- **NUNCA** compartas tu API key
- **NUNCA** la subas a repositorios públicos
- Usa variables de entorno o archivos `.gitignore`
- Si comprometes una key, revócala inmediatamente en OpenAI

## 📊 Monitoreo de Uso

Puedes monitorear tu uso en:
- [https://platform.openai.com/usage](https://platform.openai.com/usage)

Aquí verás cuántos tokens has usado y cuánto has gastado.

## 🚨 Límites y Rate Limits

OpenAI tiene límites de rate (velocidad de peticiones). Si el bot recibe muchos mensajes simultáneos, puede haber delays. El sistema maneja esto automáticamente con el fallback a reglas.

## 💡 Consejos

- El modelo `gpt-4o-mini` es rápido y económico, perfecto para este uso
- Si necesitas más precisión, puedes cambiar a `gpt-4o` en `ai/openai_service.py`
- Los costos son muy bajos para uso normal (centavos por día)

