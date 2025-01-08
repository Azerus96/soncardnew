# ai/mccfr_agent.py
from typing import List, Dict, Set, Tuple
import numpy as np
import json
from .game_rules import PineappleRules
from .evaluator import HandEvaluator

class MCCFRAgent:
    def __init__(self, progressive: bool = False):
        self.progressive = progressive
        self.rules = PineappleRules()
        self.evaluator = HandEvaluator()
        
        # Стратегии и счетчики
        self.strategy_map = {}
        self.regret_sum = {}
        self.strategy_sum = {}
        
        # Информация о картах
        self.cards_info = {
            'remaining': set(range(52)),
            'visible': set(),
            'fantasy_potential': 0.0
        }
        
        # Веса для оценки стратегий
        self.weights = {
            'fantasy': 2.0,    # Вес для достижения фантазии
            'royalty': 1.5,    # Вес для получения бонусов
            'winning': 1.0     # Вес для победы в линиях
        }
        
    def get_action(self, game_state: Dict) -> Dict:
        """Выбирает лучший ход в текущей ситуации"""
        if game_state.get('fantasy_mode'):
            return self._get_fantasy_action(game_state)
        return self._get_regular_action(game_state)
        
    def _get_fantasy_action(self, game_state: Dict) -> Dict:
        """Логика для режима фантазии"""
        available_cards = self._get_available_cards(game_state)
        possible_hands = self._generate_possible_hands(
            available_cards,
            extra_cards=self._get_fantasy_cards_count(game_state)
        )
        
        best_hand = None
        best_value = float('-inf')
        
        for hand in possible_hands:
            value = self._evaluate_fantasy_hand(hand)
            if value > best_value and self.rules.is_valid_hand(**hand):
                best_value = value
                best_hand = hand
                
        return best_hand
        
    def _get_regular_action(self, game_state: Dict) -> Dict:
        """Логика для обычного режима"""
        info_set = self._get_information_set(game_state)
        strategy = self._get_strategy(info_set)
        
        # Получаем возможные действия
        legal_actions = self._get_legal_actions(game_state)
        
        # Оцениваем каждое действие
        action_values = []
        for action in legal_actions:
            base_value = strategy.get(str(action), 1.0)
            fantasy_value = self._evaluate_fantasy_potential(action)
            royalty_value = self._evaluate_royalties(action)
            winning_value = self._evaluate_winning_chances(action, game_state)
            
            total_value = (
                base_value +
                self.weights['fantasy'] * fantasy_value +
                self.weights['royalty'] * royalty_value +
                self.weights['winning'] * winning_value
            )
            
            action_values.append((action, total_value))
            
        # Выбираем лучшее действие
        return max(action_values, key=lambda x: x[1])[0]
        
    def train(self, iterations: int = 1000):
        """Тренировка агента"""
        for _ in range(iterations):
            game_state = self._create_training_state()
            utility = self._cfr_iteration(game_state, 1.0)
            
            # Обновляем веса на основе результатов
            self._update_weights(utility)
            
    def _cfr_iteration(self, game_state: Dict, reach_probability: float) -> float:
        """Одна итерация CFR"""
        if self._is_terminal(game_state):
            return self._get_utility(game_state)
            
        info_set = self._get_information_set(game_state)
        strategy = self._get_strategy(info_set)
        
        # Вычисляем значения действий
        action_utilities = {}
        node_utility = 0
        
        for action in self._get_legal_actions(game_state):
            new_state = self._apply_action(game_state, action)
            action_utility = self._cfr_iteration(new_state, 
                                              reach_probability * strategy[str(action)])
            action_utilities[str(action)] = action_utility
            node_utility += strategy[str(action)] * action_utility
            
        # Обновляем сожаления и стратегию
        for action in action_utilities:
            regret = action_utilities[action] - node_utility
            self.regret_sum[info_set][action] += reach_probability * regret
            self.strategy_sum[info_set][action] += reach_probability * strategy[action]
            
        return node_utility
        
    def _get_strategy(self, info_set: str) -> Dict[str, float]:
        """Получает текущую стратегию для информационного набора"""
        if info_set not in self.strategy_map:
            self.strategy_map[info_set] = {}
            self.regret_sum[info_set] = {}
            self.strategy_sum[info_set] = {}
            
        # Нормализуем сожаления
        regret_sum = self.regret_sum[info_set]
        positive_regrets = {a: max(r, 0) for a, r in regret_sum.items()}
        regret_sum = sum(positive_regrets.values())
        
        if regret_sum > 0:
            strategy = {a: r/regret_sum for a, r in positive_regrets.items()}
        else:
            # Равномерная стратегия если нет положительных сожалений
            actions = len(positive_regrets)
            strategy = {a: 1.0/actions for a in positive_regrets}
            
        return strategy

 def _evaluate_fantasy_potential(self, hand: Dict) -> float:
        """Оценивает потенциал достижения фантазии"""
        top_cards = hand.get('top', [])
        if not top_cards:
            return 0.0
            
        fantasy_check = self.rules.check_fantasy(top_cards)
        if fantasy_check['fantasy']:
            # Уже собрана фантазия
            return 1.0
            
        # Оцениваем близость к фантазии
        ranks = [card['rank'] for card in top_cards]
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
            
        # Оцениваем потенциал для различных типов фантазии
        potential = 0.0
        
        # Для пар
        for rank in 'QKA':
            if rank_counts.get(rank, 0) == 1:
                remaining_in_deck = self._count_remaining_rank(rank)
                potential = max(potential, 0.5 * remaining_in_deck / 4)
                
        # Для сетов
        for rank in '23456789TJQKA':
            if rank_counts.get(rank, 0) == 2:
                remaining_in_deck = self._count_remaining_rank(rank)
                potential = max(potential, 0.8 * remaining_in_deck / 4)
                
        return potential
        
    def _evaluate_royalties(self, hand: Dict) -> float:
        """Оценивает потенциальные бонусы"""
        royalties = self.rules.get_royalties(hand)
        total_royalties = sum(royalties.values())
        
        

        # Нормализуем значение бонусов
        max_possible_royalties = 50  # Максимально возможные бонусы
        normalized_royalties = total_royalties / max_possible_royalties
        
        # Оцениваем потенциал фантазии
        fantasy_potential = 0
        if hand['top']:
            fantasy_check = self.rules.check_fantasy(hand['top'])
            if fantasy_check['fantasy']:
                fantasy_potential = 1.0
                if fantasy_check['type'] in ['KK', 'AA']:
                    fantasy_potential = 1.5
                elif 'Set' in fantasy_check['type']:
                    fantasy_potential = 2.0
                    
        # Комбинируем все факторы
        final_score = (base_hand_value + 
                      normalized_royalties * self.royalty_weight +
                      fantasy_potential * self.fantasy_weight)
                      
        return final_score

    def _cfr_iteration(self, game_state: Dict, reach_probability: float):
        """Выполняет одну итерацию CFR"""
        if self._is_terminal(game_state):
            return self._get_terminal_value(game_state)
            
        info_set = self._get_information_set(game_state)
        
        # Получаем текущую стратегию
        strategy = self._get_strategy(info_set)
        
        # Вычисляем значения для каждого действия
        action_values = {}
        node_value = 0
        
        for action in self._get_legal_actions(game_state):
            next_state = self._apply_action(game_state, action)
            action_value = -self._cfr_iteration(next_state, 
                                              reach_probability * strategy[str(action)])
            action_values[str(action)] = action_value
            node_value += strategy[str(action)] * action_value
            
        # Обновляем сожаления и стратегию
        for action in action_values:
            regret = action_values[action] - node_value
            self.regret_sum[info_set][action] = (
                self.regret_sum[info_set].get(action, 0) + 
                reach_probability * regret
            )
            self.strategy_sum[info_set][action] = (
                self.strategy_sum[info_set].get(action, 0) + 
                reach_probability * strategy[action]
            )
            
        return node_value

    def _get_legal_actions(self, game_state: Dict) -> List[Dict]:
        """Получает список возможных действий"""
        if game_state.get('fantasy_mode'):
            return self._get_fantasy_actions(game_state)
        return self._get_regular_actions(game_state)
        
    def _get_fantasy_actions(self, game_state: Dict) -> List[Dict]:
        """Генерирует возможные действия для режима фантазии"""
        available_cards = self._get_available_cards(game_state)
        hand_size = self._get_fantasy_hand_size(game_state)
        
        possible_hands = []
        self._generate_fantasy_hands(available_cards, hand_size, [], possible_hands)
        
        return possible_hands
        
    def _generate_fantasy_hands(self, available_cards: List[Dict], 
                              cards_needed: int,
                              current_hand: List[Dict],
                              possible_hands: List[Dict]):
        """Рекурсивно генерирует возможные руки для фантазии"""
        if cards_needed == 0:
            if self.rules.is_valid_hand(current_hand[:3],
                                      current_hand[3:8],
                                      current_hand[8:]):
                possible_hands.append(current_hand.copy())
            return
            
        for i, card in enumerate(available_cards):
            current_hand.append(card)
            remaining_cards = available_cards[:i] + available_cards[i+1:]
            self._generate_fantasy_hands(remaining_cards,
                                      cards_needed - 1,
                                      current_hand,
                                      possible_hands)
            current_hand.pop()
            
    def _get_fantasy_hand_size(self, game_state: Dict) -> int:
        """Определяет количество карт для фантазии"""
        if not self.progressive:
            return 14
            
        top_line = game_state['table']['top']
        fantasy_info = self.rules.check_fantasy(top_line)
        return fantasy_info['extra_cards']
        
    def _get_available_cards(self, game_state: Dict) -> List[Dict]:
        """Получает список доступных карт"""
        used_cards = set()
        
        # Собираем использованные карты
        for line in ['top', 'middle', 'bottom']:
            for card in game_state['table'].get(line, []):
                if card:
                    used_cards.add(f"{card['rank']}{card['suit']}")
                    
        # Добавляем видимые карты противников
        for card in game_state.get('visible_cards', []):
            used_cards.add(f"{card['rank']}{card['suit']}")
            
        # Генерируем доступные карты
        available = []
        for rank in 'AKQJT98765432':
            for suit in '♠♣♥♦':
                card_key = f"{rank}{suit}"
                if card_key not in used_cards:
                    available.append({'rank': rank, 'suit': suit})
                    
        return available

    def _is_terminal(self, game_state: Dict) -> bool:
        """Проверяет, является ли состояние конечным"""
        return (len(game_state['table']['top']) == 3 and
                len(game_state['table']['middle']) == 5 and
                len(game_state['table']['bottom']) == 5)
