"""
SAKURA V4 - MOTOR ACH + BAYES
Análisis de Hipótesis en Competencia con actualización bayesiana
"""

import json
import math
from datetime import datetime

class ACHBayesEngine:
    """Motor de inteligencia basado en ACH + Bayes"""
    
    def __init__(self):
        # ============================================================
        # 4 HIPÓTESIS EN COMPETENCIA (ACH)
        # ============================================================
        self.hypotheses = {
            'H1': {
                'name': 'Lanzamiento antes de 2027 (mainline ANA)',
                'description': 'ANA lanza la ruta Tokio-Panamá como vuelo directo operado por ANA antes de finales de 2027',
                'prior': 0.20,  # Probabilidad inicial
                'posterior': 0.20,  # Probabilidad actualizada
                'evidence': [],  # Lista de evidencias a favor
                'against': [],   # Lista de evidencias en contra
                'status': 'active'
            },
            'H2': {
                'name': 'Lanzamiento después de 2027 (mainline ANA)',
                'description': 'ANA lanza la ruta Tokio-Panamá como vuelo directo operado por ANA, pero después de 2027',
                'prior': 0.30,
                'posterior': 0.30,
                'evidence': [],
                'against': [],
                'status': 'active'
            },
            'H3': {
                'name': 'RoD sin ejercer',
                'description': 'El Record of Discussions queda como marco jurídico sin que ANA ejerza los derechos de tráfico',
                'prior': 0.30,
                'posterior': 0.30,
                'evidence': [],
                'against': [],
                'status': 'active'
            },
            'H4': {
                'name': 'Codeshare en vez de mainline',
                'description': 'La ruta se materializa como codeshare/interline mejorado con Copa Airlines, sin vuelo directo de ANA',
                'prior': 0.20,
                'posterior': 0.20,
                'evidence': [],
                'against': [],
                'status': 'active'
            }
        }
        
        # ============================================================
        # EVIDENCIA Y PESOS
        # ============================================================
        self.evidence_registry = {}
        self.evidence_id_counter = 0
        
        # Pesos base para tipos de evidencia (likelihood)
        self.likelihood_weights = {
            'oficial': 0.85,      # Comunicado oficial
            'especializada': 0.65, # Prensa especializada
            'general': 0.45,      # Prensa general
            'rumor': 0.25         # Rumor/especulación
        }
    
    # ============================================================
    # REGISTRAR EVIDENCIA
    # ============================================================
    
    def add_evidence(self, title, source, category, supports, hypothesis_id, strength=1.0):
        """
        Registra una nueva evidencia
        
        Args:
            title: Título de la evidencia
            source: Fuente de la evidencia
            category: oficial, especializada, general, rumor
            supports: True = a favor, False = en contra
            hypothesis_id: H1, H2, H3, H4
            strength: 0.5-1.5 (multiplicador de peso)
        """
        self.evidence_id_counter += 1
        evidence_id = f"EVID-{self.evidence_id_counter:04d}"
        
        # Calcular peso base según categoría
        base_weight = self.likelihood_weights.get(category, 0.5)
        
        # Aplicar fuerza
        weight = base_weight * strength
        weight = min(1.0, max(0.1, weight))  # Limitar entre 0.1 y 1.0
        
        evidence = {
            'id': evidence_id,
            'title': title,
            'source': source,
            'category': category,
            'supports': supports,
            'hypothesis_id': hypothesis_id,
            'weight': weight,
            'timestamp': datetime.now().isoformat()
        }
        
        self.evidence_registry[evidence_id] = evidence
        
        # Actualizar la hipótesis correspondiente
        if supports:
            self.hypotheses[hypothesis_id]['evidence'].append(evidence_id)
        else:
            self.hypotheses[hypothesis_id]['against'].append(evidence_id)
        
        # Recalcular probabilidades
        self._update_bayesian()
        
        return evidence_id
    
    # ============================================================
    # MOTOR BAYESIANO
    # ============================================================
    
    def _update_bayesian(self):
        """
        Actualiza las probabilidades usando el Teorema de Bayes
        """
        # Calcular el peso total de evidencia para cada hipótesis
        evidence_scores = {}
        total_evidence_weight = 0
        
        for h_id, hypothesis in self.hypotheses.items():
            # Peso a favor
            for_evidence = hypothesis['evidence']
            for_weight = sum(self.evidence_registry[e]['weight'] for e in for_evidence if e in self.evidence_registry)
            
            # Peso en contra
            against_evidence = hypothesis['against']
            against_weight = sum(self.evidence_registry[e]['weight'] for e in against_evidence if e in self.evidence_registry)
            
            # Peso neto (a favor - en contra)
            net_weight = for_weight - against_weight
            evidence_scores[h_id] = net_weight
            total_evidence_weight += abs(net_weight)
        
        # Si no hay evidencia, mantener prior
        if total_evidence_weight == 0:
            for h_id in self.hypotheses:
                self.hypotheses[h_id]['posterior'] = self.hypotheses[h_id]['prior']
            return
        
        # Calcular nuevas probabilidades (normalizadas)
        total_score = 0
        for h_id, hypothesis in self.hypotheses.items():
            # Probabilidad = prior * (1 + evidencia_neta_normalizada)
            evidence_factor = 1 + (evidence_scores.get(h_id, 0) / (total_evidence_weight + 1))
            posterior = hypothesis['prior'] * evidence_factor
            self.hypotheses[h_id]['posterior'] = posterior
            total_score += posterior
        
        # Normalizar para que sumen 1
        if total_score > 0:
            for h_id in self.hypotheses:
                self.hypotheses[h_id]['posterior'] /= total_score
    
    # ============================================================
    # CONSULTAS
    # ============================================================
    
    def get_best_hypothesis(self):
        """Obtiene la hipótesis con mayor probabilidad"""
        best = None
        best_score = -1
        for h_id, h in self.hypotheses.items():
            if h['posterior'] > best_score and h['status'] == 'active':
                best_score = h['posterior']
                best = h_id
        return best, best_score
    
    def get_all_hypotheses(self):
        """Obtiene todas las hipótesis con sus probabilidades"""
        result = []
        for h_id, h in self.hypotheses.items():
            result.append({
                'id': h_id,
                'name': h['name'],
                'probability': h['posterior'],
                'status': h['status'],
                'evidence_count': len(h['evidence']),
                'against_count': len(h['against'])
            })
        # Ordenar por probabilidad descendente
        return sorted(result, key=lambda x: x['probability'], reverse=True)
    
    def get_evidence_summary(self, hypothesis_id):
        """Resumen de evidencia para una hipótesis"""
        h = self.hypotheses.get(hypothesis_id)
        if not h:
            return None
        
        for_evidence = []
        against_evidence = []
        
        for e_id in h['evidence']:
            if e_id in self.evidence_registry:
                for_evidence.append(self.evidence_registry[e_id])
        
        for e_id in h['against']:
            if e_id in self.evidence_registry:
                against_evidence.append(self.evidence_registry[e_id])
        
        return {
            'for': for_evidence,
            'against': against_evidence,
            'net_evidence': len(for_evidence) - len(against_evidence)
        }
    
    def get_confidence_band(self):
        """Traduce la probabilidad a banda de confianza (Gemini)"""
        best, score = self.get_best_hypothesis()
        
        if score >= 0.80:
            band = "🟢 ALTA - Ejecución Inminente"
            action = "Preparar compra de boletos"
        elif score >= 0.50:
            band = "🟡 MEDIA - Planificación Activa"
            action = "Monitoreo intensivo"
        elif score >= 0.20:
            band = "🟠 BAJA - Fase de Exploración"
            action = "Buscar más evidencia"
        else:
            band = "🔴 MUY BAJA - Ruta Fría"
            action = "Reevaluar hipótesis"
        
        return {
            'band': band,
            'action': action,
            'best_hypothesis': best,
            'probability': score
        }

