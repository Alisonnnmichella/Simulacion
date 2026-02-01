from simulacion import HORIZONTE_VACIO, SimuladorMesaAyuda

def interarribo_dummy(_rng) -> float:
    return 1.0

def duracion_dummy(_tipo: str, _rng) -> float:
    return 1.0


def crear_simulador_dummy() -> SimuladorMesaAyuda:
    return SimuladorMesaAyuda(
        cantidad_operadores_it=1,
        cantidad_operadores_tecnico=1,
        cantidad_operadores_dev=1,
        muestrear_interarribo_min=interarribo_dummy,
        muestrear_duracion_servicio_min=duracion_dummy,
        seed=123,
        debug=False,
    )
def sim_crear_simulador_dummy(tec, sit,dev) :
    sim = crear_simulador_dummy()
    sim.TPSTEC = tec
    sim.TPSIT = sit   
    sim.TPSDEVS = dev
    return sim

def test_elegir_siguiente_salida():
    sim = sim_crear_simulador_dummy([100.0, 200.0, 50.0], [80.0, 120.0], [150.0, 90.0, 110.0])
    tiempo_minimo, categoria, indice = sim._elegir_siguiente_salida()
    assert categoria == 'TEC'
    assert tiempo_minimo == 50.0
    assert indice == 2
    
def test_elegir_siguiente_salida_devuelve_hv_y_menos_uno():
    sim = sim_crear_simulador_dummy([HORIZONTE_VACIO,HORIZONTE_VACIO, HORIZONTE_VACIO], [HORIZONTE_VACIO], [HORIZONTE_VACIO,HORIZONTE_VACIO, HORIZONTE_VACIO])
    tiempo_minimo, categoria, indice = sim._elegir_siguiente_salida()
    assert categoria == ''
    assert tiempo_minimo == HORIZONTE_VACIO
    assert indice == -1

def test_elegir_siguiente_salida_con_highvalue():
    sim = sim_crear_simulador_dummy([HORIZONTE_VACIO,50.0, HORIZONTE_VACIO], [HORIZONTE_VACIO], [HORIZONTE_VACIO,HORIZONTE_VACIO, 3.0])
    tiempo_minimo, categoria, indice = sim._elegir_siguiente_salida()
    assert categoria == "DEV"
    assert tiempo_minimo == 3.0
    assert indice == 2    