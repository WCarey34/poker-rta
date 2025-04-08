from treys import Card, Deck, Evaluator
import random

evaluator = Evaluator()

def convert_to_treys(cards):
    return [Card.new(card) for card in cards]

def calculate_equity_vs_random(hole_cards, board_cards, num_opponents=1, num_trials=1000):
    hole = convert_to_treys(hole_cards)
    board = convert_to_treys(board_cards)
    deck = Deck()
    
    # Remove known cards
    known_cards = hole + board
    for card in known_cards:
        deck.cards.remove(card)

    win_count = 0
    tie_count = 0

    for _ in range(num_trials):
        # Deal opponent hands
        opponent_hands = [
            [deck.draw(1)[0], deck.draw(1)[0]] for _ in range(num_opponents)
        ]

        # Complete the board if needed
        trial_board = board[:]
        while len(trial_board) < 5:
            trial_board.append(deck.draw(1)[0])

        # Evaluate our hand
        our_score = evaluator.evaluate(hole, trial_board)
        opp_scores = [evaluator.evaluate(opp, trial_board) for opp in opponent_hands]

        if our_score < min(opp_scores):
            win_count += 1
        elif our_score == min(opp_scores):
            tie_count += 1

        # Return all drawn cards back to the deck
        deck = Deck()
        for card in known_cards:
            deck.cards.remove(card)

    equity = (win_count + tie_count * 0.5) / num_trials
    return equity
