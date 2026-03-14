"""
Ejecutor de acciones - Ejecuta las acciones basadas en intenciones parseadas.
"""
import logging
from typing import Dict, Any
from ai.intent_parser import IntentType
from ai.financial_advisor import FinancialAdvisor
from services.contabilidad_service import ContabilidadService, DeudaService
from services.inventario_service import InventarioService
from services.contenedores_service import ContenedorService
from utils.validators import ValidationError

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Ejecuta acciones basadas en intenciones parseadas."""
    
    @staticmethod
    async def execute_intent(
        intent: IntentType,
        params: Dict[str, Any],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Ejecuta una acción basada en la intención y parámetros.
        
        Returns:
            Dict con 'success', 'message', y datos adicionales
        """
        try:
            if intent == IntentType.BALANCE:
                return await ActionExecutor._execute_balance()
            
            elif intent == IntentType.INGRESO:
                return await ActionExecutor._execute_ingreso(params, user_id)
            
            elif intent == IntentType.GASTO:
                return await ActionExecutor._execute_gasto(params, user_id)
            
            elif intent == IntentType.TRASPASO:
                return await ActionExecutor._execute_traspaso(params, user_id)
            
            elif intent == IntentType.DEUDAS:
                return await ActionExecutor._execute_deudas()
            
            elif intent == IntentType.HISTORIAL:
                return await ActionExecutor._execute_historial(params)
            
            elif intent == IntentType.STOCK:
                return await ActionExecutor._execute_stock()
            
            elif intent == IntentType.VENTA:
                return await ActionExecutor._execute_venta(params, user_id)
            
            elif intent == IntentType.ENTRADA:
                return await ActionExecutor._execute_entrada(params)
            
            elif intent == IntentType.GANANCIA:
                return await ActionExecutor._execute_ganancia()
            
            elif intent == IntentType.STOCK_CONSIGNADO:
                return await ActionExecutor._execute_stock_consignado(params)
            
            elif intent == IntentType.EXPORTAR:
                return await ActionExecutor._execute_exportar()
            
            elif intent == IntentType.CONTENEDOR_CREAR:
                return await ActionExecutor._execute_contenedor_crear(params)
            
            elif intent == IntentType.CONTENEDOR_LISTAR:
                return await ActionExecutor._execute_contenedor_listar()
            
            elif intent == IntentType.CONTENEDOR_EDITAR:
                return await ActionExecutor._execute_contenedor_editar(params)
            
            elif intent == IntentType.CONTENEDOR_ELIMINAR:
                return await ActionExecutor._execute_contenedor_eliminar(params)
            
            elif intent == IntentType.CONTENEDORES:
                # Intención general de contenedores, mostrar lista
                return await ActionExecutor._execute_contenedor_listar()
            
            elif intent == IntentType.ANALISIS_FINANCIERO:
                return await ActionExecutor._execute_analisis_financiero(params)
            
            elif intent == IntentType.CLARIFICATION:
                pregunta = params.get("pregunta", "¿Podrías darme más detalles sobre lo que necesitas?")
                return {"success": True, "message": f"🤔 {pregunta}"}
            
            elif intent == IntentType.GREETING:
                return {
                    "success": True,
                    "message": "👋 ¡Hola! Soy <b>ContaBot</b>, tu asistente financiero con IA.\n\n"
                              "Puedo ayudarte con:\n"
                              "• 💰 Contabilidad y balances\n"
                              "• 📦 Inventario y ventas\n"
                              "• 📊 Reportes inteligentes\n"
                              "• 🧠 Análisis financiero con IA\n"
                              "• 📋 Gestión de deudas\n\n"
                              "Escríbeme en lenguaje natural o usa /start para el menú."
                }
            
            elif intent == IntentType.HELP:
                return {
                    "success": True,
                    "message": "📚 <b>Ayuda - Comandos Disponibles</b>\n\n"
                              "Puedes usar lenguaje natural o comandos:\n\n"
                              "💰 <b>Contabilidad:</b>\n"
                              "• \"Ver balance\" o \"/balance\"\n"
                              "• \"Registrar ingreso de 100 USD en CFG\"\n"
                              "• \"Gasto de 50 CUP en SC para pago de renta\"\n\n"
                              "📦 <b>Inventario:</b>\n"
                              "• \"Ver stock\" o \"/stock\"\n"
                              "• \"Venta de SHIRT01, 2 unidades, 60 USD\"\n\n"
                              "📦 <b>Contenedores:</b>\n"
                              "• \"Listar contenedores\" o \"Ver contenedores\"\n"
                              "• \"Crear contenedor llamado ALMACEN1\"\n\n"
                              "🧠 <b>IA Financiera:</b>\n"
                              "• \"Analizar estado del negocio\"\n"
                              "• \"¿Cómo van las tendencias?\"\n"
                              "• \"Análisis de gastos\"\n"
                              "• \"Reporte inteligente de inventario\"\n\n"
                              "📊 <b>Reportes:</b>\n"
                              "• \"Ver deudas\" o \"/deudas\"\n"
                              "• \"Historial de últimos 7 días\"\n\n"
                              "También puedes usar el menú con /start"
                }
            
            else:
                return {
                    "success": False,
                    "message": "No entendí tu solicitud. Puedes:\n\n"
                              "• Usar comandos como /balance, /stock, etc.\n"
                              "• Escribir en lenguaje natural\n"
                              "• Usar /start para ver el menú\n"
                              "• Escribir \"ayuda\" para más información"
                }
        
        except ValidationError as e:
            return {
                "success": False,
                "message": f"❌ Error de validación: {e}"
            }
        except ValueError as e:
            return {
                "success": False,
                "message": f"❌ Error: {e}"
            }
        except Exception as e:
            logger.error(f"Error ejecutando acción {intent}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"❌ Ocurrió un error al procesar tu solicitud: {str(e)}"
            }
    
    @staticmethod
    async def _execute_balance() -> Dict[str, Any]:
        """Ejecuta consulta de balance."""
        balances = ContabilidadService.obtener_balance()
        
        if not balances:
            return {
                "success": True,
                "message": "No hay ningún movimiento registrado todavía."
            }
        
        respuesta = "--- 📊 Balance General ---\n\n"
        for caja, monedas in balances.items():
            respuesta += f"<b>CAJA: {caja.upper()}</b>\n"
            for moneda, total in monedas.items():
                respuesta += f"  • {total:,.2f} {moneda.upper()}\n"
            respuesta += "\n"
        
        return {"success": True, "message": respuesta}
    
    @staticmethod
    async def _execute_ingreso(params: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Ejecuta registro de ingreso."""
        monto = params.get('monto')
        moneda = params.get('moneda', 'usd')
        caja = params.get('caja', 'cfg')
        
        if not monto:
            return {
                "success": False,
                "message": "❌ Necesito saber el monto a ingresar. Ejemplo: \"Ingresar 100 USD en CFG\""
            }
        
        resultado = ContabilidadService.registrar_ingreso(monto, moneda, caja, user_id)
        
        return {
            "success": True,
            "message": (
                f"✅ <b>¡Ingreso registrado!</b>\n\n"
                f"💰 Monto: {monto:.2f} {moneda.upper()}\n"
                f"📦 Caja: {caja.upper()}"
            )
        }
    
    @staticmethod
    async def _execute_gasto(params: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Ejecuta registro de gasto."""
        monto = params.get('monto')
        moneda = params.get('moneda', 'usd')
        caja = params.get('caja', 'cfg')
        descripcion = params.get('descripcion', 'Gasto')
        
        if not monto:
            return {
                "success": False,
                "message": "❌ Necesito saber el monto a gastar. Ejemplo: \"Gasto de 50 CUP en SC para pago de renta\""
            }
        
        resultado = ContabilidadService.registrar_gasto(monto, moneda, caja, user_id, descripcion)
        
        return {
            "success": True,
            "message": (
                f"💸 <b>Gasto Registrado!</b>\n\n"
                f"💰 Monto: -{monto:.2f} {moneda.upper()} de {caja.upper()}\n"
                f"📝 Descripción: {descripcion}"
            )
        }
    
    @staticmethod
    async def _execute_traspaso(params: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Ejecuta traspaso entre cajas."""
        monto = params.get('monto')
        moneda_origen = params.get('moneda', 'usd')
        caja_origen = params.get('caja_origen') or params.get('caja', 'cfg')
        caja_destino = params.get('caja_destino', 'sc')
        moneda_destino = params.get('moneda_destino', moneda_origen)
        motivo = params.get('descripcion', 'Traspaso')
        
        if not monto:
            return {
                "success": False,
                "message": "❌ Necesito saber el monto a transferir. Ejemplo: \"Transferir 20 USD de CFG a SC\""
            }
        
        if caja_origen == caja_destino:
            return {
                "success": False,
                "message": "❌ Las cajas de origen y destino deben ser diferentes."
            }
        
        resultado = ContabilidadService.registrar_traspaso(
            monto, moneda_origen, caja_origen, moneda_destino, caja_destino, user_id, motivo
        )
        
        return {
            "success": True,
            "message": (
                f"✅ <b>Traspaso Registrado!</b>\n\n"
                f"Origen: -{resultado['monto_origen']:.2f} {resultado['moneda_origen'].upper()} "
                f"de {resultado['caja_origen'].upper()}\n"
                f"Destino: +{resultado['monto_destino']:.2f} {resultado['moneda_destino'].upper()} "
                f"a {resultado['caja_destino'].upper()}\n"
                f"Motivo: {motivo}"
            )
        }
    
    @staticmethod
    async def _execute_deudas() -> Dict[str, Any]:
        """Ejecuta consulta de deudas."""
        deudas = DeudaService.obtener_deudas_pendientes()
        
        if not deudas['por_pagar'] and not deudas['por_cobrar']:
            return {
                "success": True,
                "message": "✅ No hay deudas pendientes (por pagar o por cobrar)."
            }
        
        respuesta = "📊 <b>ESTADO DE DEUDAS PENDIENTES</b> 📊\n\n"
        
        # Cuentas por pagar
        respuesta += "❌ <b>CUENTAS POR PAGAR (Proveedores)</b>\n"
        if deudas['por_pagar']:
            totales_por_pagar = {}
            for deuda in deudas['por_pagar']:
                respuesta += f"  • {deuda['actor_id']}: -{deuda['monto']:,.2f} {deuda['moneda'].upper()}\n"
                totales_por_pagar[deuda['moneda']] = totales_por_pagar.get(deuda['moneda'], 0) + deuda['monto']
            respuesta += "  --- TOTALES POR PAGAR ---\n"
            for moneda, total in totales_por_pagar.items():
                respuesta += f"  Total {moneda.upper()}: -{total:,.2f} {moneda.upper()}\n"
        else:
            respuesta += "  <i>No hay deudas con proveedores pendientes.</i>\n"
        
        respuesta += "\n"
        
        # Cuentas por cobrar
        respuesta += "✅ <b>CUENTAS POR COBRAR (Vendedores)</b>\n"
        if deudas['por_cobrar']:
            totales_por_cobrar = {}
            for deuda in deudas['por_cobrar']:
                respuesta += f"  • {deuda['actor_id']}: +{deuda['monto']:,.2f} {deuda['moneda'].upper()}\n"
                totales_por_cobrar[deuda['moneda']] = totales_por_cobrar.get(deuda['moneda'], 0) + deuda['monto']
            respuesta += "  --- TOTALES POR COBRAR ---\n"
            for moneda, total in totales_por_cobrar.items():
                respuesta += f"  Total {moneda.upper()}: +{total:,.2f} {moneda.upper()}\n"
        else:
            respuesta += "  <i>No hay deudas de vendedores pendientes.</i>\n"
        
        return {"success": True, "message": respuesta}
    
    @staticmethod
    async def _execute_historial(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta consulta de historial."""
        dias = params.get('dias', 7)
        movimientos = ContabilidadService.obtener_historial(dias)
        
        if not movimientos:
            return {
                "success": True,
                "message": f"✅ No se encontraron movimientos registrados en los últimos {dias} días."
            }
        
        reporte = f"⏳ <b>HISTORIAL DE MOVIMIENTOS ({dias} días)</b> 📜\n\n"
        
        # Mostrar solo los últimos 10 movimientos para no saturar
        for mov in movimientos[:10]:
            tipo = mov['tipo']
            simbolo = "+" if tipo in ('ingreso', 'venta') else "-"
            color = "🟢" if tipo in ('ingreso', 'venta') else "🔴" if tipo in ('gasto',) else "🔵"
            
            from datetime import datetime
            try:
                fecha_dt = datetime.strptime(mov['fecha'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                fecha_formateada = fecha_dt.strftime('%d/%m %H:%M')
            except:
                fecha_formateada = mov['fecha'][:10]
            
            reporte += (
                f"{color} <code>{fecha_formateada}</code> | "
                f"<b>{simbolo}{mov['monto']:,.2f} {mov['moneda'].upper()}</b> en {mov['caja'].upper()}\n"
                f"  {tipo.upper()}: {mov['descripcion'][:50]}...\n"
            )
        
        if len(movimientos) > 10:
            reporte += f"\n<i>(Mostrando 10 de {len(movimientos)} movimientos. Usa /historial para ver todos)</i>"
        
        return {"success": True, "message": reporte}
    
    @staticmethod
    async def _execute_stock() -> Dict[str, Any]:
        """Ejecuta consulta de stock."""
        productos = InventarioService.obtener_stock()
        
        if not productos:
            return {
                "success": True,
                "message": "El inventario está actualmente vacío (stock = 0)."
            }
        
        respuesta = "--- 📋 Inventario Actual ---\n\n"
        for producto in productos[:15]:  # Limitar a 15 productos
            respuesta += (
                f"📦 <b>{producto['codigo']}</b> ({producto['nombre']})\n"
                f"  • Stock: {producto['stock']:,.0f} unidades\n"
                f"  • Costo: {producto['costo_unitario']:,.2f} {producto['moneda_costo'].upper()}\n\n"
            )
        
        if len(productos) > 15:
            respuesta += f"<i>(Mostrando 15 de {len(productos)} productos. Usa /stock para ver todos)</i>"
        
        return {"success": True, "message": respuesta}
    
    @staticmethod
    async def _execute_venta(params: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Ejecuta registro de venta."""
        codigo = params.get('codigo')
        cantidad = params.get('cantidad') or params.get('monto')  # Usar monto como cantidad si no hay cantidad
        monto_total = params.get('monto')
        moneda = params.get('moneda', 'usd')
        caja = params.get('caja', 'sc')
        nota = params.get('descripcion', 'Venta')
        
        if not codigo or not cantidad or not monto_total:
            return {
                "success": False,
                "message": "❌ Necesito código, cantidad y monto. Ejemplo: \"Venta de SHIRT01, 2 unidades, 60 USD\""
            }
        
        # Intentar detectar si es consignada
        vendedor = params.get('actor')
        if vendedor:
            stock_consignado = InventarioService.obtener_stock_consignado(vendedor)
            for item in stock_consignado:
                if item['codigo'] == codigo and item['stock'] >= cantidad:
                    resultado = InventarioService.registrar_venta_consignada(
                        codigo, cantidad, monto_total, moneda, caja, vendedor, user_id, nota
                    )
                    return {
                        "success": True,
                        "message": (
                            f"✅ <b>Venta Consignada Registrada!</b>\n\n"
                            f"Vendedor: {vendedor}\n"
                            f"Producto: {codigo} ({cantidad} u.)\n"
                            f"Ingreso: {monto_total:.2f} {moneda.upper()}"
                        )
                    }
        
        # Venta estándar
        resultado = InventarioService.registrar_venta_estandar(
            codigo, cantidad, monto_total, moneda, caja, user_id, nota
        )
        
        return {
            "success": True,
            "message": (
                f"✅ <b>Venta Registrada!</b>\n\n"
                f"Producto: {codigo} ({cantidad} u.)\n"
                f"Ingreso: {monto_total:.2f} {moneda.upper()}\n"
                f"Caja: {caja.upper()}"
            )
        }
    
    @staticmethod
    async def _execute_entrada(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta registro de entrada de mercancía."""
        codigo = params.get('codigo')
        cantidad = params.get('cantidad')
        costo_unitario = params.get('monto')  # Usar monto como costo si no hay otro
        moneda = params.get('moneda', 'usd')
        proveedor = params.get('actor', 'PROVEEDOR')
        
        if not codigo or not cantidad or not costo_unitario:
            return {
                "success": False,
                "message": "❌ Necesito código, cantidad y costo. Ejemplo: \"Entrada de HUEVOS, 100 unidades, 0.5 USD cada uno\""
            }
        
        resultado = InventarioService.registrar_entrada(
            codigo, cantidad, costo_unitario, moneda, proveedor
        )
        
        return {
            "success": True,
            "message": (
                f"📦 <b>Entrada Registrada!</b>\n\n"
                f"Código: {codigo}\n"
                f"Cantidad: +{cantidad} unidades\n"
                f"Proveedor: {proveedor}\n"
                f"Deuda generada: {resultado['costo_total']:.2f} {moneda.upper()}"
            )
        }
    
    @staticmethod
    async def _execute_ganancia() -> Dict[str, Any]:
        """Ejecuta consulta de ganancias."""
        ganancias = InventarioService.calcular_ganancias()
        
        from utils.currency import get_tasa
        
        return {
            "success": True,
            "message": (
                f"📈 <b>Reporte de Ganancia Bruta</b>\n\n"
                f"💰 Ingresos: {ganancias['ingresos_total_usd']:,.2f} USD\n"
                f"🛒 Costos: {ganancias['costos_total_usd']:,.2f} USD\n"
                f"💵 <b>GANANCIA BRUTA: {ganancias['margen_bruto_usd']:,.2f} USD</b>"
            )
        }
    
    @staticmethod
    async def _execute_stock_consignado(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta consulta de stock consignado."""
        vendedor = params.get('actor')
        
        if not vendedor:
            return {
                "success": False,
                "message": "❌ Necesito el nombre del vendedor. Ejemplo: \"Stock consignado de MARIA\""
            }
        
        stock_items = InventarioService.obtener_stock_consignado(vendedor)
        
        reporte = f"📦 <b>STOCK CONSIGNADO: {vendedor}</b>\n\n"
        if stock_items:
            for item in stock_items:
                reporte += f"  • <b>{item['codigo']}</b>: {int(item['stock'])} unidades\n"
        else:
            reporte += "  <i>No tiene stock pendiente.</i>"
        
        return {"success": True, "message": reporte}
    
    @staticmethod
    async def _execute_exportar() -> Dict[str, Any]:
        """Ejecuta exportación."""
        return {
            "success": True,
            "message": "💾 Para exportar, usa el comando /exportar que te enviará un archivo CSV con todos los movimientos."
        }
    
    @staticmethod
    async def _execute_contenedor_crear(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta creación de contenedor."""
        nombre = params.get('nombre')
        
        if not nombre:
            return {
                "success": False,
                "message": "❌ Necesito el nombre del contenedor. Ejemplo: \"Crear contenedor llamado ALMACEN1\" o \"Nuevo contenedor DEPOSITO\""
            }
        
        try:
            resultado = ContenedorService.crear(nombre)
            return {
                "success": True,
                "message": (
                    f"✅ <b>Contenedor creado!</b>\n\n"
                    f"📦 Nombre: <code>{nombre}</code>\n"
                    f"🆔 ID: {resultado['id']}"
                )
            }
        except ValueError as e:
            if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
                return {
                    "success": False,
                    "message": f"⚠️ Ya existe un contenedor con el nombre '{nombre}'. Usa otro nombre."
                }
            return {
                "success": False,
                "message": f"❌ Error: {e}"
            }
        except Exception as e:
            logger.error(f"Error creando contenedor: {e}", exc_info=True)
            return {
                "success": False,
                "message": "❌ Ocurrió un error al crear el contenedor. Intenta nuevamente."
            }
    
    @staticmethod
    async def _execute_contenedor_listar() -> Dict[str, Any]:
        """Ejecuta listado de contenedores."""
        contenedores = ContenedorService.listar()
        
        if not contenedores:
            return {
                "success": True,
                "message": "📦 <b>Contenedores</b>\n\nAún no hay contenedores registrados.\n\nPuedes crear uno diciendo: \"Crear contenedor llamado [nombre]\""
            }
        
        respuesta = "📦 <b>Lista de Contenedores</b>\n\n"
        for cont in contenedores:
            respuesta += f"🆔 <b>ID {cont['id']}</b>: <code>{cont['nombre']}</code>\n"
        
        respuesta += f"\n<i>Total: {len(contenedores)} contenedor(es)</i>"
        
        return {"success": True, "message": respuesta}
    
    @staticmethod
    async def _execute_contenedor_editar(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta edición de contenedor."""
        cont_id = params.get('id') or params.get('cont_id')
        nombre_actual = params.get('nombre_actual') or params.get('actor')
        nuevo_nombre = params.get('nuevo_nombre') or params.get('nombre')
        
        # Si no hay ID, intentar buscar por nombre
        if not cont_id and nombre_actual:
            contenedores = ContenedorService.listar()
            for cont in contenedores:
                if cont['nombre'].lower() == nombre_actual.lower():
                    cont_id = cont['id']
                    break
        
        if not cont_id:
            return {
                "success": False,
                "message": "❌ Necesito el ID o nombre del contenedor a editar. Ejemplo: \"Editar contenedor 1 a ALMACEN2\" o \"Renombrar contenedor DEPOSITO a BODEGA\""
            }
        
        if not nuevo_nombre:
            return {
                "success": False,
                "message": "❌ Necesito el nuevo nombre. Ejemplo: \"Editar contenedor 1 a ALMACEN2\" o \"Renombrar contenedor DEPOSITO a BODEGA\""
            }
        
        try:
            ContenedorService.actualizar(int(cont_id), nuevo_nombre)
            return {
                "success": True,
                "message": (
                    f"✅ <b>Contenedor actualizado!</b>\n\n"
                    f"🆔 ID: {cont_id}\n"
                    f"📦 Nuevo nombre: <code>{nuevo_nombre}</code>"
                )
            }
        except ValueError as e:
            if "no encontrado" in str(e).lower():
                return {
                    "success": False,
                    "message": f"❌ No se encontró un contenedor con ID {cont_id}."
                }
            if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
                return {
                    "success": False,
                    "message": f"⚠️ Ya existe un contenedor con el nombre '{nuevo_nombre}'. Usa otro nombre."
                }
            return {
                "success": False,
                "message": f"❌ Error: {e}"
            }
        except Exception as e:
            logger.error(f"Error editando contenedor: {e}", exc_info=True)
            return {
                "success": False,
                "message": "❌ Ocurrió un error al editar el contenedor. Intenta nuevamente."
            }
    
    @staticmethod
    async def _execute_contenedor_eliminar(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta eliminación de contenedor."""
        cont_id = params.get('id') or params.get('cont_id')
        nombre = params.get('nombre') or params.get('actor')
        
        # Si no hay ID, intentar buscar por nombre
        if not cont_id and nombre:
            contenedores = ContenedorService.listar()
            for cont in contenedores:
                if cont['nombre'].lower() == nombre.lower():
                    cont_id = cont['id']
                    break
        
        if not cont_id:
            return {
                "success": False,
                "message": "❌ Necesito el ID o nombre del contenedor a eliminar. Ejemplo: \"Eliminar contenedor 1\" o \"Borrar contenedor ALMACEN1\""
            }
        
        try:
            # Obtener nombre antes de eliminar para mostrar en el mensaje
            contenedor = ContenedorService.obtener_por_id(int(cont_id))
            nombre_eliminado = contenedor['nombre'] if contenedor else f"ID {cont_id}"
            
            ContenedorService.eliminar(int(cont_id))
            return {
                "success": True,
                "message": (
                    f"🗑️ <b>Contenedor eliminado!</b>\n\n"
                    f"📦 Contenedor: <code>{nombre_eliminado}</code>\n"
                    f"🆔 ID: {cont_id}"
                )
            }
        except ValueError as e:
            if "no encontrado" in str(e).lower():
                return {
                    "success": False,
                    "message": f"❌ No se encontró un contenedor con ID {cont_id}."
                }
            return {
                "success": False,
                "message": f"❌ Error: {e}"
            }
        except Exception as e:
            logger.error(f"Error eliminando contenedor: {e}", exc_info=True)
            return {
                "success": False,
                "message": "❌ Ocurrió un error al eliminar el contenedor. Intenta nuevamente."
            }
    
    @staticmethod
    async def _execute_analisis_financiero(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta análisis financiero inteligente."""
        tipo = params.get("tipo", "general")
        return FinancialAdvisor.generar_analisis(tipo)

