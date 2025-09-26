
from typing import List, Dict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import euclidean
import logging

logger = logging.getLogger(__name__)

def match_elements(eng_elements: List[Dict], spa_elements: List[Dict], pos_tolerance: float = 100.0, sim_threshold: float = 0.5, dist_weight: float = 1.0, sim_weight: float = 1.0, model=None) -> List[tuple]:
    matched = []
    used_spa = set()
    eng_texts = [e['text'] for e in eng_elements]
    spa_texts = [e['text'] for e in spa_elements]
    if eng_texts and spa_texts and model:
        eng_embs = model.encode(eng_texts)
        spa_embs = model.encode(spa_texts)
        sim_matrix = cosine_similarity(eng_embs, spa_embs)
    else:
        sim_matrix = np.zeros((len(eng_elements), len(spa_elements)))

    eng_elements.sort(key=lambda e: (e['rect']['y'], e['rect']['x']))
    spa_elements.sort(key=lambda s: (s['rect']['y'], s['rect']['x']))

    for i, eng in enumerate(eng_elements):
        eng_center = (eng['rect']['x'] + eng['rect']['width'] / 2, eng['rect']['y'] + eng['rect']['height'] / 2)
        best_match = None
        best_score = float('inf')
        for j, spa in enumerate(spa_elements):
            if j in used_spa:
                continue
            spa_center = (spa['rect']['x'] + spa['rect']['width'] / 2, spa['rect']['y'] + spa['rect']['height'] / 2)
            pos_dist = euclidean(eng_center, spa_center)
            sem_sim = sim_matrix[i][j] if eng_texts and spa_texts else 0.0
            combined_score = dist_weight * pos_dist - sim_weight * sem_sim
            if pos_dist < pos_tolerance and sem_sim > sim_threshold and combined_score < best_score:
                best_score = combined_score
                best_match = (j, spa)
        if best_match:
            j, spa = best_match
            used_spa.add(j)
            matched.append((eng, spa))
        else:
            matched.append((eng, None))
    for j, spa in enumerate(spa_elements):
        if j not in used_spa:
            matched.append((None, spa))
    num_matched = len([p for p in matched if p[0] and p[1]])
    num_un_eng = len([p for p in matched if p[0] and not p[1]])
    num_un_spa = len([p for p in matched if not p[0] and p[1]])
    logger.info(f"Matched {num_matched} pairs, {num_un_eng} unmatched English, {num_un_spa} unmatched Spanish")
    return matched