def _get_terminal_value(self, game_state: Dict) -> float:
        """Вычисляет значение конечного состояния"""
        if not self._is_valid_hand(game_state['table']):
            return -1000  # Штраф за невалидную руку
            
        # Оцениваем комбинации
hand_value = (
            self.evaluator.evaluate_top(game_state['table']['top']) +
            self.evaluator.evaluate_middle(game_state['table']['middle']) +
            self.evaluator.evaluate_bottom(game_state['table']['bottom'])
        )
        
        # Учитываем бонусы
royalties = self.rules.get_royalties(game_state['table'])
        royalty_value = sum(royalties.values())
        
        # Проверяем фантазию
        fantasy_value = 0
        if self.rules.check_fantasy(game_state['table']['top'])['fantasy']:
            fantasy_value = 100  # Большой бонус за фантазию
return hand_value + royalty_value + fantasy_value
        
    def _get_information_set(self, game_state: Dict) -> str:
        """Создает строковое представление информационного набора"""
        info_parts = []
        
        # Добавляем информацию о картах на столе

for line in ['top', 'middle', 'bottom']:
            cards = game_state['table'].get(line, [])
            info_parts.append(''.join(f"{c['rank']}{c['suit']}" for c in cards if c))
            
        # Добавляем информацию о видимых картах
        visible = sorted(
f"{c['rank']}{c['suit']}" for c in game_state.get('visible_cards', [])
        )
        info_parts.append(''.join(visible))
        
        # Добавляем режим фантазии
        if game_state.get('fantasy_mode'):
