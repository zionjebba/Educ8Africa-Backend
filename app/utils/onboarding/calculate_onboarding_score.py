def calculate_onboarding_score(
    ceo_correct: bool,
    mission_correct: bool
) -> tuple[int, int]:
    """
    Calculate onboarding score and points
    Returns: (total_score, points_earned)
    """
    score = 0
    if ceo_correct:
        score += 50
    if mission_correct:
        score += 50
    
    base_points = 100
    bonus_points = (50 if ceo_correct else 0) + (50 if mission_correct else 0)
    
    return score, base_points + bonus_points