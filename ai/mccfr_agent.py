# ai/mccfr_agent.py
import numpy as np
from typing import Dict, List, Tuple, Set
import json
from .game_rules import PineappleRules
from .evaluator import HandEvaluator

class MCCFRAgent:
    def __init__(self, progressive: bool = False):
        self.progressive = progressive
        self.strategy_map = {}
        self.regret_sum = {}
        self.strategy_sum = {}
        self.remaining_cards: Set[int] = set(range(52))
        self.fantasy_bonus = 2.0
        self.rules = PineappleRules()
        self.evaluator = HandEvaluator()
        
    def get_action(self, game_state: Dict) -> Dict:
        """Gets the best action for the current game state"""
        if game_state.get('fantasy_mode'):
            return self._get_fantasy_action(game_state)
        return self._get_regular_action(game_state)
        
    def _get_fantasy_action(self, game_state: Dict) -> Dict:
        """Handles fantasy mode decision making"""
        available_cards = self._get_available_cards(game_state)
        if not available_cards:
            return {}
            
        possible_hands = self._generate_possible_hands(available_cards)
        if not possible_hands:
            return {}
            
        best_hand = None
        best_value = float('-inf')
        
        for hand in possible_hands:
            # Split hand into lines
            table = {
                'top': hand[:3],
                'middle': hand[3:8],
                'bottom': hand[8:13]
            }
            
            # Evaluate complete hand
            value = self._evaluate_complete_hand(table)
            
            # Consider fantasy potential
            if self.rules.check_fantasy(table['top'])['fantasy']:
                value *= (1 + self.fantasy_bonus)
                
            if value > best_value:
                best_value = value
                best_hand = table
                
        return best_hand
        
    def _get_regular_action(self, game_state: Dict) -> Dict:
        """Handles regular gameplay decision making"""
        info_set = self._get_information_set(game_state)
        strategy = self._get_strategy(info_set)
        
        legal_actions = self._get_legal_actions(game_state)
        if not legal_actions:
            return {}
            
        action_values = []
        
        for action in legal_actions:
            action_str = str(action)
            prob = strategy.get(action_str, 1.0 / len(legal_actions))
            value = self._evaluate_action(action, game_state)
            action_values.append((action, prob * value))
            
        return max(action_values, key=lambda x: x[1])[0]
        def train(self, iterations: int = 1000):
        """Trains the agent using MCCFR algorithm"""
        for _ in range(iterations):
            game_state = self._create_training_state()
            self._cfr_iteration(game_state, 1.0)

    def update_cards_knowledge(self, visible_cards: List[Dict]):
        """Updates knowledge about available cards"""
        for card in visible_cards:
            card_index = self._card_to_index(card)
            self.remaining_cards.discard(card_index)
            
    def save_state(self) -> str:
        """Saves agent's current state"""
        state = {
            'progressive': self.progressive,
            'strategy_map': self.strategy_map,
            'regret_sum': self.regret_sum,
            'strategy_sum': self.strategy_sum,
            'remaining_cards': list(self.remaining_cards)
        }
        return json.dumps(state)

    def load_state(self, state_json: str):
        """Loads agent's state"""
        state = json.loads(state_json)
        self.progressive = state['progressive']
        self.strategy_map = state['strategy_map']
        self.regret_sum = state['regret_sum']
        self.strategy_sum = state['strategy_sum']
        self.remaining_cards = set(state['remaining_cards'])

    def _evaluate_complete_hand(self, table: Dict) -> float:
        """Evaluates the complete hand including all lines"""
        if not self._is_valid_hand(table):
            return float('-inf')
            
        # Evaluate each line using evaluator
        top_value = self.evaluator.evaluate_top(table['top'])
        middle_value = self.evaluator.evaluate_middle(table['middle'])
        bottom_value = self.evaluator.evaluate_bottom(table['bottom'])
        
        # Calculate royalties
        royalties = self._calculate_royalties(table)
        
        # Normalize values
        max_top = 22
        max_middle = 9100
        max_bottom = 9100
        
        normalized_top = top_value / max_top
        normalized_middle = middle_value / max_middle
        normalized_bottom = bottom_value / max_bottom
        
        # Weight each component
        hand_value = (normalized_top * 0.2 +
                     normalized_middle * 0.35 +
                     normalized_bottom * 0.45)
                     
        # Add royalties bonus
        total_value = hand_value + (royalties / 97.0)  # 97 is max possible royalties
        
        return total_value

    def _calculate_royalties(self, table: Dict) -> float:
        """Calculates total royalties for a hand"""
        top_royalties = self.evaluator._get_top_royalty(table['top'])
        middle_royalties = self.evaluator._get_middle_royalty(table['middle'])
        bottom_royalties = self.evaluator._get_bottom_royalty(table['bottom'])
        
        return top_royalties + middle_royalties + bottom_royalties

    def _evaluate_action(self, action: Dict, game_state: Dict) -> float:
        """Evaluates a single action"""
        # Base hand evaluation
        hand_value = self._evaluate_complete_hand(action)
        
        # Fantasy potential bonus
        fantasy_check = self.rules.check_fantasy(action.get('top', []))
        fantasy_bonus = self.fantasy_bonus if fantasy_check['fantasy'] else 0
        
        # Consider cards remaining for future streets
        remaining_potential = self._evaluate_remaining_potential(game_state)
        
        return hand_value * (1 + fantasy_bonus) + remaining_potential
        def _evaluate_remaining_potential(self, game_state: Dict) -> float:
        """Evaluates potential for improvement with remaining cards"""
        available_cards = self._get_available_cards(game_state)
        if not available_cards:
            return 0.0
            
        potential = 0.0
        table = game_state.get('table', {})
        
        # Evaluate potential for each line
        for line, cards in table.items():
            if line == 'top' and len(cards) < 3:
                potential += self._evaluate_line_potential(cards, available_cards, 'top')
            elif line in ['middle', 'bottom'] and len(cards) < 5:
                potential += self._evaluate_line_potential(cards, available_cards, line)
                
        return potential * 0.1  # Scale down potential

    def _evaluate_line_potential(self, current_cards: List[Dict], available_cards: List[Dict], line_type: str) -> float:
        """Evaluates potential improvements for a specific line"""
        if not current_cards or not available_cards:
            return 0.0
            
        current_value = self._evaluate_line(current_cards, line_type)
        max_potential = 0.0
        
        # Try each available card
        for card in available_cards:
            new_cards = current_cards + [card]
            new_value = self._evaluate_line(new_cards, line_type)
            max_potential = max(max_potential, new_value - current_value)
            
        return max_potential

    def _evaluate_line(self, cards: List[Dict], line_type: str) -> float:
        """Evaluates a single line using appropriate evaluator method"""
        if line_type == 'top':
            return self.evaluator.evaluate_top(cards)
        elif line_type == 'middle':
            return self.evaluator.evaluate_middle(cards)
        else:  # bottom
            return self.evaluator.evaluate_bottom(cards)

    def _get_strategy(self, info_set: str) -> Dict:
        """Gets current strategy for the information set"""
        if info_set not in self.strategy_map:
            return self._initialize_strategy(info_set)
            
        strategy = {}
        normalizing_sum = 0
        
        actions = self._get_legal_actions({'info_set': info_set})
        
        for action in actions:
            strategy_sum = self.strategy_sum.get((info_set, str(action)), 0)
            regret_sum = self.regret_sum.get((info_set, str(action)), 0)
            
            if regret_sum > 0:
                strategy[str(action)] = regret_sum
            else:
                strategy[str(action)] = 0
            normalizing_sum += strategy[str(action)]
            
        if normalizing_sum > 0:
            for action in actions:
                strategy[str(action)] /= normalizing_sum
        else:
            prob = 1.0 / len(actions)
            for action in actions:
                strategy[str(action)] = prob
                
        return strategy

    def _card_to_index(self, card: Dict) -> int:
        """Converts card dictionary to unique index"""
        suit_values = {'♠': 0, '♣': 1, '♥': 2, '♦': 3}
        rank_values = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6,
                      '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
        return suit_values[card['suit']] * 13 + rank_values[card['rank']]
        def _index_to_card(self, index: int) -> Dict:
        """Converts index back to card dictionary"""
        suit_index = index // 13
        rank_index = index % 13
        
        suits = ['♠', '♣', '♥', '♦']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        
        return {
            'suit': suits[suit_index],
            'rank': ranks[rank_index]
        }

    def _get_information_set(self, game_state: Dict) -> str:
        """Creates string representation of current game state"""
        table = game_state.get('table', {})
        visible_cards = []
        
        # Add cards from each line to visible cards
        for position in ['top', 'middle', 'bottom']:
            cards = table.get(position, [])
            visible_cards.extend(f"{card['rank']}{card['suit']}" for card in cards)
            
        # Add known opponent cards
        opponent_cards = game_state.get('opponent_cards', [])
        visible_cards.extend(f"{card['rank']}{card['suit']}" for card in opponent_cards)
        
        # Sort for consistent representation
        return '|'.join(sorted(visible_cards))

    def _get_available_cards(self, game_state: Dict) -> List[Dict]:
        """Gets list of cards that can still be used"""
        used_cards = set()
        
        # Add cards from the table
        table = game_state.get('table', {})
        for position in ['top', 'middle', 'bottom']:
            for card in table.get(position, []):
                used_cards.add(self._card_to_index(card))
                
        # Get currently available cards
        available = []
        for i in range(52):
            if i not in used_cards and i in self.remaining_cards:
                available.append(self._index_to_card(i))
                
        return available

    def _generate_possible_hands(self, available_cards: List[Dict]) -> List[List[Dict]]:
        """Generates all possible valid hands from available cards"""
        cards_needed = 14 if not self.progressive else 17
        possible_hands = []
        
        for combination in self._generate_combinations(available_cards, cards_needed):
            if self._is_valid_fantasy_hand(combination):
                possible_hands.append(combination)
                
        return possible_hands

    def _generate_combinations(self, cards: List[Dict], count: int) -> List[List[Dict]]:
        """Generates all possible card combinations"""
        if count <= 0:
            return [[]]
        if not cards:
            return []
            
        result = []
        for i in range(len(cards)):
            first = cards[i]
            rest = cards[i+1:]
            for combo in self._generate_combinations(rest, count-1):
                result.append([first] + combo)
                
        return result

    def _is_valid_hand(self, table: Dict) -> bool:
        """Validates if hand follows game rules"""
        if not table:
            return False
            
        top = table.get('top', [])
        middle = table.get('middle', [])
        bottom = table.get('bottom', [])
        
        if len(top) > 3 or len(middle) > 5 or len(bottom) > 5:
            return False
            
        if len(top) == 3 and len(middle) == 5 and len(bottom) == 5:
            top_value = self.evaluator.evaluate_top(top)
            middle_value = self.evaluator.evaluate_middle(middle)
            bottom_value = self.evaluator.evaluate_bottom(bottom)
            
            # Check ascending strength rule
            return top_value <= middle_value <= bottom_value
            
        return True

    def _is_valid_fantasy_hand(self, cards: List[Dict]) -> bool:
        """Validates a fantasy hand"""
        if len(cards) not in [14, 17]:  # Standard or Progressive fantasy
            return False
            
        # Split hand into lines
        table = {
            'top': cards[:3],
            'middle': cards[3:8],
            'bottom': cards[8:13]
        }
        
        return self._is_valid_hand(table)
