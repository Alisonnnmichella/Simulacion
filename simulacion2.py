from dataclasses import dataclass
from typing import Callable, List, Tuple

from simulacion import formatear_tiempo

HORIZONTE_VACIO = float('inf')
HORA_INICIO_LABORAL = 9  # 9 AM
HORA_LIMITE_PARA_ACEPTAR_REQUEST= 17  # 5 PM
HORA_FINAL_DE_TRABAJO= 17  # 5 PM

import random
import math



@dataclass
class Trabajo:
    tiempo_arribo_minutos: float
    tipo_servicio: str                 # "IT" | "APP" | "DEV"
    duracion_servicio_minutos: float       # sorteada al ARRIBO o PENDIENTE
    tomadoPorDev: bool = False          # si fue tomado por DEV


def muestrear_interarribo_placeholder(rng: random.Random) -> float:
    """
    Placeholder de interarribo.
    Exponencial con media 10 minutos (usando transformada inversa).
    """
    media = 10.0
    u = rng.random()
    return -media * math.log(u)


def muestrear_interarribo_IT(rng: random.Random) -> float:
    muestrear_interarribo_placeholder(rng)

def muestrear_interarribo_APP(rng: random.Random) -> float:
    muestrear_interarribo_placeholder(rng)

def muestrear_interarribo_DEV(rng: random.Random) -> float:
    muestrear_interarribo_placeholder(rng)


def muestrear_duracion_servicio_IT(tipo: str, rng: random.Random) -> float:
    """
    Placeholder de duración de servicio.
    Uniforme entre 5 y 15 minutos.
    """
    return rng.uniform(5.0, 15.0)


def muestrear_duracion_servicio_APP(tipo: str, rng: random.Random) -> float:
    """
    Placeholder de duración de servicio.
    Uniforme entre 5 y 15 minutos.
    """
    return rng.uniform(5.0, 15.0)

def muestrear_duracion_servicio_DEV(tipo: str, rng: random.Random) -> float:
    """
    Placeholder de duración de servicio.
    Uniforme entre 5 y 15 minutos.
    """
    return rng.uniform(300.0, 8000.0)

