"""
SAKURA V4 - MÁQUINA DE ESTADOS
Basado en la secuencia obligatoria de apertura de ruta
"""

from datetime import datetime, timedelta
import json

class RouteStateMachine:
    """Máquina de estados para el seguimiento de la ruta JP-PTY"""
    
    def __init__(self):
        # Definir la secuencia obligatoria
        self.states = [
            {
                'id': 'STATE_1',
                'name': 'Tratado Bilateral (RoD)',
                'required': True,
                'target_days_after_previous': 0,
                'description': 'Acuerdo bilateral que autoriza la ruta',
                'expected_actor': 'AAC/MLIT',
                'min_evidence_level': 8
            },
            {
                'id': 'STATE_2',
                'name': 'Solicitud de Slot en PTY',
                'required': True,
                'target_days_after_previous': 90,
                'description': 'Solicitud formal de slots en el aeropuerto de Tocumen',
                'expected_actor': 'ANA',
                'min_evidence_level': 7
            },
            {
                'id': 'STATE_3',
                'name': 'Asignación de Slot en PTY',
                'required': True,
                'target_days_after_previous': 60,
                'description': 'Asignación de slots en el aeropuerto de Tocumen',
                'expected_actor': 'AAC/Tocumen',
                'min_evidence_level': 8
            },
            {
                'id': 'STATE_4',
                'name': 'Publicación en OAG',
                'required': True,
                'target_days_after_previous': 30,
                'description': 'Carga de horarios en OAG (Official Airline Guide)',
                'expected_actor': 'ANA',
                'min_evidence_level': 7
            },
            {
                'id': 'STATE_5',
                'name': 'Carga en GDS',
                'required': True,
                'target_days_after_previous': 60,
                'description': 'Carga en sistemas GDS (Amadeus, Sabre)',
                'expected_actor': 'ANA',
                'min_evidence_level': 8
            },
            {
                'id': 'STATE_6',
                'name': 'Primer Vuelo Operativo',
                'required': True,
                'target_days_after_previous': 90,
                'description': 'Primer vuelo operativo de la ruta',
                'expected_actor': 'ANA',
                'min_evidence_level': 10
            }
        ]
        
        # Estado actual
        self.current_state = 0
        self.start_date = None
        
    def set_start_date(self, date_str):
        """Establecer la fecha del primer hito (RoD)"""
        self.start_date = datetime.strptime(date_str, '%Y-%m-%d')
        
    def get_expected_date(self, state_index):
        """Obtener la fecha esperada para un estado"""
        if self.start_date is None:
            return None
        
        # Sumar los días de todos los estados anteriores
        total_days = 0
        for i in range(state_index + 1):
            total_days += self.states[i]['target_days_after_previous']
        
        return self.start_date + timedelta(days=total_days)
    
    def check_tripwires(self, current_date_str, completed_states):
        """
        Verifica si alguna tripwire ha sido activada
        completed_states: lista de IDs de estados ya completados
        """
        current_date = datetime.strptime(current_date_str, '%Y-%m-%d')
        alerts = []
        
        for i, state in enumerate(self.states):
            expected_date = self.get_expected_date(i)
            if expected_date is None:
                continue
            
            # Si el estado ya está completado, no hacer nada
            if state['id'] in completed_states:
                continue
            
            # Calcular días de retraso
            days_overdue = (current_date - expected_date).days
            
            # Si la fecha esperada ya pasó y el estado no está completado
            if days_overdue > 0:
                alerts.append({
                    'state_id': state['id'],
                    'state_name': state['name'],
                    'expected_date': expected_date.strftime('%Y-%m-%d'),
                    'days_overdue': days_overdue,
                    'severity': 'critical' if days_overdue > 30 else 'high' if days_overdue > 15 else 'medium',
                    'message': f"⚠️ TRIPWIRE: {state['name']} no se completó en la fecha esperada ({days_overdue} días de retraso)"
                })
        
        return alerts
    
    def get_progress(self, completed_states):
        """Calcular el progreso del proyecto (0-100)"""
        required_states = [s for s in self.states if s['required']]
        completed_count = sum(1 for s in required_states if s['id'] in completed_states)
        total_count = len(required_states)
        
        return (completed_count / total_count) * 100

# ============================================================
# EJEMPLO DE USO
# ============================================================

if __name__ == '__main__':
    # Crear la máquina de estados
    machine = RouteStateMachine()
    
    # Establecer la fecha del RoD (hito 1)
    machine.set_start_date('2026-07-04')
    
    # Estados que ya están completados
    completed = ['STATE_1']  # RoD ya ocurrió
    
    # Verificar tripwires hoy
    alerts = machine.check_tripwires('2026-10-01', completed)
    
    print("🐋 SAKURA V4 - MÁQUINA DE ESTADOS")
    print("=" * 50)
    print(f"📅 Fecha del RoD: 2026-07-04")
    print(f"📊 Progreso: {machine.get_progress(completed)}%")
    print("\n📋 ESTADOS ESPERADOS:")
    
    for i, state in enumerate(machine.states):
        expected_date = machine.get_expected_date(i)
        status = "✅ COMPLETADO" if state['id'] in completed else "⏳ PENDIENTE"
        print(f"   {i+1}. {state['name']}")
        print(f"      Fecha esperada: {expected_date.strftime('%Y-%m-%d') if expected_date else 'N/A'}")
        print(f"      Estado: {status}")
    
    if alerts:
        print("\n🚨 TRIPWIRES ACTIVADAS:")
        for alert in alerts:
            print(f"   {alert['message']}")
    else:
        print("\n✅ Todas las tripwires están en verde")
