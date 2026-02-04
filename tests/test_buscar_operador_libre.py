from simulacion import HORIZONTE_VACIO, SimuladorMesaAyuda, Trabajo
import random

def interarribo_dummy(_rng) -> float:
    return 1.0

def duracion_dummy(_tipo: str, _rng) -> float:
    return 1.0

def crear_simulador_dummy(cantidad_operadores_it,cantidad_operadores_tecnico,cantidad_operadores_dev) -> SimuladorMesaAyuda:
    return SimuladorMesaAyuda(
        cantidad_operadores_it=cantidad_operadores_it,
        cantidad_operadores_tecnico=cantidad_operadores_tecnico,
        cantidad_operadores_dev=cantidad_operadores_dev,
        muestrear_interarribo_min=interarribo_dummy,
        muestrear_duracion_servicio_min=duracion_dummy,
        seed=123,
        debug=False,
    )

def sim_crear_simulador_dummy(sit, tec, dev):
    sim = crear_simulador_dummy(len(sit), len(tec), len(dev))
    sim.TPSIT = sit
    sim.TPSTEC = tec
    sim.TPSDEVS = dev
    return sim

def completar_lista_valores_random(lista, cantidad):
    lista = [random.randint(1, 500) for _ in range(cantidad)]


def test_buscar_operador_libre():
    sim = sim_crear_simulador_dummy(
        sit=[100.0, HORIZONTE_VACIO],                 # IT -> libre en idx 1
        tec=[HORIZONTE_VACIO, 50.0],                  # TEC -> libre en idx 0
        dev=[150.0, HORIZONTE_VACIO, 110.0],          # DEV -> libre en idx 1
    )
    trabajo :Trabajo = Trabajo(tiempo_arribo_minutos=0.0, tipo_servicio='IT', duracion_servicio_minutos=10.0) 
    indice_it = sim._buscar_operador_libre(trabajo)
    trabajo.tipo_servicio = 'TEC'
    indice_tec = sim._buscar_operador_libre(trabajo)
    trabajo.tipo_servicio = 'DEV'
    indice_dev = sim._buscar_operador_libre(trabajo)
    assert indice_it == 1
    assert indice_tec == 0
    assert indice_dev == 1

def test_buscar_operador_libre_estado_ocupado_y_libres():
    sim = sim_crear_simulador_dummy(
        sit=[100.0, 50],                 # IT -> libre en idx 1
        tec=[20.0, 50.0],                  # TEC -> libre en idx 0
        dev=[150.0, HORIZONTE_VACIO],          # DEV -> libre en idx 1
    )
    trabajo :Trabajo = Trabajo(tiempo_arribo_minutos=0.0, tipo_servicio='IT', duracion_servicio_minutos=10.0)
    indice_it = sim._buscar_operador_libre(trabajo)
    trabajo.tipo_servicio = 'TEC'
    indice_tec = sim._buscar_operador_libre(trabajo)
    trabajo.tipo_servicio = 'DEV'
    indice_dev = sim._buscar_operador_libre(trabajo)
    assert indice_it == 1 # tomado por dev 
    assert indice_tec == 1 # tomado por dev
    assert indice_dev == 1   

def test_buscar_operador_libre_estado_agendados():
    sim = sim_crear_simulador_dummy(
        sit=[HORIZONTE_VACIO, HORIZONTE_VACIO],       # IT -> libre en idx 1
        tec=[HORIZONTE_VACIO, HORIZONTE_VACIO],       # TEC -> libre en idx 0
        dev=[150.0, HORIZONTE_VACIO, 110.0],          # DEV -> libre en idx 1
    )
    trabajo :Trabajo = Trabajo(tiempo_arribo_minutos=0.0, tipo_servicio='IT', duracion_servicio_minutos=10.0)
    sim.AGDEVS = [1]*sim.cantidad_operadores_dev  # todos agendados
    sim.AGIT = [1]*sim.cantidad_operadores_it  # todos agendados
    sim.AGTEC = [1]*sim.cantidad_operadores_tecnico  # todos agendados
    indice_it = sim._buscar_operador_libre(trabajo)
    trabajo.tipo_servicio = 'TEC'
    indice_tec = sim._buscar_operador_libre(trabajo)
    trabajo.tipo_servicio = 'DEV'
    indice_dev = sim._buscar_operador_libre(trabajo)
    assert indice_it == -1
    assert indice_tec == -1
    assert indice_dev == -1   