class Simulacion:
    def __init__(
        self,
        cantidad_operadores_it: int,
        cantidad_operadores_app: int,
        cantidad_operadores_dev: int,
        muestrear_interarribo_minutos_it: Callable[[random.Random], float],
        muestrear_interarribo_minutos_app: Callable[[random.Random], float],
        muestrear_interarribo_minutos_dev: Callable[[random.Random], float],
        muestrear_duracion_servicio_it: Callable[[str, random.Random], float],
        muestrear_duracion_servicio_app: Callable[[str, random.Random], float],
        muestrear_duracion_servicio_dev: Callable[[str, random.Random], float],
        seed: int = 1,
        debug: bool = False,
        tiempoFinalSimulacion: int = 10,
        tiempoActual: int = 0
        ):
        self.rng = random.Random(seed)
        self.debug = debug
        self.tiempoFinalSimulacion = tiempoFinalSimulacion
        self.tiempoActual = tiempoActual
        self.cantidad_operadores_it = cantidad_operadores_it
        self.cantidad_operadores_app = cantidad_operadores_app
        self.cantidad_operadores_dev = cantidad_operadores_dev
        self.TPSIT: List[float] =  [HORIZONTE_VACIO] * cantidad_operadores_it
        self.TPSAPP: List[float] = [HORIZONTE_VACIO] *cantidad_operadores_app
        self.TPSDEV: List[float] = [HORIZONTE_VACIO] * cantidad_operadores_dev
        self.muestrear_interarribo_minutos_it = muestrear_interarribo_minutos_it
        self.muestrear_interarribo_minutos_dev = muestrear_interarribo_minutos_dev
        self.muestrear_interarribo_minutos_app = muestrear_interarribo_minutos_app
        self.muestrear_duracion_servicio_it = muestrear_duracion_servicio_it
        self.muestrear_duracion_servicio_app = muestrear_duracion_servicio_app  
        self.muestrear_duracion_servicio_dev = muestrear_duracion_servicio_dev
        self.TPLL_por_tipo = {
            "IT": HORIZONTE_VACIO,
            "APP": HORIZONTE_VACIO,
            "DEV": HORIZONTE_VACIO
        }
        self.AGDEVS: List[Trabajo | None] = [None] * cantidad_operadores_dev
        self.AGIT: List[Trabajo | None] = [None] * cantidad_operadores_it
        self.AGAPP: List[Trabajo | None] = [None] * cantidad_operadores_app
        self.DEVATENCIONIT = 0
        self.DEVATENCIONAPP = 0
        self.personasAtendidasPorTipo = {
            "IT": 0,
            "APP": 0,
            "DEV": 0
        }
        self.maximoNumeroDePersonasAtendidasPorDia=0
        


    def _elegir_siguiente_salida(self) -> Tuple[float, str, int]:
        min_it = min(self.TPSIT) if self.cantidad_operadores_it > 0 else HORIZONTE_VACIO
        min_app = min(self.TPSAPP) if self.cantidad_operadores_app > 0 else HORIZONTE_VACIO
        min_dev = min(self.TPSDEV) if self.cantidad_operadores_dev > 0 else HORIZONTE_VACIO

        if min_it <= min_app and min_it <= min_dev:
            return min_it, "IT", self.TPSIT.index(min_it)
        elif min_app <= min_it and min_app <= min_dev:
            return min_app, "APP", self.TPSAPP.index(min_app)
        else:
            return min_dev, "DEV", self.TPSDEV.index(min_dev)


    def _elegir_siguiente_entrada(self) -> Tuple[float, str, int]:
        min_it = min(self.TPLLIT) if self.cantidad_operadores_it > 0 else HORIZONTE_VACIO
        min_app = min(self.TPLLAPP) if self.cantidad_operadores_app > 0 else HORIZONTE_VACIO
        min_dev = min(self.TPLLDEV) if self.cantidad_operadores_dev > 0 else HORIZONTE_VACIO

        if min_it <= min_app and min_it <= min_dev:
            return min_it, "IT", self.TPLLIT.index(min_it)
        elif min_app <= min_it and min_app <= min_dev:
            return min_app, "APP", self.TPLLAPP.index(min_app)
        else:
            return min_dev, "DEV", self.TPLLDEV.index(min_dev)

    def _minutos_del_dia(tiempoActual:float) -> float:
        minutos_dia = tiempoActual % 1440  # 1440 minutos en un día (24 horas * 60 minutos)
        return minutos_dia

    def _fin_del_dia_en_minutos_absolutos(self , tiempoActual:float) -> float:
        dia = tiempoActual // 1440
        finalDelDiaEnMinutosAbsolutos = dia*1440+HORA_FINAL_DE_TRABAJO*60
        return finalDelDiaEnMinutosAbsolutos
    
    # necesito que si pasa de un dia  me devuelva el tiempo de fin de la tarea respecto a lo que lleve dentro del horario laboral, seria tiempo actual + tiempo total pero dentro de horario laboral algo que quizas dure 25 horas en lugar de ser un dia y una hora seria 
    # del resto del dia tomo lo que resta se lo resto a la duracion de la tarea y despues de lo que resta de la tarea lo divido en la cantidad de horas laborales para saber cuantos dias lleva
    # y con el modulo se cuantos minutos lleva del ultimo dia y se lo sumo al tiempo actual
    def determinarTiempoDeFinDeTarea(self,tiempoActual:float, tiempoDeAtencion:float) -> float:
        finDelDiaEnMinutosAbsolutos = self._fin_del_dia_en_minutos_absolutos(tiempoActual)       
        if(tiempoActual+tiempoDeAtencion <= finDelDiaEnMinutosAbsolutos):
            return tiempoActual+tiempoDeAtencion
        restoDelDia = finDelDiaEnMinutosAbsolutos - tiempoActual
        restoDeLaTarea = tiempoDeAtencion - restoDelDia
        minutosLaboralesPorDia = (HORA_FINAL_DE_TRABAJO-HORA_INICIO_LABORAL)*60
        diasRestantes = restoDeLaTarea // minutosLaboralesPorDia
        minutosRestantesDelUltimoDia = restoDeLaTarea % minutosLaboralesPorDia
        diaActual = tiempoActual // 1440
        if(minutosRestantesDelUltimoDia == 0):
            return (diaActual+diasRestantes)*1440
        return (diaActual+diasRestantes)*1440 + HORA_INICIO_LABORAL*60+minutosRestantesDelUltimoDia
    
    def _obtener_interarribo_por_tipo(self, tipo:str) -> float:
        if tipo == "IT":
            return self.muestrear_interarribo_minutos_it(self.rng)
        elif tipo == "APP":
            return self.muestrear_interarribo_minutos_app(self.rng)
        elif tipo == "DEV":
            return self.muestrear_interarribo_minutos_dev(self.rng)
        else:
            raise ValueError(f"Tipo desconocido: {tipo}")
        
    def _obtener_duracion_servicio_por_tipo(self, tipo:str) -> float:
        if tipo == "IT":
            return self.muestrear_duracion_servicio_it(tipo, self.rng)
        elif tipo == "APP":
            return self.muestrear_duracion_servicio_app(tipo, self.rng)
        elif tipo == "DEV":
            return self.muestrear_duracion_servicio_dev(tipo, self.rng)
        else:
            raise ValueError(f"Tipo desconocido: {tipo}")

    def inicioVariablesSimulacion(self) -> None:
        tiempoActual = HORA_INICIO_LABORAL*60  # Convertir días a minutos        
        self.TPLL_por_tipo["IT"] = tiempoActual + self.muestrear_interarribo_minutos_it(self.rng)
        self.TPLL_por_tipo["APP"] = tiempoActual + self.muestrear_interarribo_minutos_app(self.rng)
        self.TPLL_por_tipo["DEV"] = tiempoActual + self.muestrear_interarribo_minutos_dev(self.rng)
        self.TPSIT =  [HORIZONTE_VACIO] * self.cantidad_operadores_it
        self.TPSAPP = [HORIZONTE_VACIO] * self.cantidad_operadores_app
        self.TPSDEV = [HORIZONTE_VACIO] * self.cantidad_operadores_dev
    
    def _buscar_operador_libre(self, trabajo: Trabajo) -> int:
        """
        Libre SOLO si:
        - TPS == HV (no está atendiendo)
        - y NO tiene trabajo asignado (AG == None)
        """
        tipo_servicio = trabajo.tipo_servicio
        if tipo_servicio == "IT":
            for i in range(self.cantidad_operadores_it):
                if self.TPSIT[i] == HORIZONTE_VACIO and self.AGIT[i] is None:
                    return i
            for i in range(self.cantidad_operadores_dev):
                if self.TPSDEV[i] == HORIZONTE_VACIO and self.AGDEVS[i] is None:
                    self.DEVATENCIONIT += 1
                    trabajo.tomadoPorDev = True
                    return i
            return -1

        if tipo_servicio == "APP":
            for i in range(self.cantidad_operadores_app):
                if self.TPSAPP[i] == HORIZONTE_VACIO and self.AGAPP[i] is None:
                    return i
            for i in range(self.cantidad_operadores_dev):
                if self.TPSDEV[i] == HORIZONTE_VACIO and self.AGDEVS[i] is None:
                    self.DEVATENCIONAPP += 1
                    trabajo.tomadoPorDev = True
                    return i
            return -1
        
        for i in range(self.cantidad_operadores_dev):
            if self.TPSDEV[i] == HORIZONTE_VACIO and self.AGDEVS[i] is None:
                return i
        return -1

    
    def _procesar_arribo(self, tiempo_arribo_minutos: float, tipo: str, indice_operador_entrada: int) -> None:
        """
        ARRIBO:
        - sortea tipo
        - sortea duración de servicio del trabajo
        - intenta atender / agendar / perder
        """

        indice_libre = self._buscar_operador_libre(tipo)
        if indice_libre != -1:
            self.personasAtendidasPorTipo[tipo] += 1
            self._iniciar_servicio(tiempo_arribo_minutos, trabajo, indice_libre)
            return

        indice_para_agendar = self._buscar_operador_para_agendar(tipo, tiempo_arribo_minutos)
        if indice_para_agendar != -1:
            self._agendar_trabajo(tipo, indice_para_agendar, trabajo)
            return

        self.perdidos_por_tipo[tipo] += 1
        if self.debug:
            print(f"[PERDIDO] {tipo} arribo={formatear_tiempo(tiempo_arribo_minutos)}")

    def _iniciar_servicio(self, tiempo_actual_minutos: float, trabajo: Trabajo, indice_operador: int):
        """
        Arranca servicio:
        - normaliza inicio a horario laboral
        - acumula espera
        - programa el fin del servicio en TPS = inicio + duracion (en tiempo laboral)
        """
        duracionDeAtencion = self._obtener_duracion_servicio_por_tipo(trabajo.tipo_servicio)
        determinarTiempoDeFinDeTarea = self.determinarTiempoDeFinDeTarea(tiempo_actual_minutos, duracionDeAtencion)

        if trabajo.tipo_servicio == "IT" and trabajo.tomadoPorDev == False:
            self.TPSIT[indice_operador] = fin_servicio
        elif trabajo.tipo_servicio == "TEC" and trabajo.tomadoPorDev == False:
            self.TPSTEC[indice_operador] = fin_servicio
        else:
            self.TPSDEVS[indice_operador] = fin_servicio
            self.TIPO_EN_SERVICIO_DEV[indice_operador] = trabajo.tipo_servicio
        if self.debug:
            print(
                f"[INICIO] {trabajo.tipo_servicio} op={indice_operador} "
                f"arribo={formatear_tiempo(trabajo.tiempo_arribo_minutos)} "
                f"inicio={formatear_tiempo(inicio_servicio)} "
                f"fin={formatear_tiempo(fin_servicio)}"
            )



    def _iniciar_simulacion(self):
        self.inicioVariablesSimulacion()
        while(self.tiempoActual < self.tiempoFinalSimulacion):
            min_trabajo_programado, tipo_salida, indice_operador = self._elegir_siguiente_salida()
            min_arribo, tipo_arribo, indice_operador_entrada = self._elegir_siguiente_entrada()
            if min_arribo <= min_trabajo_programado:
                self._procesar_arribo(min_arribo, tipo_arribo,indice_operador_entrada)

            else:
                self._procesar_salida(min_trabajo_programado, tipo_salida, indice_operador)

