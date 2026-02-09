# test_simulacion_multidia.py
from simulacion import (
    SimuladorMesaAyuda,
    HORIZONTE_VACIO,
    INICIO_TURNO_MIN,
    FIN_TURNO_MIN,
)

def interarribo_dummy(_rng) -> float:
    return 1.0

def duracion_dummy(_tipo: str, _rng) -> float:
    return 1.0

def crear_simulador_dummy(cantidad_it, cantidad_tec, cantidad_dev) -> SimuladorMesaAyuda:
    return SimuladorMesaAyuda(
        cantidad_operadores_it=cantidad_it,
        cantidad_operadores_tecnico=cantidad_tec,
        cantidad_operadores_dev=cantidad_dev,
        muestrear_interarribo_minutos_it=interarribo_dummy,
        muestrear_duracion_servicio_min=duracion_dummy,
        seed=123,
        debug=False,
    )

def test_e2e_multidia_cruce_noche_arribo_antes_de_salida_y_agenda(monkeypatch):
    """
    Escenario (2 días):
    - 1 operador IT, 0 TEC, 0 DEV
    - Arribos (en tiempo laboral):
      1) Día 0 17:59 (09:00 + 539)
      2) 2 min después => cruza cierre => Día 1 09:01
      3) 10 min después => Día 1 09:11
    - Duraciones:
      1) 5 min => termina Día 1 09:04 (cruce noche)
      2) 1 min => se agenda (arriba 09:01, empieza 09:04, termina 09:05)
      3) 529 min => empieza 09:11 y termina exacto Día 1 18:00 (fin simulación)
    """

    sim = crear_simulador_dummy(cantidad_it=1, cantidad_tec=0, cantidad_dev=0)

    # Estado inicial: IT libre, sin agenda
    sim.TPSIT = [HORIZONTE_VACIO]
    sim.AGIT = [None]

    # --- Secuencias determinísticas ---
    # Interarribos (en minutos laborales)
    interarribos = iter([539.0, 2.0, 10.0, 999999.0])  # el último no debería importar
    tipos = iter(["IT", "IT", "IT"])
    duraciones = iter([5.0, 1.0, 529.0])

    monkeypatch.setattr(sim, "_obtener_siguiente_interarribo_minutos", lambda: next(interarribos))
    monkeypatch.setattr(sim, "_sortear_tipo_servicio", lambda: next(tipos))
    monkeypatch.setattr(sim, "_obtener_duracion_servicio_minutos", lambda _tipo: next(duraciones))

    # --- Instrumentación para ver el orden real de eventos ---
    eventos = []   # ("A" o "S", tiempo)
    agendas = []   # (tipo, op, tiempo_arribo)
    inicios = []   # (tiempo_inicio, duracion)

    orig_arribo = sim._procesar_arribo
    orig_salida = sim._procesar_salida
    orig_agendar = sim._agendar_trabajo
    orig_iniciar = sim._iniciar_servicio

    def arribo_wrap(t):
        eventos.append(("A", t))
        return orig_arribo(t)

    def salida_wrap(t, tipo, idx):
        eventos.append(("S", t))
        return orig_salida(t, tipo, idx)

    def agendar_wrap(tipo, idx, trabajo):
        agendas.append((tipo, idx, trabajo.tiempo_arribo_minutos))
        return orig_agendar(tipo, idx, trabajo)

    def iniciar_wrap(t_actual, trabajo, idx):
        inicios.append((t_actual, trabajo.duracion_servicio_minutos))
        return orig_iniciar(t_actual, trabajo, idx)

    monkeypatch.setattr(sim, "_procesar_arribo", arribo_wrap)
    monkeypatch.setattr(sim, "_procesar_salida", salida_wrap)
    monkeypatch.setattr(sim, "_agendar_trabajo", agendar_wrap)
    monkeypatch.setattr(sim, "_iniciar_servicio", iniciar_wrap)

    # --- Ejecutar 2 días ---
    res = sim.correr(dias=2)

    # -----------------------
    # Aserciones de TIEMPO
    # -----------------------

    # Tiempos esperados (minutos absolutos)
    t_1759_d0 = INICIO_TURNO_MIN + 539          # 1079
    t_0901_d1 = (1 * 1440) + INICIO_TURNO_MIN + 1   # 1981
    t_0904_d1 = (1 * 1440) + INICIO_TURNO_MIN + 4   # 1984
    t_0905_d1 = (1 * 1440) + INICIO_TURNO_MIN + 5   # 1985
    t_0911_d1 = (1 * 1440) + INICIO_TURNO_MIN + 11  # 1991
    t_1800_d1 = (1 * 1440) + FIN_TURNO_MIN          # 2520

    # 1) Orden de eventos clave: el arribo 09:01 ocurre antes que la salida 09:04
    # Esto valida que la comparación TPLL >= minTPS está bien.
    assert ("A", t_0901_d1) in eventos
    assert ("S", t_0904_d1) in eventos
    assert eventos.index(("A", t_0901_d1)) < eventos.index(("S", t_0904_d1))

    # 2) Validar cruce de noche: primer servicio termina Día 1 09:04
    assert ("S", t_0904_d1) in eventos

    # 3) Validar que el arribo 09:01 se AGENDÓ (porque el operador seguía ocupado hasta 09:04)
    assert len(agendas) == 1
    assert agendas[0] == ("IT", 0, t_0901_d1)

    # 4) Validar que se ejecutaron 3 servicios (3 inicios) y que el último termina en el fin del día 1 (18:00)
    assert len(inicios) == 3
    assert ("S", t_1800_d1) in eventos

    # -----------------------
    # Aserciones de MÉTRICAS
    # -----------------------

    # Se atendieron 3 IT, ninguno perdido
    assert res.atendidos_por_tipo["IT"] == 3
    assert res.perdidos_por_tipo["IT"] == 0

    # Espera promedio:
    # - trabajo1: llega 17:59, inicia 17:59 => 0
    # - trabajo2: llega 09:01, inicia 09:04 => 3
    # - trabajo3: llega 09:11, inicia 09:11 => 0
    # total espera = 3 / 3 = 1
    assert abs(res.espera_promedio_por_tipo_min["IT"] - 1.0) < 1e-9
