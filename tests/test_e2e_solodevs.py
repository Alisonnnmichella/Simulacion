# test_simulacion_e2e.py
from simulacion import HORIZONTE_VACIO, SimuladorMesaAyuda, MINUTOS_POR_DIA, INICIO_TURNO_MIN, FIN_TURNO_MIN

def interarribo_dummy(_rng) -> float:
    return 1.0

def duracion_dummy(_tipo: str, _rng) -> float:
    return 1.0

def crear_simulador_dummy(cantidad_it, cantidad_tec, cantidad_dev) -> SimuladorMesaAyuda:
    return SimuladorMesaAyuda(
        cantidad_operadores_it=cantidad_it,
        cantidad_operadores_tecnico=cantidad_tec,
        cantidad_operadores_dev=cantidad_dev,
        muestrear_interarribo_min=interarribo_dummy,
        muestrear_duracion_servicio_min=duracion_dummy,
        seed=123,
        debug=False,
    )

def test_e2e_3_arribos_con_agenda_dev_y_salidas(monkeypatch):
    sim = crear_simulador_dummy(cantidad_it=1, cantidad_tec=1, cantidad_dev=2)

    # 1) Forzamos IT y TEC "ocupados" todo el día (para que IT/TEC caigan en DEV)
    sim.TPSIT = [10**9]
    sim.TPSTEC = [10**9]
    sim.TPSDEVS = [HORIZONTE_VACIO, HORIZONTE_VACIO]

    sim.AGIT = [None]
    sim.AGTEC = [None]
    sim.AGDEVS = [None, None]

    # 2) Secuencias determinísticas:
    # Arribos en 09:01, 09:02, 09:03 (desde 09:00)
    interarribos = iter([1.0, 1.0, 1.0, 999999.0])
    tipos = iter(["IT", "TEC", "DEV"])

    # Duraciones por arribo (en el orden de arribos):
    # IT (por DEV0) dura 10 min -> termina 09:11
    # TEC (por DEV1) dura 10 min -> termina 09:12
    # DEV llega 09:03 y se agenda; empieza 09:11 y dura hasta 18:00:
    # 18:00 = 1080, 09:11 = 540+11 = 551 => 1080-551 = 529 min
    duraciones = iter([10.0, 10.0, 529.0])

    monkeypatch.setattr(sim, "_obtener_siguiente_interarribo_minutos", lambda: next(interarribos))
    monkeypatch.setattr(sim, "_sortear_tipo_servicio", lambda: next(tipos))
    monkeypatch.setattr(sim, "_obtener_duracion_servicio_minutos", lambda _tipo: next(duraciones))

    # 3) Instrumentación para “ver” arribos/salidas sin depender de prints
    agendas = []
    inicios = []
    fines = []

    orig_agendar = sim._agendar_trabajo
    orig_iniciar = sim._iniciar_servicio
    orig_salida = sim._procesar_salida

    def agendar_wrap(tipo_servicio, indice_operador, trabajo):
        agendas.append((tipo_servicio, indice_operador, trabajo.tiempo_arribo_minutos))
        return orig_agendar(tipo_servicio, indice_operador, trabajo)

    def iniciar_wrap(t_actual, trabajo, idx):
        # Pool real: si el trabajo lo toma DEV (o es DEV), el pool es DEV
        pool = "DEV" if (trabajo.tomadoPorDev or trabajo.tipo_servicio == "DEV") else trabajo.tipo_servicio
        inicios.append((trabajo.tipo_servicio, pool, idx, t_actual))
        return orig_iniciar(t_actual, trabajo, idx)

    def salida_wrap(t_salida, pool_tipo, idx):
        # "pool_tipo" es IT/TEC/DEV según el TPS que venció.
        # Si pool es DEV, el tipo atendido real está en TIPO_EN_SERVICIO_DEV[idx]
        tipo_atendido = pool_tipo
        if pool_tipo == "DEV":
            tipo_atendido = sim.TIPO_EN_SERVICIO_DEV[idx] or "DEV"
        fines.append((pool_tipo, tipo_atendido, idx, t_salida))
        return orig_salida(t_salida, pool_tipo, idx)

    monkeypatch.setattr(sim, "_agendar_trabajo", agendar_wrap)
    monkeypatch.setattr(sim, "_iniciar_servicio", iniciar_wrap)
    monkeypatch.setattr(sim, "_procesar_salida", salida_wrap)

    # 4) Ejecutamos 1 día (termina en 18:00) con salidas reales
    res = sim.correr(dias=1)

    # -----------------
    # Aserciones clave
    # -----------------

    # A) Se agenda exactamente 1 trabajo (el DEV del 3er arribo) en algún DEV
    assert len(agendas) == 1
    assert agendas[0][0] == "DEV"         # tipo del trabajo agendado
    assert agendas[0][1] == 0             # lo agenda en DEV0 (termina antes que DEV1)

    # B) Arrancan 3 servicios en total: IT->DEV, TEC->DEV, y luego DEV (desde la agenda)
    assert [x[0] for x in inicios] == ["IT", "TEC", "DEV"]
    assert [x[1] for x in inicios] == ["DEV", "DEV", "DEV"]

    # C) Terminan 3 servicios y se cuentan por tipo atendido real
    # Dev0 termina IT a las 09:11 (551), Dev1 termina TEC a las 09:12 (552),
    # Dev0 termina DEV a las 18:00 (1080)
    assert fines[0][0] == "DEV" and fines[0][1] == "IT"
    assert fines[1][0] == "DEV" and fines[1][1] == "TEC"
    assert fines[2][0] == "DEV" and fines[2][1] == "DEV"

    assert fines[0][3] == INICIO_TURNO_MIN + 11   # 09:11 = 551
    assert fines[1][3] == INICIO_TURNO_MIN + 12   # 09:12 = 552
    assert fines[2][3] == FIN_TURNO_MIN           # 18:00 = 1080

    # D) Métricas finales: atendidos por tipo
    assert res.atendidos_por_tipo["IT"] == 1
    assert res.atendidos_por_tipo["TEC"] == 1
    assert res.atendidos_por_tipo["DEV"] == 1

    # E) No se pierde nada
    assert res.perdidos_por_tipo == {"IT": 0, "TEC": 0, "DEV": 0}
