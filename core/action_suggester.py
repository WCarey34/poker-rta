import pandas as pd
import os

# Load the chart once
CHART_PATH = os.path.join("data", "charts", "push_fold.csv")
push_fold_chart = pd.read_csv(CHART_PATH)

def suggest_action(equity):
    if equity > 0.75:
        return "Raise"
    elif equity > 0.45:
        return "Call"
    else:
        return "Fold"

def suggest_push_fold(position, stack_bb, hand):
    try:
        filtered = push_fold_chart[
            (push_fold_chart["position"] == position) &
            (push_fold_chart["stack_bb"] == int(stack_bb)) &
            (push_fold_chart["hand"].str.upper() == hand.upper())
        ]
        if not filtered.empty:
            return filtered.iloc[0]["action"]
        else:
            return "No chart suggestion"
    except Exception as e:
        return f"Error: {e}"
