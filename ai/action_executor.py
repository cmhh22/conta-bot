"""
Ejecutor de actions - Ejecuta las actions basadas en intenciones parseadas.
"""
import logging
from typing import Dict, Any
from ai.intent_parser import IntentType
from ai.financial_advisor import FinancialAdvisor
from services.contabilidad_service import ContabilidadService, DeudaService
from services.inventario_service import InventarioService
from services.containeres_service import ContainerService
from utils.validators import ValidationError

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Ejecuta actions basadas en intenciones parseadas."""
    
    @staticmethod
    async def execute_intent(
        intent: IntentType,
        params: Dict[str, Any],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Ejecuta una action basada en la intencion y parametros.
        
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
                return await ActionExecutor._execute_container_create(params)
            
            elif intent == IntentType.CONTENEDOR_LISTAR:
                return await ActionExecutor._execute_container_listar()
            
            elif intent == IntentType.CONTENEDOR_EDITAR:
                return await ActionExecutor._execute_container_editar(params)
            
            elif intent == IntentType.CONTENEDOR_ELIMINAR:
                return await ActionExecutor._execute_container_delete(params)
            
            elif intent == IntentType.CONTENEDORES:
                # Intencion general de containeres, mostrar lista
                return await ActionExecutor._execute_container_listar()
            
            elif intent == IntentType.ANALISIS_FINANCIERO:
                return await ActionExecutor._execute_analisis_financiero(params)
            
            elif intent == IntentType.CLARIFICATION:
                pregunta = params.get("pregunta", "Podrias darme mas detalles sobre lo que necesitas?")
                return {"success": True, "message": f"🤔 {pregunta}"}
            
            elif intent == IntentType.GREETING:
                return {
                    "success": True,
                    "message": "👋 Hola! Soy <b>ContaBot</b>, tu asistente financiero con IA.\n\n"
                              "Puedo ayudarte con:\n"
                              "• 💰 Contabilidad y balances\n"
                              "• 📦 Inventario y ventas\n"
                              "• 📊 Reportes inteligentes\n"
                              "• 🧠 Analisis financiero con IA\n"
                              "• 📋 Management de deudas\n\n"
                              "Escribeme en lenguaje natural o usa /start para el menu."
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
                              "📦 <b>Containeres:</b>\n"
                              "• \"Listar containeres\" o \"Ver containeres\"\n"
                              "• \"Create container llamado ALMACEN1\"\n\n"
                              "🧠 <b>IA Financiera:</b>\n"
                              "• \"Analizar estado del negocio\"\n"
                              "• \"Como van las tendencias?\"\n"
                              "• \"Analisis de gastos\"\n"
                              "• \"Reporte inteligente de inventario\"\n\n"
                              "📊 <b>Reportes:</b>\n"
                              "• \"Ver deudas\" o \"/deudas\"\n"
                              "• \"Historial de ultimos 7 days\"\n\n"
                              "Tambien puedes usar el menu con /start"
                }
            
            else:
                return {
                    "success": False,
                    "message": "No entendi tu solicitud. Puedes:\n\n"
                              "• Usar comandos como /balance, /stock, etc.\n"
                              "• Escribir en lenguaje natural\n"
                              "• Usar /start para ver el menu\n"
                              "• Escribir \"ayuda\" para mas informacion"
                }
        
        except ValidationError as e:
            return {
                "success": False,
                "message": f"❌ Error: validacion: {e}"
            }
        except ValueError as e:
            return {
                "success": False,
                "message": f"❌ Error: {e}"
            }
        except Exception as e:
            logger.error(f"Error ejecutando action {intent}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"❌ An error occurred al procesar tu solicitud: {str(e)}"
            }
    
    @staticmethod
    async def _execute_balance() -> Dict[str, Any]:
        """Ejecuta consulta de balance."""
        balances = ContabilidadService.obtener_balance()
        
        if not balances:
            return {
                "success": True,
                "message": "No ningun movimiento recorded todavia."
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
                f"✅ <b>Ingreso recorded!</b>\n\n"
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
                f"📝 Description: {descripcion}"
            )
        }
    
    @staticmethod
    async def _execute_traspaso(params: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Ejecuta traspaso entre cajas."""
        monto = params.get('monto')
        moneda_source = params.get('moneda', 'usd')
        caja_source = params.get('caja_source') or params.get('caja', 'cfg')
        caja_destination = params.get('caja_destination', 'sc')
        moneda_destination = params.get('moneda_destination', moneda_source)
        motivo = params.get('descripcion', 'Traspaso')
        
        if not monto:
            return {
                "success": False,
                "message": "❌ Necesito saber el monto a transferir. Ejemplo: \"Transferir 20 USD de CFG a SC\""
            }
        
        if caja_source == caja_destination:
            return {
                "success": False,
                "message": "❌ Las cajas de source y destination deben ser diferentes."
            }
        
        resultado = ContabilidadService.registrar_traspaso(
            monto, moneda_source, caja_source, moneda_destination, caja_destination, user_id, motivo
        )
        
        return {
            "success": True,
            "message": (
                f"✅ <b>Traspaso Registrado!</b>\n\n"
                f"Origen: -{resultado['monto_source']:.2f} {resultado['moneda_source'].upper()} "
                f"de {resultado['caja_source'].upper()}\n"
                f"Destino: +{resultado['monto_destination']:.2f} {resultado['moneda_destination'].upper()} "
                f"a {resultado['caja_destination'].upper()}\n"
                f"Reason: {motivo}"
            )
        }
    
    @staticmethod
    async def _execute_deudas() -> Dict[str, Any]:
        """Ejecuta consulta de deudas."""
        deudas = DeudaService.obtener_deudas_pendientes()
        
        if not deudas['por_pagar'] and not deudas['por_cobrar']:
            return {
                "success": True,
                "message": "✅ No pending debts (por pagar o por cobrar)."
            }
        
        respuesta = "📊 <b>PENDING DEBT STATUS</b> 📊\n\n"
        
        # Cuentas por pagar
        respuesta += "❌ <b>CUENTAS POR PAGAR (Supplieres)</b>\n"
        if deudas['por_pagar']:
            totales_por_pagar = {}
            for deuda in deudas['por_pagar']:
                respuesta += f"  • {deuda['actor_id']}: -{deuda['monto']:,.2f} {deuda['moneda'].upper()}\n"
                totales_por_pagar[deuda['moneda']] = totales_por_pagar.get(deuda['moneda'], 0) + deuda['monto']
            respuesta += "  --- TOTALES POR PAGAR ---\n"
            for moneda, total in totales_por_pagar.items():
                respuesta += f"  Total {moneda.upper()}: -{total:,.2f} {moneda.upper()}\n"
        else:
            respuesta += "  <i>No deudas with supplieres pendientes.</i>\n"
        
        respuesta += "\n"
        
        # Cuentas por cobrar
        respuesta += "✅ <b>CUENTAS POR COBRAR (Selleres)</b>\n"
        if deudas['por_cobrar']:
            totales_por_cobrar = {}
            for deuda in deudas['por_cobrar']:
                respuesta += f"  • {deuda['actor_id']}: +{deuda['monto']:,.2f} {deuda['moneda'].upper()}\n"
                totales_por_cobrar[deuda['moneda']] = totales_por_cobrar.get(deuda['moneda'], 0) + deuda['monto']
            respuesta += "  --- TOTALES POR COBRAR ---\n"
            for moneda, total in totales_por_cobrar.items():
                respuesta += f"  Total {moneda.upper()}: +{total:,.2f} {moneda.upper()}\n"
        else:
            respuesta += "  <i>No deudas de vendedores pendientes.</i>\n"
        
        return {"success": True, "message": respuesta}
    
    @staticmethod
    async def _execute_historial(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta consulta de historial."""
        days = params.get('days', 7)
        movimientos = ContabilidadService.obtener_historial(days)
        
        if not movimientos:
            return {
                "success": True,
                "message": f"✅ No se encontraron movimientos recordeds en los ultimos {days} days."
            }
        
        reporte = f"⏳ <b>TRANSACTION HISTORY ({days} days)</b> 📜\n\n"
        
        # Mostrar solo los ultimos 10 movimientos para no saturar
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
                "message": "El inventario esta actualmente empty (stock = 0)."
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
                "message": "❌ Necesito codigo, cantidad y monto. Ejemplo: \"Venta de SHIRT01, 2 unidades, 60 USD\""
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
                            f"Seller: {vendedor}\n"
                            f"Producto: {codigo} ({cantidad} u.)\n"
                            f"Ingreso: {monto_total:.2f} {moneda.upper()}"
                        )
                    }
        
        # Venta estandar
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
        """Ejecuta registro de merchandise intake."""
        codigo = params.get('codigo')
        cantidad = params.get('cantidad')
        costo_unitario = params.get('monto')  # Usar monto como costo si no hay otro
        moneda = params.get('moneda', 'usd')
        proveedor = params.get('actor', 'PROVEEDOR')
        
        if not codigo or not cantidad or not costo_unitario:
            return {
                "success": False,
                "message": "❌ Necesito codigo, cantidad y costo. Ejemplo: \"Entrada de HUEVOS, 100 unidades, 0.5 USD cada uno\""
            }
        
        resultado = InventarioService.registrar_entrada(
            codigo, cantidad, costo_unitario, moneda, proveedor
        )
        
        return {
            "success": True,
            "message": (
                f"📦 <b>Entrada Registrada!</b>\n\n"
                f"Codigo: {codigo}\n"
                f"Cantidad: +{cantidad} unidades\n"
                f"Supplier: {proveedor}\n"
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
        
        reporte = f"📦 <b>CONSIGNED STOCK: {vendedor}</b>\n\n"
        if stock_items:
            for item in stock_items:
                reporte += f"  • <b>{item['codigo']}</b>: {int(item['stock'])} unidades\n"
        else:
            reporte += "  <i>No tiene stock pendiente.</i>"
        
        return {"success": True, "message": reporte}
    
    @staticmethod
    async def _execute_exportar() -> Dict[str, Any]:
        """Ejecuta exportacion."""
        return {
            "success": True,
            "message": "💾 Para exportar, usa el comando /exportar que te enviara un archivo CSV con todos los movimientos."
        }
    
    @staticmethod
    async def _execute_container_create(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta creation de container."""
        nombre = params.get('nombre')
        
        if not nombre:
            return {
                "success": False,
                "message": "❌ Necesito el nombre del container. Ejemplo: \"Create container llamado ALMACEN1\" o \"Nuevo container DEPOSITO\""
            }
        
        try:
            resultado = ContainerService.create(nombre)
            return {
                "success": True,
                "message": (
                    f"✅ <b>Container created!</b>\n\n"
                    f"📦 Nombre: <code>{nombre}</code>\n"
                    f"🆔 ID: {resultado['id']}"
                )
            }
        except ValueError as e:
            if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
                return {
                    "success": False,
                    "message": f"⚠️ Ya existe un container con el nombre '{nombre}'. Usa otro nombre."
                }
            return {
                "success": False,
                "message": f"❌ Error: {e}"
            }
        except Exception as e:
            logger.error(f"Error creando container: {e}", exc_info=True)
            return {
                "success": False,
                "message": "❌ An error occurred al create el container. Try again."
            }
    
    @staticmethod
    async def _execute_container_listar() -> Dict[str, Any]:
        """Ejecuta listado de containeres."""
        containeres = ContainerService.listar()
        
        if not containeres:
            return {
                "success": True,
                "message": "📦 <b>Containeres</b>\n\nStill no hay containeres recordeds.\n\nPuedes create uno diciendo: \"Create container llamado [nombre]\""
            }
        
        respuesta = "📦 <b>Lista de Containeres</b>\n\n"
        for cont in containeres:
            respuesta += f"🆔 <b>ID {cont['id']}</b>: <code>{cont['nombre']}</code>\n"
        
        respuesta += f"\n<i>Total: {len(containeres)} container(es)</i>"
        
        return {"success": True, "message": respuesta}
    
    @staticmethod
    async def _execute_container_editar(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta edicion de container."""
        cont_id = params.get('id') or params.get('cont_id')
        nombre_actual = params.get('nombre_actual') or params.get('actor')
        nuevo_nombre = params.get('nuevo_nombre') or params.get('nombre')
        
        # Si no hay ID, intentar buscar por nombre
        if not cont_id and nombre_actual:
            containeres = ContainerService.listar()
            for cont in containeres:
                if cont['nombre'].lower() == nombre_actual.lower():
                    cont_id = cont['id']
                    break
        
        if not cont_id:
            return {
                "success": False,
                "message": "❌ Necesito el ID o nombre del container a editar. Ejemplo: \"Editar container 1 a ALMACEN2\" o \"Renombrar container DEPOSITO a BODEGA\""
            }
        
        if not nuevo_nombre:
            return {
                "success": False,
                "message": "❌ Necesito el nuevo nombre. Ejemplo: \"Editar container 1 a ALMACEN2\" o \"Renombrar container DEPOSITO a BODEGA\""
            }
        
        try:
            ContainerService.update(int(cont_id), nuevo_nombre)
            return {
                "success": True,
                "message": (
                    f"✅ <b>Container updated!</b>\n\n"
                    f"🆔 ID: {cont_id}\n"
                    f"📦 Nuevo nombre: <code>{nuevo_nombre}</code>"
                )
            }
        except ValueError as e:
            if "not found" in str(e).lower():
                return {
                    "success": False,
                    "message": f"❌ Not found un container con ID {cont_id}."
                }
            if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
                return {
                    "success": False,
                    "message": f"⚠️ Ya existe un container con el nombre '{nuevo_nombre}'. Usa otro nombre."
                }
            return {
                "success": False,
                "message": f"❌ Error: {e}"
            }
        except Exception as e:
            logger.error(f"Error editando container: {e}", exc_info=True)
            return {
                "success": False,
                "message": "❌ An error occurred al editar el container. Try again."
            }
    
    @staticmethod
    async def _execute_container_delete(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta deletion de container."""
        cont_id = params.get('id') or params.get('cont_id')
        nombre = params.get('nombre') or params.get('actor')
        
        # Si no hay ID, intentar buscar por nombre
        if not cont_id and nombre:
            containeres = ContainerService.listar()
            for cont in containeres:
                if cont['nombre'].lower() == nombre.lower():
                    cont_id = cont['id']
                    break
        
        if not cont_id:
            return {
                "success": False,
                "message": "❌ Necesito el ID o nombre del container a delete. Ejemplo: \"Delete container 1\" o \"Borrar container ALMACEN1\""
            }
        
        try:
            # Obtener nombre antes de delete para mostrar en el mensaje
            container = ContainerService.obtener_por_id(int(cont_id))
            nombre_deleted = container['nombre'] if container else f"ID {cont_id}"
            
            ContainerService.delete(int(cont_id))
            return {
                "success": True,
                "message": (
                    f"🗑️ <b>Container deleted!</b>\n\n"
                    f"📦 Container: <code>{nombre_deleted}</code>\n"
                    f"🆔 ID: {cont_id}"
                )
            }
        except ValueError as e:
            if "not found" in str(e).lower():
                return {
                    "success": False,
                    "message": f"❌ Not found un container con ID {cont_id}."
                }
            return {
                "success": False,
                "message": f"❌ Error: {e}"
            }
        except Exception as e:
            logger.error(f"Error eliminando container: {e}", exc_info=True)
            return {
                "success": False,
                "message": "❌ An error occurred al delete el container. Try again."
            }
    
    @staticmethod
    async def _execute_analisis_financiero(params: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta analisis financiero inteligente."""
        tipo = params.get("tipo", "general")
        return FinancialAdvisor.generar_analisis(tipo)