# ============================================================
# EJEMPLO DE USO
# ============================================================

def main():
    print("🐋 SAKURA V4 - MOTOR ACH + BAYES")
    print("=" * 60)
    
    # Crear el motor
    engine = ACHBayesEngine()
    
    # ============================================================
    # REGISTRAR EVIDENCIA
    # ============================================================
    
    print("\n📋 REGISTRANDO EVIDENCIA...")
    
    # Evidencia 1: RoD firmado (a favor de H1)
    engine.add_evidence(
        title="Firma del Record of Discussions entre AAC y MLIT",
        source="UHN Plus",
        category="oficial",
        supports=True,
        hypothesis_id="H1",
        strength=1.5
    )
    print("   ✅ EVID-0001: RoD firmado (a favor de H1)")
    
    # Evidencia 2: Visita técnica de ANA (a favor de H1)
    engine.add_evidence(
        title="Visita técnica de ANA y Boeing a Tocumen",
        source="Infobae",
        category="especializada",
        supports=True,
        hypothesis_id="H1",
        strength=1.2
    )
    print("   ✅ EVID-0002: Visita técnica (a favor de H1)")
    
    # Evidencia 3: Acuerdo bilateral (a favor de H1)
    engine.add_evidence(
        title="Acuerdo bilateral Panamá-Japón",
        source="La Prensa",
        category="general",
        supports=True,
        hypothesis_id="H1",
        strength=1.0
    )
    print("   ✅ EVID-0003: Acuerdo bilateral (a favor de H1)")
    
    # Evidencia 4: Sin slots en PTY (en contra de H1 - Tripwire)
    engine.add_evidence(
        title="No hay solicitud de slots en PTY para 2027",
        source="Sistema Sakura - Tripwire",
        category="oficial",
        supports=False,
        hypothesis_id="H1",
        strength=1.3
    )
    print("   ✅ EVID-0004: Sin slots en PTY (en contra de H1)")
    
    # Evidencia 5: Sin mención en earnings call (en contra de H1)
    engine.add_evidence(
        title="ANA no menciona Panamá en su earnings call",
        source="Sistema Sakura - Tripwire",
        category="oficial",
        supports=False,
        hypothesis_id="H1",
        strength=0.8
    )
    print("   ✅ EVID-0005: Sin mención en earnings call (en contra de H1)")
    
    # ============================================================
    # RESULTADOS
    # ============================================================
    
    print("\n" + "=" * 60)
    print("📊 RESULTADOS ACH + BAYES")
    print("=" * 60)
    
    # Mostrar todas las hipótesis
    hypotheses = engine.get_all_hypotheses()
    for h in hypotheses:
        status = "✅ Activa" if h['status'] == 'active' else "❌ Inactiva"
        print(f"\n🔹 {h['id']}: {h['name']}")
        print(f"   Probabilidad: {h['probability']*100:.1f}%")
        print(f"   Estado: {status}")
        print(f"   Evidencia a favor: {h['evidence_count']}")
        print(f"   Evidencia en contra: {h['against_count']}")
    
    # Mejor hipótesis
    best, score = engine.get_best_hypothesis()
    print(f"\n🏆 MEJOR HIPÓTESIS: {best} ({score*100:.1f}%)")
    
    # Banda de confianza (Gemini)
    confidence = engine.get_confidence_band()
    print(f"\n📈 CONFIANZA: {confidence['band']}")
    print(f"🎯 ACCIÓN SUGERIDA: {confidence['action']}")
    
    # Resumen de evidencia
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE EVIDENCIA PARA H1")
    print("=" * 60)
    
    evidence_summary = engine.get_evidence_summary('H1')
    if evidence_summary:
        print(f"\n✅ EVIDENCIA A FAVOR ({len(evidence_summary['for'])}):")
        for e in evidence_summary['for']:
            print(f"   • {e['title']} ({e['source']})")
        
        print(f"\n❌ EVIDENCIA EN CONTRA ({len(evidence_summary['against'])}):")
        for e in evidence_summary['against']:
            print(f"   • {e['title']} ({e['source']})")
        
        print(f"\n📊 BALANCE NETO: {evidence_summary['net_evidence']}")

if __name__ == "__main__":
    main()
