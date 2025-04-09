def findPokerHand(hand):
    """Given a list of cards like ['KH', 'QH', '10H', 'JH', 'AH'],
    returns the best poker hand rank as a string."""
    
    ranks = []
    suits = []
    possible_ranks = []

    for card in hand:
        if len(card) == 2:
            rank = card[0]
            suit = card[1]
        else:
            rank = card[:2]
            suit = card[2]

        if rank == "A":
            rank = 14
        elif rank == "K":
            rank = 13
        elif rank == "Q":
            rank = 12
        elif rank == "J":
            rank = 11

        ranks.append(int(rank))
        suits.append(suit)

    sorted_ranks = sorted(ranks)
    unique_vals = list(set(sorted_ranks))

    # Flush / Straight / Royal
    if suits.count(suits[0]) == 5:
        if sorted_ranks == [10, 11, 12, 13, 14]:
            possible_ranks.append(10)  # Royal Flush
        elif all(sorted_ranks[i] == sorted_ranks[i - 1] + 1 for i in range(1, 5)):
            possible_ranks.append(9)  # Straight Flush
        else:
            possible_ranks.append(6)  # Flush

    if all(sorted_ranks[i] == sorted_ranks[i - 1] + 1 for i in range(1, 5)):
        possible_ranks.append(5)  # Straight

    if len(unique_vals) == 2:
        for val in unique_vals:
            if sorted_ranks.count(val) == 4:
                possible_ranks.append(8)  # Four of a Kind
            if sorted_ranks.count(val) == 3:
                possible_ranks.append(7)  # Full House

    if len(unique_vals) == 3:
        for val in unique_vals:
            if sorted_ranks.count(val) == 3:
                possible_ranks.append(4)  # Three of a Kind
            if sorted_ranks.count(val) == 2:
                possible_ranks.append(3)  # Two Pair

    if len(unique_vals) == 4:
        possible_ranks.append(2)  # One Pair

    if not possible_ranks:
        possible_ranks.append(1)  # High Card

    rank_names = {
        10: "Royal Flush",
        9: "Straight Flush",
        8: "Four of a Kind",
        7: "Full House",
        6: "Flush",
        5: "Straight",
        4: "Three of a Kind",
        3: "Two Pair",
        2: "Pair",
        1: "High Card"
    }

    return rank_names[max(possible_ranks)]
