# ai/game_rules.py
from typing import List, Dict
from .evaluator import HandEvaluator

class PineappleRules:
    def __init__(self):
        self.evaluator = HandEvaluator()
        
    def is_valid_hand(self, top: List[Dict], middle: List[Dict], bottom: List[Dict]) -> bool:
        """Проверяет валидность всей руки"""
        if len(top) != 3 or len(middle) != 5 or len(bottom) != 5:
            return False
            
        # Проверяем правило возрастания силы комбинаций
        top_value = self.evaluator.evaluate_top(top)
        middle_value = self.evaluator.evaluate_middle(middle)
        bottom_value = self.evaluator.evaluate_bottom(bottom)
        
        return top_value <= middle_value <= bottom_value
        
    def check_fantasy(self, top_cards: List[Dict]) -> Dict:
        """Проверяет возможность фантазии и определяет тип"""
        if not top_cards or len(top_cards) != 3:
            return {'fantasy': False, 'type': None, 'extra_cards': 0}
            
        ranks = [card['rank'] for card in top_cards]
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
            
        # Проверяем условия фантазии
        if rank_counts.get('Q', 0) >= 2:
            return {'fantasy': True, 'type': 'QQ', 'extra_cards': 14}
        if rank_counts.get('K', 0) >= 2:
            return {'fantasy': True, 'type': 'KK', 'extra_cards': 15}
        if rank_counts.get('A', 0) >= 2:
            return {'fantasy': True, 'type': 'AA', 'extra_cards': 16}
            
        # Проверяем сеты
        for rank in '23456789TJQKA':
            if rank_counts.get(rank, 0) >= 3:
                return {'fantasy': True, 'type': f'Set of {rank}', 'extra_cards': 17}
                
        return {'fantasy': False, 'type': None, 'extra_cards': 0}
        
    def calculate_score(self, hand1: Dict, hand2: Dict) -> int:
        """Подсчитывает очки при сравнении двух рук"""
        score = 0
        
        # Сравниваем верхние линии
        if self.evaluator.evaluate_top(hand1['top']) > self.evaluator.evaluate_top(hand2['top']):
            score += 1
            
        # Сравниваем средние линии    
        if self.evaluator.evaluate_middle(hand1['middle']) > self.evaluator.evaluate_middle(hand2['middle']):
            score += 1
            
        # Сравниваем нижние линии    
        if self.evaluator.evaluate_bottom(hand1['bottom']) > self.evaluator.evaluate_bottom(hand2['bottom']):
            score += 1
            
        # Бонус за выигрыш всех линий
        if score == 3:
            score += 3
            
        return score
        
    def get_royalties(self, hand: Dict) -> Dict[str, int]:
        """Подсчитывает бонусы за комбинации"""
        royalties = {'top': 0, 'middle': 0, 'bottom': 0}
        
        # Бонусы за верхнюю линию
        top_value = self.evaluator.evaluate_top(hand['top'])
        if top_value >= 10:  # Сет
            royalties['top'] = self._get_top_royalty(hand['top'])
            
        # Бонусы за среднюю линию
        middle_value = self.evaluator.evaluate_middle(hand['middle'])
        if middle_value >= 3000:  # От сета и выше
            royalties['middle'] = self._get_middle_royalty(hand['middle'])
            
        # Бонусы за нижнюю линию
        bottom_value = self.evaluator.evaluate_bottom(hand['bottom'])
        if bottom_value >= 4000:  # От стрита и выше
            royalties['bottom'] = self._get_bottom_royalty(hand['bottom'])
            
        return royalties
        
    def _get_top_royalty(self, cards: List[Dict]) -> int:
        """Подсчитывает бонусы за верхнюю линию"""
        ranks = [card['rank'] for card in cards]
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
            
        # Проверяем пары и сеты
        for rank in 'AKQJT98765432':
            if rank_counts.get(rank, 0) == 2:
                return {'A': 9, 'K': 8, 'Q': 7, 'J': 6, 'T': 5,
                       '9': 4, '8': 3, '7': 2, '6': 1}.get(rank, 0)
            elif rank_counts.get(rank, 0) == 3:
                return {'A': 22, 'K': 21, 'Q': 20, 'J': 19, 'T': 18,
                       '9': 17, '8': 16, '7': 15, '6': 14, '5': 13,
                       '4': 12, '3': 11, '2': 10}.get(rank, 0)
        return 0