info_parts.append('F')
            if self.progressive:
                info_parts.append('P')
                
        return '|'.join(info_parts)
        
    def _get_strategy(self, info_set: str) -> Dict[str, float]:
        """Получает текущую стратегию для информационного набора"""
if info_set not in self.strategy_map:

    def _evaluate_royalties(self, hand: Dict) -> float:
        """Оценивает потенциальные бонусы"""
        royalties = self.rules.get_royalties(hand)
        total_royalties = sum(royalties.values())
        
        # Нормализуем значение бонусов
        max_possible_royalties = 97  # 22 (top) + 50 (middle) + 25 (bottom)
        normalized_royalties = total_royalties / max_possible_royalties
        
        return normalized_royalties
        
    def _get_strategy(self, info_set: str) -> Dict:
        """Получает текущую стратегию для информационного набора"""
        if info_set not in self.strategy_map:
            # Инициализируем новую стратегию
            return self._initialize_strategy(info_set)
            
        strategy = {}
        normalizing_sum = 0
        
        # Получаем все возможные действия для этого состояния
        actions = self._get_legal_actions(info_set)
        
        # Вычисляем стратегию на основе накопленных сожалений
        for action in actions:
            strategy_sum = self.strategy_sum.get((info_set, str(action)), 0)
            regret_sum = self.regret_sum.get((info_set, str(action)), 0)
            
            if regret_sum > 0:
                strategy[str(action)] = regret_sum
            else:
                strategy[str(action)] = 0
            normalizing_sum += strategy[str(action)]
            
        # Нормализуем стратегию
        if normalizing_sum > 0:
            for action in actions:
                strategy[str(action)] /= normalizing_sum
        else:
            # Если нет положительных сожалений, используем равномерное распределение
            prob = 1.0 / len(actions)
            for action in actions:
                strategy[str(action)] = prob
                
        return strategy
        
    def _initialize_strategy(self, info_set: str) -> Dict:
        """Инициализирует новую стратегию для информационного набора"""
        actions = self._get_legal_actions(info_set)
        strategy = {}
        
        # Равномерное распределение вероятностей
        prob = 1.0 / len(actions)
        for action in actions:
            strategy[str(action)] = prob
            
        self.strategy_map[info_set] = strategy
        return strategy
        
    def _update_regrets(self, info_set: str, action: str, regret: float):
        """Обновляет накопленные сожаления"""
        key = (info_set, action)
        self.regret_sum[key] = self.regret_sum.get(key, 0) + regret
        
    def _update_strategy_sum(self, info_set: str, strategy: Dict):
        """Обновляет накопленную стратегию"""
        for action, prob in strategy.items():
            key = (info_set, action)
            self.strategy_sum[key] = self.strategy_sum.get(key, 0) + prob
            
    def _cfr_iteration(self, game_state: Dict, reach_prob: float):
        """Выполняет одну итерацию CFR"""
        info_set = self._get_information_set(game_state)
        strategy = self._get_strategy(info_set)
        
        # Вычисляем значения для каждого действия
        action_values = {}
        for action in self._get_legal_actions(info_set):
            next_state = self._apply_action(game_state, action)
            action_values[str(action)] = self._cfr_value(next_state, reach_prob * strategy[str(action)])
            
        # Вычисляем ожидаемое значение узла
        node_value = sum(prob * action_values[action] for action, prob in strategy.items())
        
        # Обновляем сожаления и накопленную стратегию
        for action in self._get_legal_actions(info_set):
            regret = action_values[str(action)] - node_value
            self._update_regrets(info_set, str(action), reach_prob * regret)
            
        self._update_strategy_sum(info_set, strategy)
        return node_value
        
    def _cfr_value(self, game_state: Dict, reach_prob: float) -> float:
        """Вычисляет значение для состояния игры"""
        if self._is_terminal(game_state):
            return self._get_terminal_value(game_state)
            
        return self._cfr_iteration(game_state, reach_prob)
        
    def _is_terminal(self, game_state: Dict) -> bool:
        """Проверяет, является ли состояние терминальным"""
        if not game_state:
            return True
            
        # Проверяем завершение раздачи
        cards_placed = sum(len(line) for line in game_state['table'].values())
        return cards_placed == 13  # 3 (top) + 5 (middle) + 5 (bottom)
        
    def _get_terminal_value(self, game_state: Dict) -> float:
        """Вычисляет значение терминального состояния"""
        if not self._is_valid_hand(game_state):
            return -1.0  # Штраф за невалидную руку
            
        # Оцениваем комбинации
        hand_value = self._evaluate_hand(game_state)
        royalties = self._evaluate_royalties(game_state)
        fantasy_potential = self._evaluate_fantasy_potential(game_state)
        
        # Комбинируем все факторы
        total_value = (hand_value + royalties) * (1 + self.fantasy_bonus * fantasy_potential)
        
        return total_value
